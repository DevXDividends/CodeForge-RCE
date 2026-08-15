import logging

from .models import ExecutionRequest
from .workspace_manager import WorkspaceManager
from .docker_environment import DockerEnvironment
from .container_manager import ContainerManager
from .compiler import Compiler
from .executor import Executor
from .language import (
    LanguageConfig,
    LanguageRegistry,
)


logger = logging.getLogger(
    "codeforge"
)


class CodeForgeRCE:

    def __init__(
        self,
        image_name: str = "adityadengale/codeforge-rce",
        image_tag: str = "0.1.0",
        base_workspace_path: str | None = None,
        default_timeout: float = 2.0,
        memory_limit: str = "128m",
        pids_limit: int = 64,
        auto_pull_image: bool = True,
        auto_build_image: bool = False,
        build_context: str | None = None,
        build_dockerfile: str = "Dockerfile",
    ):

        # -----------------------------------------------------
        # Configuration
        # -----------------------------------------------------

        self.image_name = image_name
        self.image_tag = image_tag

        self.default_timeout = (
            default_timeout
        )

        self.memory_limit = memory_limit
        self.pids_limit = pids_limit

        # -----------------------------------------------------
        # Workspace
        # -----------------------------------------------------

        self.workspace = WorkspaceManager(
            base_workspace_path
        )

        self.workspace_path = (
            self.workspace.workspace_path
        )

        # -----------------------------------------------------
        # Docker environment
        # -----------------------------------------------------

        self.docker_environment = (
            DockerEnvironment(
                image_name=image_name,
                image_tag=image_tag,
                auto_pull=auto_pull_image,
                auto_build=auto_build_image,
                build_context=build_context,
                build_dockerfile=(
                    build_dockerfile
                ),
            )
        )

        # -----------------------------------------------------
        # Docker-dependent services
        # -----------------------------------------------------

        self.container_manager = None
        self.compiler = None
        self.executor = None

        # -----------------------------------------------------
        # Language registry
        # -----------------------------------------------------

        self.language_registry = (
            LanguageRegistry()
        )

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

    # =========================================================
    # Docker-dependent initialization
    # =========================================================

    def _initialize_services(self) -> bool:

        client = (
            self.docker_environment.client
        )

        if client is None:
            return False

        if self.container_manager is None:

            self.container_manager = (
                ContainerManager(
                    image_name=(
                        self.docker_environment
                        .image_ref
                    ),
                    docker_client=client,
                    memory_limit=(
                        self.memory_limit
                    ),
                    pids_limit=self.pids_limit,
                )
            )

        if self.compiler is None:

            self.compiler = Compiler(
                self.container_manager.client
            )

        if self.executor is None:

            self.executor = Executor(
                container_manager=(
                    self.container_manager
                ),
                workspace_manager=(
                    self.workspace
                ),
                default_timeout=(
                    self.default_timeout
                ),
            )

        return True

    # =========================================================
    # Execute
    # =========================================================

    def execute(
        self,
        request: ExecutionRequest,
    ):

        # -----------------------------------------------------
        # Validate request
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Language
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Docker environment
        # -----------------------------------------------------

        if not self.docker_environment.ensure_ready():

            if not self.docker_environment.is_available():

                return {
                    "status": "DOCKER_UNAVAILABLE",
                    "logs": (
                        "Docker Engine is not running "
                        "or is unreachable."
                    ),
                    "status_code": -1,
                }

            return {
                "status": "DOCKER_IMAGE_ERROR",
                "logs": (
                    "CodeForge runtime image could "
                    "not be prepared."
                ),
                "status_code": -1,
            }

        # -----------------------------------------------------
        # Initialize Docker services
        # -----------------------------------------------------

        if not self._initialize_services():

            return {
                "status": "DOCKER_ERROR",
                "logs": (
                    "Failed to initialize Docker services."
                ),
                "status_code": -1,
            }

        container = None

        try:

            # -------------------------------------------------
            # Ensure workspace
            # -------------------------------------------------

            self.workspace.ensure_workspace()

            self.workspace_path = (
                self.workspace.workspace_path
            )

            # -------------------------------------------------
            # Write source
            # -------------------------------------------------

            self.workspace.write_code(
                request.code,
                language_config.source_file,
            )

            # -------------------------------------------------
            # Create container
            # -------------------------------------------------

            container = (
                self.container_manager.create(
                    self.workspace_path
                )
            )

            if container is None:

                return {
                    "status": "DOCKER_ERROR",
                    "logs": (
                        "Failed to create "
                        "Docker container."
                    ),
                    "status_code": -1,
                }

            # -------------------------------------------------
            # Compile
            # -------------------------------------------------

            compile_result = (
                self.compiler.compile(
                    container,
                    language_config,
                )
            )

            if compile_result.status_code != 0:

                return {
                    "status": (
                        compile_result.status
                    ),
                    "logs": (
                        compile_result.logs
                    ),
                    "status_code": (
                        compile_result.status_code
                    ),
                }

            # -------------------------------------------------
            # Execute
            # -------------------------------------------------

            execution_result = (
                self.executor.run(
                    container=container,
                    language_config=(
                        language_config
                    ),
                    timeout=request.timeout,
                    input_data=request.stdin,
                )
            )

            # Executor owns cleanup.
            container = None

            return {
                "status": (
                    execution_result.status
                ),
                "stdout": (
                    execution_result.stdout
                ),
                "status_code": (
                    execution_result.status_code
                ),
                "execution_time_ms": (
                    execution_result.execution_time_ms
                ),
                "memory": (
                    execution_result.memory_mb
                ),
            }

        finally:

            if container is not None:

                self.workspace.cleanup()

                self.container_manager.remove(
                    container
                )