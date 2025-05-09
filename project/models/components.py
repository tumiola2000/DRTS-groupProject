from dataclasses import dataclass, field
from typing import List, Optional
from .tasks import Task

@dataclass(eq=True)
class Component:
    component_id: str
    scheduler: str
    budget: int
    period: int
    core_id: str
    priority: Optional[int]
    tasks: List[Task] = field(default_factory=list)

    def __hash__(self):
        # only the ID matters for hashing
        return hash(self.component_id)
