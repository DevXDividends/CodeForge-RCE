import os
import docker

from models import (
    ExecutionRequest,
)

from workspace_manager import WorkspaceManager
from container_manager import ContainerManager
from compiler import Compiler
from executor import Executor


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

compiler = Compiler(
    container_manager.client
)

executor = Executor(
    container_manager=container_manager,
    workspace_manager=workspace,
    default_timeout=DEFAULT_TIMEOUT,
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

        # -----------------------------------------
        # Write source code
        # -----------------------------------------

        workspace.write_code(
            request.code
        )

        # -----------------------------------------
        # Create container
        # -----------------------------------------

        container = container_manager.create(
            WORKSPACE_PATH
        )

        if container is None:
            return {
                "status": "DOCKER_ERROR",
                "logs": "Failed to create Docker container",
                "status_code": -1,
            }

        # -----------------------------------------
        # Compile
        # -----------------------------------------

        compile_result = compiler.compile(
            container
        )

        if compile_result.status_code != 0:

            return {
                "status": compile_result.status,
                "logs": compile_result.logs,
                "status_code": compile_result.status_code,
            }

        # -----------------------------------------
        # Execute
        # -----------------------------------------

        execution_result = executor.run(
            container=container,
            timeout=request.timeout,
            input_data=request.stdin,
        )

        # executor owns cleanup now
        container = None

        return {
            "status": execution_result.status,
            "stdout": execution_result.stdout,
            "status_code": execution_result.status_code,
            "execution_time_ms": execution_result.execution_time_ms,
            "memory": execution_result.memory_mb,
        }

    finally:

        # This handles failures before Executor.run()
        # takes ownership of the container.

        if container is not None:

            workspace.cleanup()

            container_manager.remove(
                container
            )