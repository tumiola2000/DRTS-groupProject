from dataclasses import dataclass
from typing import Optional

@dataclass
class Task:
    task_name: str
    wcet: int
    period: int
    component_id: str
    priority: Optional[int]