import os
import docker 
import queue
import threading
import shutil
import time

client = docker.from_env()## used to make connection to the docker daemon running on the machine

## Constants
DEFAULT_TIMEOUT = 2
MEMORY_LIMIT = "128m"
PIDS_LIMIT = 64

def create_container(host_path):
    try:

        container =client.containers.create(
            image="codeforge-rce",
            command="sleep infinity",
            network_disabled=True,
            mem_limit=MEMORY_LIMIT,
            pids_limit=PIDS_LIMIT,
             volumes={
            host_path:{
                "bind":"/app",
                 "mode":"rw"
            }
        },
        )
        container.start()
        container.reload()
        
        return container
        
    except docker.errors.DockerException as e:
        print("Gadbad ! 🤔",e)
        return None
   


def compile_code(container):
    if not container:
        return {
            "status":"ERROR",
            "logs":"Container not found!",
            "status_code":-1
        }
    try:
        response = container.exec_run(
            cmd = "g++ /app/code.cpp -o /app/out"
        )
        return {
          "status":"SUCCESS" if response.exit_code == 0 else "COMPILATION ERROR",
          "logs":response.output.decode(),
          "status_code":response.exit_code
        }

    except docker.errors.DockerException as e:
          return {
            "status": "DOCKER_ERROR",
            "logs": str(e),
            "status_code": -1
        }

def worker(exec_id: str, result_queue: queue.Queue):
    try:
        output = client.api.exec_start(exec_id=exec_id)
        info = client.api.exec_inspect(exec_id=exec_id)

        result_queue.put({
            "output": output,
            "info": info
        })

    except Exception as e:
        result_queue.put({
            "error": str(e)
        })

        
def run_code(container,host_path, timeout=DEFAULT_TIMEOUT, input_data=None):

    if container is None:
        return {
            "status": "ERROR",
            "stdout": "",
            "status_code": -1
        }

    result_queue = queue.Queue()

    input_file = os.path.join(host_path, "input.txt")

    try:

        # ----------------------------------
        # Always create input.txt
        # ----------------------------------

        with open(input_file, "w", encoding="utf-8") as f:
            f.write(input_data or "")
    

        command = ["sh", "-c", "/app/out < /app/input.txt"]

        # ----------------------------------
        # Create exec
        # ----------------------------------
        exec_obj = client.api.exec_create(
            container=container.id,
            cmd=command,
            stdout=True,
            stderr=True
        )

        exec_id = exec_obj["Id"]

        thread = threading.Thread(
            target=worker,
            args=(exec_id, result_queue),
            daemon=True
        )

        # ----------------------------------
        # Start timer
        # ----------------------------------

        start = time.perf_counter()

        thread.start()
        thread.join(timeout)

        end = time.perf_counter()

        execution_time = round((end - start) * 1000, 3)

        # ----------------------------------
        # TLE
        # ----------------------------------

        if thread.is_alive():

            try:
                container.kill()
            except docker.errors.APIError:
                pass

            thread.join(timeout=1)

            return {
                "status": "TLE",
                "stdout": "Time Limit Exceeded",
                "status_code": -1,
                "execution_time_ms": execution_time
            }

        # ----------------------------------
        # Worker failed
        # ----------------------------------

        if result_queue.empty():
            return {
                "status": "ERROR",
                "stdout": "Worker returned no result",
                "status_code": -1,
                "execution_time_ms": execution_time
            }

        result = result_queue.get()

        if "error" in result:
            return {
                "status": "DOCKER_ERROR",
                "stdout": result["error"],
                "status_code": -1,
                "execution_time_ms": execution_time
            }

        output = result["output"]
        info = result["info"]

        container.reload()

        state = container.attrs["State"]

        # ----------------------------------
        # Memory Limit
        # ----------------------------------

        if state.get("OOMKilled", False):
            return {
                "status": "MLE",
                "stdout": "Memory Limit Exceeded",
                "status_code": 137,
                "execution_time_ms": execution_time
            }

        # ----------------------------------
        # Peak Memory (if available)
        # ----------------------------------

        memory_mb = None

        try:
            stats = container.stats(stream=False)

            memory = stats["memory_stats"].get(
                "max_usage",
                stats["memory_stats"].get("usage", 0)
            )

            memory_mb = round(memory / (1024 * 1024), 2)

        except Exception:
            pass

        exit_code = info["ExitCode"]

        runtime_map = {
            0: ("SUCCESS", "Program executed successfully"),
            132: ("ILLEGAL_INSTRUCTION", "Illegal instruction"),
            134: ("ABORTED", "Program aborted"),
            136: ("FLOATING_POINT_EXCEPTION", "Floating point exception"),
            137: ("KILLED", "Process killed"),
            139: ("SEGMENTATION_FAULT", "Segmentation fault"),
        }

        status, default_msg = runtime_map.get(
            exit_code,
            ("RUNTIME_ERROR", "Runtime Error")
        )

        stdout = output.decode("utf-8", errors="replace")

        if stdout.strip() == "" and exit_code != 0:
            stdout = default_msg

        return {
            "status": status,
            "stdout": stdout,
            "status_code": exit_code,
            "execution_time_ms": execution_time,
            "memory_mb": memory_mb
        }

    except docker.errors.DockerException as e:

        return {
            "status": "DOCKER_ERROR",
            "stdout": str(e),
            "status_code": -1
        }

    finally:

          cleanup(
        container=container,
        workspace_path=host_path
    )
        

PRESERVE_FILES = {
    ".gitkeep",
    "code.cpp"
}

def cleanup(container=None, workspace_path=None):

    # --------------------------
    # Remove Docker Container
    # --------------------------

    if container is not None:
        try:
            container.remove(force=True)
        except docker.errors.DockerException:
            pass

    # --------------------------
    # Clean Workspace
    # --------------------------

    if workspace_path and os.path.isdir(workspace_path):

        for item in os.listdir(workspace_path):

            # Skip preserved files
            if item in PRESERVE_FILES:
                continue

            path = os.path.join(workspace_path, item)

            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)

                elif os.path.isdir(path):
                    shutil.rmtree(path)

            except OSError:
                pass


def CodeForgeRCE(code:str,input = None):
   
    if not code:
        return {
            "error":"Code not provided"
        }
    # put the code in  a file 
    with open("workspace/code.cpp",'w') as file:
        file.write(code)

    host_path = os.path.abspath("workspace")
    container = create_container(
        host_path=host_path
        )

    response = compile_code(
        container=container
        )


    if response["status_code"]!=0:
                return {
                      "status":response["status"],
                      "logs":response["logs"],
                      "status_code":response["status_code"]
                }
    else:
        output = run_code(
            container=container,
            timeout=2,
            input_data= input,
            host_path=host_path
            )
        return {
            "status": output["status"],
            "stdout": output["stdout"],
            "status_code":output["status_code"],
            "execution_time_ms":output["execution_time_ms"],
            "memory": output["memory_mb"]
        }
