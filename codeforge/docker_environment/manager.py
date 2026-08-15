import logging

import docker
from docker.errors import DockerException, ImageNotFound, APIError


class DockerEnvironment:

    def __init__(
        self,
        image_name: str = "codeforge-rce",
        image_tag: str = "0.1.0",
        auto_pull: bool = True,
    ):
        self.image_name = image_name
        self.image_tag = image_tag
        self.image_ref = f"{image_name}:{image_tag}"
        self.auto_pull = auto_pull

        self.logger = logging.getLogger(
            "codeforge.docker"
        )

        self.client = None

    def connect(self) -> bool:
        """
        Connect to Docker Engine and verify that it is reachable.
        """

        self.logger.info(
            "Checking Docker Engine..."
        )

        try:

            self.client = docker.from_env()

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
        """
        Returns True when Docker Engine is reachable.
        """

        if self.client is None:
            return self.connect()

        try:

            self.client.ping()

            return True

        except DockerException:

            return False

    def image_exists(self) -> bool:
        """
        Check whether the required Docker image exists locally.
        """

        if not self.is_available():
            return False

        try:

            self.client.images.get(
                self.image_ref
            )

            self.logger.info(
                "Docker image found: %s",
                self.image_ref,
            )

            return True

        except ImageNotFound:

            self.logger.info(
                "Docker image missing: %s",
                self.image_ref,
            )

            return False

        except DockerException as e:

            self.logger.error(
                "Failed to check Docker image: %s",
                e,
            )

            return False

    def pull_image(self) -> bool:
        """
        Pull the required Docker image from the configured registry.
        """

        if not self.is_available():
            return False

        self.logger.info(
            "Pulling Docker image: %s",
            self.image_ref,
        )

        try:

            self.client.images.pull(
                self.image_name,
                tag=self.image_tag,
            )

            self.logger.info(
                "Docker image ready: %s",
                self.image_ref,
            )

            return True

        except APIError as e:

            self.logger.error(
                "Failed to pull Docker image: %s",
                e,
            )

            return False

        except DockerException as e:

            self.logger.error(
                "Docker error while pulling image: %s",
                e,
            )

            return False

    def ensure_ready(self) -> bool:
        """
        Ensure Docker Engine is available and the required image exists.
        """

        if not self.is_available():
            return False

        if self.image_exists():
            return True

        if not self.auto_pull:

            self.logger.error(
                "Docker image missing and auto_pull is disabled: %s",
                self.image_ref,
            )

            return False

        return self.pull_image()