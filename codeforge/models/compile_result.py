from dataclasses import dataclass


@dataclass
class CompileResult:
    status: str
    logs: str
    status_code: int