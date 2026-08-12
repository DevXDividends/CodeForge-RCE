import os
import shutil


class WorkspaceManager:

    PRESERVE_FILES = {
        ".gitkeep",
        "code.cpp",
    }

    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)

        os.makedirs(
            self.workspace_path,
            exist_ok=True
        )

    def write_code(self, code: str) -> str:

        code_path = os.path.join(
            self.workspace_path,
            "code.cpp"
        )

        with open(
            code_path,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(code)

        return code_path

    def write_input(self, input_data: str | None) -> str:

        input_path = os.path.join(
            self.workspace_path,
            "input.txt"
        )

        with open(
            input_path,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(input_data or "")

        return input_path

    def cleanup(self):

        if not os.path.isdir(self.workspace_path):
            return

        for item in os.listdir(self.workspace_path):

            if item in self.PRESERVE_FILES:
                continue

            path = os.path.join(
                self.workspace_path,
                item
            )

            try:

                if (
                    os.path.isfile(path)
                    or os.path.islink(path)
                ):
                    os.remove(path)

                elif os.path.isdir(path):
                    shutil.rmtree(path)

            except OSError:
                pass