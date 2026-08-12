from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LanguageConfig:
    name: str
    source_file: str
    compile_command: Optional[str]
    run_command: str