from dataclasses import dataclass, field
from pathlib import Path

from domain.sample import Sample


@dataclass(frozen=True)
class FailedFile:
    path: Path
    error: str

@dataclass(frozen=True)
class SortResult:
    source_folder: Path
    samples: list[Sample] = field(default_factory=list)
    failures: list[FailedFile] = field(default_factory=list)
    cancelled: bool = False

    @property
    def total_scanned(self) -> int:
        return len(self.samples) + len(self.failures)