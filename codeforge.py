import os

from models import ExecutionRequest

from workspace_manager import WorkspaceManager
from container_manager import ContainerManager
from compiler import Compiler
from executor import Executor


class CodeForgeRCE:

    def __init__(
        self,
        image_name: str = "codeforge-rce",
        workspace_path: str | None = None,
        default_timeout: float = 2.0,
        memory_limit: str = "128m",
        pids_limit: int = 64,
    ):

        # ----------------------------------------------------
        # Resolve workspace
        # ----------------------------------------------------

        if workspace_path is None:

            base_dir = os.path.dirname(
                os.path.abspath(__file__)
            )

            workspace_path = os.path.join(
                base_dir,
                "workspace",
            )

        self.workspace_path = workspace_path

        # ----------------------------------------------------
        # Create managers
        # ----------------------------------------------------

        self.workspace = WorkspaceManager(
            self.workspace_path
        )

        self.container_manager = ContainerManager(
            image_name=image_name,
            memory_limit=memory_limit,
            pids_limit=pids_limit,
        )

        self.compiler = Compiler(
            self.container_manager.client
        )

        self.executor = Executor(
            container_manager=self.container_manager,
            workspace_manager=self.workspace,
            default_timeout=default_timeout,
        )

    def execute(
        self,
        request: ExecutionRequest,
    ):

        # ----------------------------------------------------
        # Validate request
        # ----------------------------------------------------

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

            # ------------------------------------------------
            # Write source code
            # ------------------------------------------------

            self.workspace.write_code(
                request.code
            )

            # ------------------------------------------------
            # Create container
            # ------------------------------------------------

            container = self.container_manager.create(
                self.workspace_path
            )

            if container is None:

                return {
                    "status": "DOCKER_ERROR",
                    "logs": "Failed to create Docker container",
                    "status_code": -1,
                }

            # ------------------------------------------------
            # Compile
            # ------------------------------------------------

            compile_result = self.compiler.compile(
                container
            )

            if compile_result.status_code != 0:

                return {
                    "status": compile_result.status,
                    "logs": compile_result.logs,
                    "status_code": compile_result.status_code,
                }

            # ------------------------------------------------
            # Execute
            # ------------------------------------------------

            execution_result = self.executor.run(
                container=container,
                timeout=request.timeout,
                input_data=request.stdin,
            )

            # Executor has already cleaned everything.
            container = None

            return {
                "status": execution_result.status,
                "stdout": execution_result.stdout,
                "status_code": execution_result.status_code,
                "execution_time_ms": execution_result.execution_time_ms,
                "memory": execution_result.memory_mb,
            }

        finally:

            # ------------------------------------------------
            # Fallback cleanup
            #
            # Needed when something fails before Executor.run()
            # gets ownership of the container.
            # ------------------------------------------------

            if container is not None:

                self.workspace.cleanup()

                self.container_manager.remove(
                    container
                )