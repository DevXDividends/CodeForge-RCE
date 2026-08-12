import docker

from models import CompileResult
from language import LanguageConfig


class Compiler:

    def __init__(self, docker_client):
        self.client = docker_client

    def compile(
        self,
        container,
        language_config: LanguageConfig,
    ) -> CompileResult:

        if container is None:

            return CompileResult(
                status="ERROR",
                logs="Container not found!",
                status_code=-1,
            )

        try:

            # Interpreted language
            if language_config.compile_command is None:

                return CompileResult(
                    status="SUCCESS",
                    logs="",
                    status_code=0,
                )

            response = container.exec_run(
                cmd=language_config.compile_command
            )

            logs = response.output.decode(
                "utf-8",
                errors="replace",
            )

            status = (
                "SUCCESS"
                if response.exit_code == 0
                else "COMPILATION ERROR"
            )

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