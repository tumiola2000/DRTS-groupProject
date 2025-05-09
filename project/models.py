from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Task:
    task_name: str
    wcet: int
    period: int
    component_id: str
    priority: Optional[int]

@dataclass
class Component:
    component_id: str
    scheduler: str          # 'RM' or 'EDF'
    budget: int
    period: int             # for the BDR interface
    core_id: str
    priority: Optional[int]
    tasks: List[Task] = field(default_factory=list)

@dataclass
class Core:
    core_id: str
    speed_factor: float
    scheduler: str          # top-level scheduler (e.g. 'EDF')
    components: List[Component] = field(default_factory=list)