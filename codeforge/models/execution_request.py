from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionRequest:
    code: str
    language: str = "cpp"
    stdin: Optional[str] = None
    timeout: float = 2.0