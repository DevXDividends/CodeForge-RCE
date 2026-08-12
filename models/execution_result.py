from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionResult:
    status: str
    stdout: str
    status_code: int
    execution_time_ms: Optional[float] = None
    memory_mb: Optional[float] = None