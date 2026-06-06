import docker 
from docker.errors import DockerException
import os
import requests


client = docker.from_env()## used to make connection to the docker daemon running on the machine

host_path = os.path.abspath("workspace")
def execute_code():
    host_path = os.path.abspath("workspace")
    container = None
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
        network_disabled=True,
        mem_limit="128m",
        pids_limit=64
        )
        result = container.wait(timeout=5)
        logs = container.logs().decode()
        container.reload()
        state = container.attrs["State"]
        if(state["OOMKilled"]):
            return {
        "status": "MLE",
        "logs": "Memory Limit Exceeded",
        "status_code": 137
        }
        return {
            "status":"SUCCESS" if result["StatusCode"]==0 else "ERROR",
            "logs":logs,
            "status_code":result["StatusCode"]
        }

    except requests.exceptions.ConnectionError:
        if container:
            try:
                 container.kill()
            except:
                pass
        return {
            "status": "TLE",
            "logs": "Time Limit Exceeded (5 seconds)",
            "status_code": -1
        }
    except DockerException as e:

        return {
            "status": "DOCKER_ERROR",
            "logs": str(e),
            "status_code": -1
        }
    finally:
        if container:
            try:
                container.remove(force=True)
            except:
                pass