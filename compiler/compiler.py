import docker

from models import CompileResult


class Compiler:

    def __init__(self, docker_client):
        self.client = docker_client

    def compile(self, container) -> CompileResult:

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

            if response.exit_code == 0:
                status = "SUCCESS"
            else:
                status = "COMPILATION ERROR"

            return CompileResult(
                status=status,
                logs=logs,
                status_code=response.exit_code,
            )

        except docker.errors.DockerException as e:

            return CompileResult(
                status="DOCKER_ERROR",
                logs=str(e),
                status_code=-1,
            )