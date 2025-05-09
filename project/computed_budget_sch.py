from math import floor
from typing import List, Tuple
from parser import parse_task, parse_budget, parse_cores
from models.tasks import Task
from models.components import Component
from models.cores import Core
from fixed_budget_sch import build_system


def dbf(tasks: List[Task], t: float) -> float:
    """EDF demand-bound for implicit deadlines."""
    return sum(floor(t / tau.period) * tau.wcet for tau in tasks)

def sbf_bdr(alpha: float, delta: float, t: float) -> float:
    """BDR supply-bound: alpha*(t-delta) but not below zero."""
    return max(0.0, alpha * (t - delta))

def scheduling_points(tasks: List[Task]) -> List[float]:
    """All deadlines up to the hyperperiod."""
    from math import lcm
    periods = [tau.period for tau in tasks]
    H = lcm(*map(int, periods))
    pts = set()
    for T in periods:
        for k in range(1, int(H // T) + 1):
            pts.add(k * T)
    return sorted(pts)

def compute_bdr_interface(comp: Component,
                          alpha_step: float = 0.005,
                          delta_step: float = 0.5
                         ) -> Tuple[float,float]:
    """
    Find the smallest (alpha, delta) such that:
      ∀t∈T: dbf(comp.tasks, t) <= sbf_bdr(alpha, delta, t).
    We fix the server period to comp.period and budget = alpha*period.
    """
    pts = scheduling_points(comp.tasks)
    # Lower bound on alpha is total utilization
    U = sum(tau.wcet/tau.period for tau in comp.tasks)

    best = None  # (alpha, delta)
    # scan alpha from U up to 1.0
    alpha = U
    while alpha <= 1.0:
        # for a given alpha, find the smallest delta that works
        # delta must lie in [0, max(pts)]
        maxT = max(pts)
        delta = 0.0
        ok = False
        while delta <= maxT:
            # check all points
            if all(dbf(comp.tasks, t) <= sbf_bdr(alpha, delta, t) for t in pts):
                ok = True
                break
            delta += delta_step
        if ok:
            best = (round(alpha,3), round(delta,3))
            break
        alpha += alpha_step

    if best is None:
        raise RuntimeError(f"No feasible BDR interface for component {comp.component_id}")

    return best

def is_schedulable_core(servers: List[Tuple[float,float,float]],  # list of (Q,P,deadline)
                        scheduler: str
                       ) -> bool:
    """
    Check top-level EDF/RM schedulability of a set of server tasks
    by DBF vs. flat supply (alpha=1, delta=0).
    servers: (Q, P, D) for each component.
    """
    # Build tasks with wcet=Q, period=P, deadline=D
    class S:
        def __init__(self, Q,P,D):
            self.wcet, self.period, self.deadline = Q,P,D
    sts = [S(Q,P,P) for Q,P,_ in servers]  # implicit deadlines = P
    pts = scheduling_points(sts)
    for t in pts:
        demand = sum(floor(t/s.period)*s.wcet for s in sts)
        supply = t  # flat CPU supply: 1*t
        if demand > supply:
            return False
    return True



def main():
    tasks   = parse_task()
    budgets = parse_budget()
    cores   = parse_cores()

    system = build_system(tasks, budgets, cores)

    print("\n=== Analysis of BDR Interfaces ===\n")
    # 1) Compute (alpha, delta) for each component
    comp_interfaces = {}
    for comp in budgets:
        alpha, delta = compute_bdr_interface(comp)
        Q = alpha * comp.period
        P = comp.period
        comp_interfaces[comp.component_id] = (alpha, delta, Q, P)
        print(f"Component {comp.component_id}: alpha={alpha:.2f}, delta={delta:.1f},  Q={Q:.1f}, P={P}")

    # 2) Check schedulability at core level
    print("\n=== Core-level schedulability ===\n")
    for core in cores:
        # gather this core’s components as servers
        servers = []
        for comp in budgets:
            if comp.core_id == core.core_id:
                alpha,delta,Q,P = comp_interfaces[comp.component_id]
                servers.append((Q,P,P))
        ok = is_schedulable_core(servers, core.scheduler)
        verdict = "Schedulable" if ok else "NOT schedulable"
        print(f"Core {core.core_id} ({core.scheduler}): {verdict}")

if __name__=="__main__":
    main()
