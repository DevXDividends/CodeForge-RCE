import logging
from pathlib import Path

import docker
from docker.errors import APIError, DockerException, ImageNotFound


class DockerEnvironment:

    def __init__(
        self,
        image_name: str,
        image_tag: str = "0.1.0",
        auto_pull: bool = True,
        auto_build: bool = False,
        build_context: str | None = None,
        build_dockerfile: str = "Dockerfile",
    ):
        self.image_name = image_name
        self.image_tag = image_tag

        self.auto_pull = auto_pull
        self.auto_build = auto_build

        self.build_context = (
            Path(build_context).resolve()
            if build_context
            else None
        )

        self.build_dockerfile = build_dockerfile

        self.image_ref = (
            f"{self.image_name}:{self.image_tag}"
        )

        self.client = None

        self.logger = logging.getLogger(
            "codeforge.docker"
        )

    # ---------------------------------------------------------
    # Docker connection
    # ---------------------------------------------------------

    def connect(self) -> bool:

        if self.client is not None:
            return self.is_available()

        self.logger.info(
            "Checking Docker Engine..."
        )

        try:

            self.client = docker.from_env(
                timeout=10
            )

            self.client.ping()

            self.logger.info(
                "Docker Engine: OK"
            )

            return True

        except DockerException as e:

            self.client = None

            self.logger.error(
                "Docker Engine unavailable: %s",
                e,
            )

            return False

    def is_available(self) -> bool:

        if self.client is None:

            try:
                self.client = docker.from_env(
                    timeout=10
                )
            except DockerException:
                self.client = None
                return False

        try:

            self.client.ping()

            return True

        except DockerException:

            self.client = None

            return False

    # ---------------------------------------------------------
    # Image check
    # ---------------------------------------------------------

    def image_exists(self) -> bool:

        if not self.is_available():
            return False

        try:

            self.client.images.get(
                self.image_ref
            )

            self.logger.info(
                "Runtime image found: %s",
                self.image_ref,
            )

            return True

        except ImageNotFound:

            self.logger.info(
                "Runtime image not found locally: %s",
                self.image_ref,
            )

            return False

        except DockerException as e:

            self.logger.error(
                "Failed to inspect runtime image: %s",
                e,
            )

            return False

    # ---------------------------------------------------------
    # Pull image
    # ---------------------------------------------------------

    def pull_image(self) -> bool:

        if not self.is_available():
            return False

        self.logger.info(
            "Pulling runtime image: %s",
            self.image_ref,
        )

        try:

            self.client.images.pull(
                repository=self.image_name,
                tag=self.image_tag,
            )

            # Verify after pull.
            self.client.images.get(
                self.image_ref
            )

            self.logger.info(
                "Runtime image ready: %s",
                self.image_ref,
            )

            return True

        except APIError as e:

            self.logger.error(
                "Failed to pull runtime image: %s",
                e,
            )

            return False

        except DockerException as e:

            self.logger.error(
                "Docker error while pulling image: %s",
                e,
            )

            return False

    # ---------------------------------------------------------
    # Build image
    # ---------------------------------------------------------

    def build_image(self) -> bool:

        if not self.is_available():
            return False

        if self.build_context is None:

            self.logger.error(
                "Build requested but no build_context was provided."
            )

            return False

        if not self.build_context.is_dir():

            self.logger.error(
                "Build context does not exist: %s",
                self.build_context,
            )

            return False

        dockerfile_path = (
            self.build_context
            / self.build_dockerfile
        )

        if not dockerfile_path.is_file():

            self.logger.error(
                "Dockerfile not found: %s",
                dockerfile_path,
            )

            return False

        self.logger.info(
            "Building runtime image: %s",
            self.image_ref,
        )

        self.logger.info(
            "Build context: %s",
            self.build_context,
        )

        try:

            image, build_logs = (
                self.client.images.build(
                    path=str(
                        self.build_context
                    ),
                    dockerfile=self.build_dockerfile,
                    tag=self.image_ref,
                    rm=True,
                    forcerm=True,
                )
            )

            for entry in build_logs:

                if not isinstance(entry, dict):
                    continue

                stream = entry.get("stream")

                if stream:
                    message = stream.strip()

                    if message:
                        self.logger.info(
                            "[Docker Build] %s",
                            message,
                        )

                error = entry.get("error")

                if error:
                    self.logger.error(
                        "[Docker Build] %s",
                        error,
                    )

            # Verify image.
            self.client.images.get(
                self.image_ref
            )

            self.logger.info(
                "Runtime image built successfully: %s",
                self.image_ref,
            )

            return True

        except (APIError, DockerException) as e:

            self.logger.error(
                "Failed to build runtime image: %s",
                e,
            )

            return False

    # ---------------------------------------------------------
    # Ensure environment
    # ---------------------------------------------------------

    def ensure_ready(self) -> bool:

        if not self.connect():
            return False

        if self.image_exists():
            return True

        # Custom/local build gets priority when explicitly enabled.
        if (
            self.auto_build
            and self.build_context is not None
        ):

            if self.build_image():
                return True

        # Default distribution path.
        if self.auto_pull:
            return self.pull_image()

        self.logger.error(
            "Runtime image unavailable and automatic pull is disabled: %s",
            self.image_ref,
        )

        return False