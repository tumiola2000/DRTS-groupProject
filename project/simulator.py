import heapq
import statistics
from dataclasses import dataclass, field
from typing import Any, List, Dict
from math import lcm, isclose

from parser import parse_task, parse_budget, parse_cores
from models.tasks import Task
from models.components import Component
from models.cores import Core

# An event in the simulation (either a task release or a budget replenish)
@dataclass(order=True)
class Event:
    time: float              # simulation time at which event happens
    kind: str                # 'release' or 'replenish'
    obj: Any = field(compare=False)  # the Task or Component associated


def build_system(tasks: List[Task],
                 budgets: List[Component],
                 cores: List[Core]) -> List[Core]:
    """
    Attach tasks to their components and initialize per-component budget state.
    Then attach components to their designated cores and reset core time.
    """
    for comp in budgets:
        comp.tasks = [t for t in tasks if t.component_id == comp.component_id]
        comp.budget_left = comp.budget
        comp.next_replenish = comp.period

    for core in cores:
        core.components = [c for c in budgets if c.core_id == core.core_id]
        core.current_time = 0.0

    return cores


def simulate_core(core: Core, horizon: float) -> Dict[str, Dict[str, float]]:
    """
    Run a discrete-event simulation on a single core until 'horizon'.
    Returns per-task metrics: avg/max response and missed-deadline flag,
    plus the configured supply utilization.
    """
    events: List[Event] = []

    # initialize events at t=0
    for comp in core.components:
        heapq.heappush(events, Event(0.0, 'replenish', comp))
        for task in comp.tasks:
            task.next_release = 0.0
            task.remaining = 0.0
            task.response_times = []
            heapq.heappush(events, Event(0.0, 'release', task))

    ready_components = set()

    while events and core.current_time < horizon:
        ev = heapq.heappop(events)
        core.current_time = ev.time

        if ev.kind == 'replenish':
            comp: Component = ev.obj
            comp.budget_left = comp.budget
            comp.next_replenish = core.current_time + comp.period
            heapq.heappush(events, Event(comp.next_replenish, 'replenish', comp))
            if any(t.remaining > 0 for t in comp.tasks):
                ready_components.add(comp)
        else:
            task: Task = ev.obj
            task.remaining = task.wcet / core.speed_factor
            task.release_time = core.current_time
            task.deadline = core.current_time + task.period
            task.next_release += task.period
            heapq.heappush(events, Event(task.next_release, 'release', task))
            parent = next(c for c in core.components if c.component_id == task.component_id)
            ready_components.add(parent)

        if not ready_components:
            continue

        # Filter to components that actually have ready jobs
        active_comps = [c for c in ready_components if any(t.remaining > 0 for t in c.tasks)]
        if not active_comps:
            continue

        # Core-level scheduling
        if core.scheduler == 'EDF':
            comp = min(
                active_comps,
                key=lambda c: min(t.deadline for t in c.tasks if t.remaining > 0)
            )
        else:
            comp = min(active_comps, key=lambda c: c.priority)

        # Task-level: pick only tasks with work
        runnable = [t for t in comp.tasks if t.remaining > 0]
        if not runnable:
            ready_components.discard(comp)
            continue

        if comp.scheduler == 'EDF':
            task = min(runnable, key=lambda t: t.deadline)
        else:
            task = min(runnable, key=lambda t: t.priority)

        # determine next run window
        next_ev_time = events[0].time if events else horizon
        run_until = min(
            core.current_time + comp.budget_left,
            core.current_time + task.remaining,
            next_ev_time
        )
        run_time = run_until - core.current_time

        comp.budget_left -= run_time
        task.remaining -= run_time
        core.current_time = run_until

        if task.remaining <= 0:
            rt = core.current_time - task.release_time
            task.response_times.append(rt)

        if comp.budget_left <= 0:
            ready_components.discard(comp)
        if task.remaining > 0:
            ready_components.add(comp)

    # compute metrics
    metrics: Dict[str, Dict[str, float]] = {}
    for comp in core.components:
        sup_util = comp.budget / comp.period
        for t in comp.tasks:
            rts = t.response_times
            metrics[t.task_name] = {
                'avg_rt':  statistics.mean(rts) if rts else 0.0,
                'max_rt':  max(rts) if rts else 0.0,
                'missed':  any(rt > t.period for rt in rts),
                'sup_util': sup_util
            }
    return metrics


def main():
    tasks  = parse_task()
    bufs   = parse_budget()
    cores  = parse_cores()

    system = build_system(tasks, bufs, cores)

    horizon = 1
    for t in tasks:
        horizon = lcm(int(horizon), int(t.period))

    print("Simulation results\n" + "-"*40)
    for core in system:
        print(f"\nCore {core.core_id} (speed={core.speed_factor}, sched={core.scheduler})")
        results = simulate_core(core, horizon)
        for name, m in results.items():
            print(f"  {name:20s} avg={m['avg_rt']:.2f}  max={m['max_rt']:.2f}  "
                  f"missed={m['missed']}  sup_util={m['sup_util']:.2f}")

if __name__ == "__main__":
    main()