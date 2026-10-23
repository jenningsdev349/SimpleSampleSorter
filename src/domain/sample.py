from dataclasses import dataclass

from anyio import Path

from domain.category import Category

@dataclass
class Sample:
    path: Path
    category: Category
    confidence: float
    duration: float
    user_override: bool = False