import os
import docker
import queue
import threading
import time

from models import (
    CompileResult,
    ExecutionResult,
    ExecutionRequest,
)

from workspace_manager import WorkspaceManager
from container_manager import ContainerManager


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WORKSPACE_PATH = os.path.join(
    BASE_DIR,
    "workspace",
)

IMAGE_NAME = "codeforge-rce"

DEFAULT_TIMEOUT = 2.0
MEMORY_LIMIT = "128m"
PIDS_LIMIT = 64


RUNTIME_STATUS = {
    0: ("SUCCESS", "Program executed successfully"),
    132: ("ILLEGAL_INSTRUCTION", "Illegal instruction"),
    134: ("ABORTED", "Program aborted"),
    136: ("FLOATING_POINT_EXCEPTION", "Floating point exception"),
    137: ("KILLED", "Process killed"),
    139: ("SEGMENTATION_FAULT", "Segmentation fault"),
}


# ============================================================
# MANAGERS
# ============================================================

workspace = WorkspaceManager(
    WORKSPACE_PATH
)

container_manager = ContainerManager(
    image_name=IMAGE_NAME,
    memory_limit=MEMORY_LIMIT,
    pids_limit=PIDS_LIMIT,
)


# ============================================================
# COMPILER
# ============================================================

def compile_code(container) -> CompileResult:

    if container is None:
        return CompileResult(
            status="ERROR",
            logs="Container not found!",
            status_code=-1,
        )

    try:

        response = container.exec_run(
            cmd="g++ /app/code.cpp -o /app/out"
        )

        logs = response.output.decode(
            "utf-8",
            errors="replace",
        )

        return CompileResult(
            status=(
                "SUCCESS"
                if response.exit_code == 0
                else "COMPILATION ERROR"
            ),
            logs=logs,
            status_code=response.exit_code,
        )

    except docker.errors.DockerException as e:

        return CompileResult(
            status="DOCKER_ERROR",
            logs=str(e),
            status_code=-1,
        )


# ============================================================
# EXECUTION WORKER
# ============================================================

def worker(
    exec_id: str,
    result_queue: queue.Queue,
):

    try:

        # Temporary for Layer 3.
        # Execution-specific Docker API usage will move
        # into Executor in a later layer.

        output = container_manager.client.api.exec_start(
            exec_id=exec_id
        )

        info = container_manager.client.api.exec_inspect(
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


# ============================================================
# CODE EXECUTION
# ============================================================

def run_code(
    container,
    timeout: float = DEFAULT_TIMEOUT,
    input_data: str | None = None,
) -> ExecutionResult:

    if container is None:
        return ExecutionResult(
            status="ERROR",
            stdout="Container not found",
            status_code=-1,
        )

    result_queue = queue.Queue()

    try:

        # ----------------------------------------------------
        # Prepare input
        # ----------------------------------------------------

        workspace.write_input(
            input_data
        )

        # ----------------------------------------------------
        # Create execution process
        # ----------------------------------------------------

        command = [
            "sh",
            "-c",
            "/app/out < /app/input.txt",
        ]

        exec_obj = container_manager.client.api.exec_create(
            container=container.id,
            cmd=command,
            stdout=True,
            stderr=True,
        )

        exec_id = exec_obj["Id"]

        # ----------------------------------------------------
        # Start worker
        # ----------------------------------------------------

        thread = threading.Thread(
            target=worker,
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

        # ----------------------------------------------------
        # TLE
        # ----------------------------------------------------

        if thread.is_alive():

            container_manager.kill(
                container
            )

            thread.join(timeout=1)

            return ExecutionResult(
                status="TLE",
                stdout="Time Limit Exceeded",
                status_code=-1,
                execution_time_ms=execution_time,
            )

        # ----------------------------------------------------
        # No result
        # ----------------------------------------------------

        if result_queue.empty():

            return ExecutionResult(
                status="ERROR",
                stdout="Worker returned no result",
                status_code=-1,
                execution_time_ms=execution_time,
            )

        result = result_queue.get()

        # ----------------------------------------------------
        # Worker error
        # ----------------------------------------------------

        if "error" in result:

            return ExecutionResult(
                status="DOCKER_ERROR",
                stdout=result["error"],
                status_code=-1,
                execution_time_ms=execution_time,
            )

        output = result["output"]
        info = result["info"]

        # ----------------------------------------------------
        # Reload container
        # ----------------------------------------------------

        container_manager.reload(
            container
        )

        state = container.attrs["State"]

        # ----------------------------------------------------
        # MLE
        # ----------------------------------------------------

        if state.get("OOMKilled", False):

            return ExecutionResult(
                status="MLE",
                stdout="Memory Limit Exceeded",
                status_code=137,
                execution_time_ms=execution_time,
            )

        # ----------------------------------------------------
        # Memory usage
        # ----------------------------------------------------

        memory_mb = None

        try:

            stats = container_manager.stats(
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

        # ----------------------------------------------------
        # Exit code
        # ----------------------------------------------------

        exit_code = info["ExitCode"]

        status, default_message = RUNTIME_STATUS.get(
            exit_code,
            (
                "RUNTIME_ERROR",
                "Runtime Error",
            ),
        )

        # ----------------------------------------------------
        # Output
        # ----------------------------------------------------

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

        # Workspace responsibility
        workspace.cleanup()

        # Container responsibility
        container_manager.remove(
            container
        )


# ============================================================
# PUBLIC RCE FUNCTION
# ============================================================

def CodeForgeRCE(
    request: ExecutionRequest,
):

    if (
        request is None
        or not request.code
        or not request.code.strip()
    ):
        return {
            "status": "ERROR",
            "logs": "Code not provided",
            "status_code": -1,
        }

    container = None

    try:

        # ----------------------------------------------------
        # Write source code
        # ----------------------------------------------------

        workspace.write_code(
            request.code
        )

        # ----------------------------------------------------
        # Create container
        # ----------------------------------------------------

        container = container_manager.create(
            WORKSPACE_PATH
        )

        if container is None:

            return {
                "status": "DOCKER_ERROR",
                "logs": "Failed to create Docker container",
                "status_code": -1,
            }

        # ----------------------------------------------------
        # Compile
        # ----------------------------------------------------

        compile_result = compile_code(
            container
        )

        if compile_result.status_code != 0:

            return {
                "status": compile_result.status,
                "logs": compile_result.logs,
                "status_code": compile_result.status_code,
            }

        # ----------------------------------------------------
        # Execute
        # ----------------------------------------------------

        execution_result = run_code(
            container=container,
            timeout=request.timeout,
            input_data=request.stdin,
        )

        # run_code() already cleaned container.
        container = None

        return {
            "status": execution_result.status,
            "stdout": execution_result.stdout,
            "status_code": execution_result.status_code,
            "execution_time_ms": execution_result.execution_time_ms,
            "memory": execution_result.memory_mb,
        }

    finally:

        # If compilation failed or something crashed
        # before run_code() took responsibility.

        if container is not None:

            workspace.cleanup()

            container_manager.remove(
                container
            )