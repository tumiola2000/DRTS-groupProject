#!/usr/bin/env python3
import csv
import heapq
import statistics
from math import lcm
from parser import parse_task, parse_budget, parse_cores
from models.cores import Core

# A tiny event type for our discrete‐event sim
class Event:
    __slots__ = ("time","kind","obj")
    def __init__(self, time: float, kind: str, obj):
        self.time = time
        self.kind = kind    # "release" or "replenish"
        self.obj = obj
    def __lt__(self, other): 
        return self.time < other.time

def build_system(tasks, budgets, cores):
    # attach tasks → components
    for comp in budgets:
        comp.tasks = [t for t in tasks if t.component_id == comp.component_id]
        comp.budget_left = comp.budget
        comp.next_replenish = comp.period
    # attach components → cores
    for core in cores:
        core.components = [c for c in budgets if c.core_id == core.core_id]
        core.current_time = 0.0
    return cores

def simulate_core(core: Core, horizon: float):
    """ Run until `horizon`, return dict task_name→{avg_rt,max_rt,missed}. """
    # event queue
    evq = []
    # init: at t=0, each comp gets replenish, each task gets release
    for comp in core.components:
        heapq.heappush(evq, Event(0.0, "replenish", comp))
        for t in comp.tasks:
            t.next_release = 0.0
            t.remaining    = 0.0
            t.response_times = []
            heapq.heappush(evq, Event(0.0, "release", t))

    ready_comps = set()
    # run
    while evq and core.current_time < horizon:
        ev = heapq.heappop(evq)
        core.current_time = ev.time

        if ev.kind == "replenish":
            c = ev.obj
            c.budget_left = c.budget
            c.next_replenish = core.current_time + c.period
            heapq.heappush(evq, Event(c.next_replenish, "replenish", c))
            # if any jobs still pending in c, make it ready
            if any(t.remaining>0 for t in c.tasks):
                ready_comps.add(c)

        else:  # release
            job = ev.obj
            job.remaining    = job.wcet / core.speed_factor
            job.release_time = core.current_time
            job.deadline     = core.current_time + job.period
            job.next_release += job.period
            heapq.heappush(evq, Event(job.next_release, "release", job))
            parent = next(c for c in core.components if c.component_id==job.component_id)
            ready_comps.add(parent)

        # pick nothing if no work
        if not ready_comps:
            continue

        # only keep components that still have work + budget
        active = [c for c in ready_comps if c.budget_left>0 and any(t.remaining>0 for t in c.tasks)]
        if not active:
            continue

        # core‐level pick
        if core.scheduler=="EDF":
            comp = min(active, key=lambda c: min(t.deadline for t in c.tasks if t.remaining>0))
        else:  # RM at core
            comp = min(active, key=lambda c: c.priority)

        # task‐level pick
        runnables = [t for t in comp.tasks if t.remaining>0]
        if comp.scheduler=="EDF":
            task = min(runnables, key=lambda t: t.deadline)
        else:
            task = min(runnables, key=lambda t: t.priority)

        # how far can we run?
        next_evt = evq[0].time if evq else horizon
        run_until = min(core.current_time + comp.budget_left,
                        core.current_time + task.remaining,
                        next_evt)
        dt = run_until - core.current_time

        # consume
        comp.budget_left -= dt
        task.remaining    -= dt
        core.current_time  = run_until

        # finished job?
        if task.remaining<=0:
            rt = core.current_time - task.release_time
            task.response_times.append(rt)

        # update ready set
        if comp.budget_left<=0:
            ready_comps.discard(comp)
        if task.remaining>0:
            ready_comps.add(comp)

    # aggregate metrics
    out = {}
    for c in core.components:
        sup_util = c.budget / c.period
        for t in c.tasks:
            rts = t.response_times
            out[t.task_name] = {
                "avg_rt": statistics.mean(rts) if rts else 0.0,
                "max_rt": max(rts) if rts else 0.0,
                "missed": any(rt>t.period for rt in rts),
                "sup_util": sup_util
            }
    return out

def main():

    tasks   = parse_task()
    budgets = parse_budget()
    cores   = parse_cores()
    sim_sys = build_system(tasks, budgets, cores)
    
    horizon=1
    for t in tasks:
        H = lcm(horizon, int(t.period))

    sim_results = {}
    for core in sim_sys:
        sim_results.update(simulate_core(core, H))

    # 3) per‐component sched (all tasks must be non‐missed)
    comp_sched = {}
    for comp in budgets:
        comp_sched[comp.component_id] = all(not sim_results[t.task_name]["missed"]
                                             for t in comp.tasks)

    # 4) write solution.csv
    with open("simulator.csv","w",newline="") as f:
        w=csv.writer(f)
        w.writerow(["task_name","component_id","task_schedulable",
                    "avg_response_time","max_response_time","sup_util","component_schedulable"])
        for t in tasks:
            m = sim_results[t.task_name]
            w.writerow([
                t.task_name,
                t.component_id,
                0 if m["missed"] else 1,
                f"{m['avg_rt']:.3f}",
                f"{m['max_rt']:.3f}",
                f"{m['sup_util']:.3f}",
                1 if comp_sched[t.component_id] else 0
            ])

    print("→ simulation done, wrote solution.csv")

if __name__=="__main__":
    main()
