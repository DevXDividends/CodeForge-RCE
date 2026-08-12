import os
import docker
import queue
import threading
import shutil
import time

from models import (
    CompileResult,
    ExecutionResult,
    ExecutionRequest,
)


# CONFIGURATION
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_PATH = os.path.join(BASE_DIR, "workspace")

IMAGE_NAME = "codeforge-rce"

DEFAULT_TIMEOUT = 2.0
MEMORY_LIMIT = "128m"
PIDS_LIMIT = 64


PRESERVE_FILES = {
    ".gitkeep",
    "code.cpp",
}


RUNTIME_STATUS = {
    0: ("SUCCESS", "Program executed successfully"),
    132: ("ILLEGAL_INSTRUCTION", "Illegal instruction"),
    134: ("ABORTED", "Program aborted"),
    136: ("FLOATING_POINT_EXCEPTION", "Floating point exception"),
    137: ("KILLED", "Process killed"),
    139: ("SEGMENTATION_FAULT", "Segmentation fault"),
}


# DOCKER CLIENT
client = docker.from_env()


# CONTAINER
def create_container(host_path: str):
    try:
        container = client.containers.create(
            image=IMAGE_NAME,
            command="sleep infinity",
            network_disabled=True,
            mem_limit=MEMORY_LIMIT,
            pids_limit=PIDS_LIMIT,
            volumes={
                host_path: {
                    "bind": "/app",
                    "mode": "rw",
                }
            },
        )

        container.start()
        container.reload()

        return container

    except docker.errors.DockerException:
        return None


# COMPILER
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


# EXECUTION WORKER

def worker(exec_id: str, result_queue: queue.Queue):

    try:
        output = client.api.exec_start(
            exec_id=exec_id
        )

        info = client.api.exec_inspect(
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


# CODE EXECUTION

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

    input_file = os.path.join(
        WORKSPACE_PATH,
        "input.txt",
    )

    try:

        # Prepare stdin

        with open(
            input_file,
            "w",
            encoding="utf-8",
        ) as f:
            f.write(input_data or "")

        # Create execution process

        command = [
            "sh",
            "-c",
            "/app/out < /app/input.txt",
        ]

        exec_obj = client.api.exec_create(
            container=container.id,
            cmd=command,
            stdout=True,
            stderr=True,
        )

        exec_id = exec_obj["Id"]

        # Start worker

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

        # TIME LIMIT EXCEEDED

        if thread.is_alive():

            try:
                container.kill()
            except docker.errors.DockerException:
                pass

            thread.join(timeout=1)

            return ExecutionResult(
                status="TLE",
                stdout="Time Limit Exceeded",
                status_code=-1,
                execution_time_ms=execution_time,
            )

        # Worker produced no result

        if result_queue.empty():

            return ExecutionResult(
                status="ERROR",
                stdout="Worker returned no result",
                status_code=-1,
                execution_time_ms=execution_time,
            )

        result = result_queue.get()

        # Worker / Docker error

        if "error" in result:

            return ExecutionResult(
                status="DOCKER_ERROR",
                stdout=result["error"],
                status_code=-1,
                execution_time_ms=execution_time,
            )

        output = result["output"]
        info = result["info"]

        # Reload container state

        container.reload()

        state = container.attrs["State"]

        # MEMORY LIMIT EXCEEDED

        if state.get("OOMKilled", False):

            return ExecutionResult(
                status="MLE",
                stdout="Memory Limit Exceeded",
                status_code=137,
                execution_time_ms=execution_time,
            )

        # MEMORY USAGE

        memory_mb = None

        try:

            stats = container.stats(
                stream=False
            )

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

        # EXIT CODE

        exit_code = info["ExitCode"]

        status, default_message = RUNTIME_STATUS.get(
            exit_code,
            (
                "RUNTIME_ERROR",
                "Runtime Error",
            ),
        )

        # STDOUT + STDERR

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

        cleanup(
            container=container,
            workspace_path=WORKSPACE_PATH,
        )


# CLEANUP

def cleanup(
    container=None,
    workspace_path=None,
):

    # Remove container

    if container is not None:

        try:
            container.remove(
                force=True
            )
        except docker.errors.DockerException:
            pass

    # Clean workspace
    if (
        workspace_path
        and os.path.isdir(workspace_path)
    ):

        for item in os.listdir(workspace_path):

            if item in PRESERVE_FILES:
                continue

            path = os.path.join(
                workspace_path,
                item,
            )

            try:

                if (
                    os.path.isfile(path)
                    or os.path.islink(path)
                ):
                    os.remove(path)

                elif os.path.isdir(path):
                    shutil.rmtree(path)

            except OSError:
                pass


# CODEFORGE RCE

def CodeForgeRCE(
    request: ExecutionRequest,
):

    # Validate request

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

        # Write source code

        source_file = os.path.join(
            WORKSPACE_PATH,
            "code.cpp",
        )

        with open(
            source_file,
            "w",
            encoding="utf-8",
        ) as file:
            file.write(request.code)

        # Create container

        container = create_container(
            host_path=WORKSPACE_PATH,
        )

        if container is None:

            return {
                "status": "DOCKER_ERROR",
                "logs": "Failed to create Docker container",
                "status_code": -1,
            }

        # Compile

        compile_result = compile_code(
            container=container,
        )

        if compile_result.status_code != 0:

            return {
                "status": compile_result.status,
                "logs": compile_result.logs,
                "status_code": compile_result.status_code,
            }

        # Execute

        execution_result = run_code(
            container=container,
            timeout=request.timeout,
            input_data=request.stdin,
        )

        # run_code() owns cleanup after execution.

        container = None

        return {
            "status": execution_result.status,
            "stdout": execution_result.stdout,
            "status_code": execution_result.status_code,
            "execution_time_ms": execution_result.execution_time_ms,
            "memory": execution_result.memory_mb,
        }

    finally:

        # ----------------------------------------------------
        # Important:
        # If compilation fails or container creation/execution
        # throws before run_code() gets ownership, clean it.
        # ----------------------------------------------------

        if container is not None:

            cleanup(
                container=container,
                workspace_path=WORKSPACE_PATH,
            )