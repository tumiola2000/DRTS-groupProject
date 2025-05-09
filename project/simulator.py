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
        # collect all tasks belonging to this component
        comp.tasks = [t for t in tasks if t.component_id == comp.component_id]
        # track remaining budget in each replenishment period
        comp.budget_left = comp.budget
        # schedule next budget refill at time = comp.period
        comp.next_replenish = comp.period

    for core in cores:
        # assign each component to its core
        core.components = [c for c in budgets if c.core_id == core.core_id]
        # start the core’s clock at 0
        core.current_time = 0.0

    return cores

def simulate_core(core: Core, horizon: float
                 ) -> Dict[str, Dict[str, float]]:
    """
    Run a discrete-event simulation on a single core until 'horizon'.
    Returns per-task metrics: avg/max response and missed-deadline flag,
    plus the configured supply utilization.
    """
    # priority queue of upcoming events (release/replenish)
    events: List[Event] = []

    # initialize events at t=0
    for comp in core.components:
        # first budget replenish at time 0
        heapq.heappush(events, Event(0.0, 'replenish', comp))
        for task in comp.tasks:
            # prepare task fields for simulation
            task.next_release = 0.0
            task.remaining = 0.0
            task.response_times = []
            # first job release at time 0
            # DEBUG: log initial release scheduling
            #print(f"[DEBUG] Scheduling first release of {task.task_name} at t=0")
            heapq.heappush(events, Event(0.0, 'release', task))

    # we'll keep a working set of components that have ready jobs & budget
    ready_components = set()

    # main event loop
    while events and core.current_time < horizon:
        ev = heapq.heappop(events)
        core.current_time = ev.time

        if ev.kind == 'replenish':
            # refill the component’s budget
            comp: Component = ev.obj
            comp.budget_left = comp.budget
            comp.next_replenish = core.current_time + comp.period
            # schedule the next replenish event
            heapq.heappush(events,
                Event(comp.next_replenish, 'replenish', comp))
            # if there are unfinished jobs in this component, make it runnable
            if any(t.remaining > 0 for t in comp.tasks):
                ready_components.add(comp)

        else:  # ev.kind == 'release'
            # release a new job of this task
            task: Task = ev.obj
            # scale its WCET by the core’s speed factor
             # DEBUG: log each release event
            #print(f"[DEBUG] Release of {task.task_name} at t={core.current_time:.2f}")
            task.remaining = task.wcet / core.speed_factor
            task.release_time = core.current_time
            task.deadline = core.current_time + task.period
            # schedule this task’s next release
            task.next_release += task.period
            heapq.heappush(events,
                Event(task.next_release, 'release', task))
            # mark its parent component runnable
            parent = next(c for c in core.components
                          if c.component_id == task.component_id)
            ready_components.add(parent)

        # if no component is ready, skip ahead to the next event
        if not ready_components:
            continue

        # 1) Select which component to run (core-level EDF or RM)
        if core.scheduler == 'EDF':
            # pick component whose *earliest* ready-job deadline is smallest
            comp = min(
                ready_components,
                key=lambda c: min(t.deadline for t in c.tasks if t.remaining > 0)
            )
        else:  # RM (fixed priority)
            comp = min(ready_components, key=lambda c: c.priority)

        # 2) Within that component, pick which task to run
        runnable = [t for t in comp.tasks if t.remaining > 0]
        if comp.scheduler == 'EDF':
            task = min(runnable, key=lambda t: t.deadline)
        else:  # FPS (Rate Monotonic)
            task = min(runnable, key=lambda t: t.priority)

        # determine how far we can execute before the next scheduling event:
        next_ev_time = events[0].time if events else horizon
        run_until = min(
            core.current_time + comp.budget_left,    # until budget runs out
            core.current_time + task.remaining,      # until job finishes
            next_ev_time                            # until next queued event
        )
        run_time = run_until - core.current_time

        # consume CPU time from both component budget and task execution
        comp.budget_left -= run_time
        task.remaining -= run_time
        core.current_time = run_until

        # if the job completed, record its response time
        if task.remaining <= 0:
            rt = core.current_time - task.release_time
            task.response_times.append(rt)

        # if component’s budget is gone, it can’t run further until next replenish
        if comp.budget_left <= 0:
            ready_components.discard(comp)

        # if the current job still has work, keep the component ready
        if task.remaining > 0:
            ready_components.add(comp)

    # once the simulation ends, compute metrics
    metrics: Dict[str, Dict[str, float]] = {}
    for comp in core.components:
        # the configured supply utilization Q/P
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
    # parse your CSVs
    tasks  = parse_task()
    bufs   = parse_budget()
    cores  = parse_cores()

    # assemble the full system hierarchy
    system = build_system(tasks, bufs, cores)

    # simulate for one hyperperiod (LCM of all task periods)
    horizon = 1
    for t in tasks:
        horizon = lcm(int(horizon), int(t.period))

    # DEBUG: print the hyperperiod and task periods
    # print(f"\nComputed hyperperiod (horizon): {horizon}\n")
    # print("Task periods and divisibility check:")
    # for task in tasks:
    #     p = task.period
    #     div = horizon / p
    #     ok = isclose(div, round(div), rel_tol=1e-9)
    #     status = "OK" if ok else "✗"
    #     print(f"  {task.task_name:10s} period={p:5.2f}  horizon/period={div:.4f} → {status}")
    # print()

    print("Simulation results\n" + "-"*40)
    # run each core independently
    for core in system:
        print(f"\nCore {core.core_id} (speed={core.speed_factor}, sched={core.scheduler})")
        results = simulate_core(core, horizon)
        # print per-task metrics
        for name, m in results.items():
            print(f"  {name:20s} avg={m['avg_rt']:.2f}  max={m['max_rt']:.2f}  "
                  f"missed={m['missed']}  sup_util={m['sup_util']:.2f}")

if __name__ == "__main__":
    main()