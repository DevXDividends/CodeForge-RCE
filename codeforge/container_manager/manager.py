import docker


class ContainerManager:

    def __init__(
        self,
        image_name: str,
        memory_limit: str = "128m",
        pids_limit: int = 64,
    ):
        self.image_name = image_name
        self.memory_limit = memory_limit
        self.pids_limit = pids_limit

        self.client = docker.from_env()

    def create(self, host_path: str):

        try:

            container = self.client.containers.create(
                image=self.image_name,
                command="sleep infinity",
                network_disabled=True,
                mem_limit=self.memory_limit,
                pids_limit=self.pids_limit,
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

    def kill(self, container):

        if container is None:
            return

        try:
            container.kill()

        except docker.errors.DockerException:
            pass

    def remove(self, container):

        if container is None:
            return

        try:
            container.remove(
                force=True
            )

        except docker.errors.DockerException:
            pass

    def reload(self, container):

        if container is None:
            return None

        try:
            container.reload()
            return container

        except docker.errors.DockerException:
            return None

    def stats(self, container):

        if container is None:
            return None

        try:
            return container.stats(
                stream=False
            )

        except docker.errors.DockerException:
            return None