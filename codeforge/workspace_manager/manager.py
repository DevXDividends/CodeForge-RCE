import os
import shutil
import tempfile


class WorkspaceManager:

    def __init__(
        self,
        base_dir: str | None = None,
    ):
        if base_dir is None:
            base_dir = tempfile.gettempdir()

        self.base_dir = os.path.abspath(
            base_dir
        )

        self.workspace_path = None

        self.ensure_workspace()

    def ensure_workspace(self):

        if (
            self.workspace_path is None
            or not os.path.isdir(self.workspace_path)
        ):
            self.workspace_path = tempfile.mkdtemp(
                prefix="codeforge-",
                dir=self.base_dir,
            )

    def write_code(
        self,
        code: str,
        filename: str,
    ) -> str:

        self.ensure_workspace()

        file_path = os.path.join(
            self.workspace_path,
            filename,
        )

        with open(
            file_path,
            "w",
            encoding="utf-8",
        ) as file:
            file.write(code)

        return file_path

    def write_input(
        self,
        input_data: str | None,
    ) -> str:

        self.ensure_workspace()

        file_path = os.path.join(
            self.workspace_path,
            "input.txt",
        )

        with open(
            file_path,
            "w",
            encoding="utf-8",
        ) as file:
            file.write(input_data or "")

        return file_path

    def cleanup(self):

        if (
            self.workspace_path is None
            or not os.path.exists(
                self.workspace_path
            )
        ):
            return

        shutil.rmtree(
            self.workspace_path,
            ignore_errors=True,
        )