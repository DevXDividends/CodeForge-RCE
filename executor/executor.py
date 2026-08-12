import queue
import threading
import time

import docker

from models import ExecutionResult


class Executor:

    RUNTIME_STATUS = {
        0: ("SUCCESS", "Program executed successfully"),
        132: ("ILLEGAL_INSTRUCTION", "Illegal instruction"),
        134: ("ABORTED", "Program aborted"),
        136: ("FLOATING_POINT_EXCEPTION", "Floating point exception"),
        137: ("KILLED", "Process killed"),
        139: ("SEGMENTATION_FAULT", "Segmentation fault"),
    }

    def __init__(
        self,
        container_manager,
        workspace_manager,
        default_timeout: float = 2.0,
    ):
        self.container_manager = container_manager
        self.workspace_manager = workspace_manager
        self.default_timeout = default_timeout

    def _worker(
        self,
        exec_id: str,
        result_queue: queue.Queue,
    ):
        try:
            output = self.container_manager.client.api.exec_start(
                exec_id=exec_id
            )

            info = self.container_manager.client.api.exec_inspect(
                exec_id=exec_id
            )

            result_queue.put({
                "output": output,
                "info": info,
            })

        except Exception as e:
            result_queue.put({
                "error": str(e),
            })

    def run(
        self,
        container,
        timeout: float | None = None,
        input_data: str | None = None,
    ) -> ExecutionResult:

        timeout = (
            timeout
            if timeout is not None
            else self.default_timeout
        )

        if container is None:
            return ExecutionResult(
                status="ERROR",
                stdout="Container not found",
                status_code=-1,
            )

        result_queue = queue.Queue()

        try:
            # ------------------------------------------
            # Prepare stdin
            # ------------------------------------------

            self.workspace_manager.write_input(
                input_data
            )

            command = [
                "sh",
                "-c",
                "/app/out < /app/input.txt",
            ]

            # ------------------------------------------
            # Create exec
            # ------------------------------------------

            exec_obj = (
                self.container_manager.client.api.exec_create(
                    container=container.id,
                    cmd=command,
                    stdout=True,
                    stderr=True,
                )
            )

            exec_id = exec_obj["Id"]

            # ------------------------------------------
            # Worker thread
            # ------------------------------------------

            thread = threading.Thread(
                target=self._worker,
                args=(exec_id, result_queue),
                daemon=True,
            )

            start = time.perf_counter()

            thread.start()
            thread.join(timeout)

            execution_time = round(
                (time.perf_counter() - start) * 1000,
                3,
            )

            # ------------------------------------------
            # TLE
            # ------------------------------------------

            if thread.is_alive():

                self.container_manager.kill(
                    container
                )

                thread.join(timeout=1)

                return ExecutionResult(
                    status="TLE",
                    stdout="Time Limit Exceeded",
                    status_code=-1,
                    execution_time_ms=execution_time,
                )

            # ------------------------------------------
            # Worker returned nothing
            # ------------------------------------------

            if result_queue.empty():

                return ExecutionResult(
                    status="ERROR",
                    stdout="Worker returned no result",
                    status_code=-1,
                    execution_time_ms=execution_time,
                )

            result = result_queue.get()

            # ------------------------------------------
            # Worker error
            # ------------------------------------------

            if "error" in result:

                return ExecutionResult(
                    status="DOCKER_ERROR",
                    stdout=result["error"],
                    status_code=-1,
                    execution_time_ms=execution_time,
                )

            output = result["output"]
            info = result["info"]

            # ------------------------------------------
            # Reload container
            # ------------------------------------------

            self.container_manager.reload(
                container
            )

            state = container.attrs["State"]

            # ------------------------------------------
            # MLE
            # ------------------------------------------

            if state.get("OOMKilled", False):

                return ExecutionResult(
                    status="MLE",
                    stdout="Memory Limit Exceeded",
                    status_code=137,
                    execution_time_ms=execution_time,
                )

            # ------------------------------------------
            # Memory
            # ------------------------------------------

            memory_mb = None

            try:

                stats = self.container_manager.stats(
                    container
                )

                if stats:

                    memory = stats["memory_stats"].get(
                        "max_usage",
                        stats["memory_stats"].get(
                            "usage",
                            0,
                        ),
                    )

                    memory_mb = round(
                        memory / (1024 * 1024),
                        2,
                    )

            except Exception:
                pass

            # ------------------------------------------
            # Exit code
            # ------------------------------------------

            exit_code = info["ExitCode"]

            status, default_message = self.RUNTIME_STATUS.get(
                exit_code,
                (
                    "RUNTIME_ERROR",
                    "Runtime Error",
                ),
            )

            # ------------------------------------------
            # Output
            # ------------------------------------------

            stdout = output.decode(
                "utf-8",
                errors="replace",
            )

            if not stdout.strip() and exit_code != 0:
                stdout = default_message

            return ExecutionResult(
                status=status,
                stdout=stdout,
                status_code=exit_code,
                execution_time_ms=execution_time,
                memory_mb=memory_mb,
            )

        except docker.errors.DockerException as e:

            return ExecutionResult(
                status="DOCKER_ERROR",
                stdout=str(e),
                status_code=-1,
            )

        finally:
            self.workspace_manager.cleanup()

            self.container_manager.remove(
                container
            )