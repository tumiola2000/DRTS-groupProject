from dataclasses import dataclass, field
from typing import List
from .components import Component

@dataclass
class Core:
    core_id: str
    speed_factor: float
    scheduler: str          # top-level scheduler (e.g. 'EDF')
    components: List[Component] = field(default_factory=list)