import docker 
from docker.errors import DockerException
import os

client = docker.from_env()## used to make connection to the docker daemon running on the machine

host_path = os.path.abspath("workspace")
def execute_code():
    host_path = os.path.abspath("workspace")
    try:
        container = client.containers.run(
        image="codeforge-cpp",
        command='sh -c "g++ /app/code.cpp -o /app/out && /app/out"',
        volumes={
            host_path:{
                "bind":"/app",
                 "mode":"rw"
            }
        },
        detach=True,
        remove=True
        )
        result = container.wait()
        logs = container.logs().decode()
        return {
            "logs":logs,
            "status_code":result["StatusCode"]
        }

    except DockerException as e:
        return str(e)
        




  



