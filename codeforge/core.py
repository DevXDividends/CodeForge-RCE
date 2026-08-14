from .models import ExecutionRequest
from .workspace_manager import WorkspaceManager
from .container_manager import ContainerManager
from .compiler import Compiler
from .executor import Executor
from .language import LanguageConfig, LanguageRegistry


class CodeForgeRCE:

    def __init__(
        self,
        image_name: str = "codeforge-rce",
        base_workspace_path: str | None = None,
        default_timeout: float = 2.0,
        memory_limit: str = "128m",
        pids_limit: int = 64,
    ):

        # ====================================================
        # WORKSPACE
        # ====================================================

        self.workspace = WorkspaceManager(
            base_workspace_path
        )

        self.workspace_path = (
            self.workspace.workspace_path
        )

        # ====================================================
        # CONTAINER MANAGER
        # ====================================================

        self.container_manager = ContainerManager(
            image_name=image_name,
            memory_limit=memory_limit,
            pids_limit=pids_limit,
        )

        # ====================================================
        # COMPILER
        # ====================================================

        self.compiler = Compiler(
            self.container_manager.client
        )

        # ====================================================
        # EXECUTOR
        # ====================================================

        self.executor = Executor(
            container_manager=self.container_manager,
            workspace_manager=self.workspace,
            default_timeout=default_timeout,
        )

        # ====================================================
        # LANGUAGE REGISTRY
        # ====================================================

        self.language_registry = LanguageRegistry()

        self.language_registry.register(
            LanguageConfig(
                name="cpp",
                source_file="code.cpp",
                compile_command=(
                    "g++ "
                    "/app/code.cpp "
                    "-o /app/out"
                ),
                run_command="/app/out",
            )
        )

    def execute(
        self,
        request: ExecutionRequest,
    ):

        # ====================================================
        # VALIDATE REQUEST
        # ====================================================

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

            # =================================================
            # GET LANGUAGE CONFIG
            # =================================================

            try:
                language_config = (
                    self.language_registry.get(
                        request.language
                    )
                )

            except ValueError as e:

                return {
                    "status": "ERROR",
                    "logs": str(e),
                    "status_code": -1,
                }

            # =================================================
            # ENSURE WORKSPACE EXISTS
            # =================================================

            self.workspace.ensure_workspace()

            self.workspace_path = (
                self.workspace.workspace_path
            )

            # =================================================
            # WRITE SOURCE
            # =================================================

            self.workspace.write_code(
                request.code,
                language_config.source_file,
            )

            # =================================================
            # CREATE CONTAINER
            # =================================================

            container = self.container_manager.create(
                self.workspace_path
            )

            if container is None:

                return {
                    "status": "DOCKER_ERROR",
                    "logs": (
                        "Failed to create "
                        "Docker container"
                    ),
                    "status_code": -1,
                }

            # =================================================
            # COMPILE
            # =================================================

            compile_result = self.compiler.compile(
                container,
                language_config,
            )

            if compile_result.status_code != 0:

                return {
                    "status": compile_result.status,
                    "logs": compile_result.logs,
                    "status_code": compile_result.status_code,
                }

            # =================================================
            # EXECUTE
            # =================================================

            execution_result = self.executor.run(
                container=container,
                language_config=language_config,
                timeout=request.timeout,
                input_data=request.stdin,
            )

            # Executor owns cleanup after execution
            container = None

            return {
                "status": execution_result.status,
                "stdout": execution_result.stdout,
                "status_code": execution_result.status_code,
                "execution_time_ms": (
                    execution_result.execution_time_ms
                ),
                "memory": execution_result.memory_mb,
            }

        finally:

            # =================================================
            # FALLBACK CLEANUP
            # =================================================

            if container is not None:

                self.workspace.cleanup()

                self.container_manager.remove(
                    container
                )