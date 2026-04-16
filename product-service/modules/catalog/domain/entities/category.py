from dataclasses import dataclass
from typing import Optional

@dataclass
class CategoryEntity:
    name: str
    description: str = ""
    id: Optional[int] = None

    def validate(self):
        if not self.name or not self.name.strip():
            raise ValueError("Category name cannot be empty")
