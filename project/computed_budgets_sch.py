from math import floor, lcm
from typing import List, Tuple
from parser import parse_task, parse_budget, parse_cores
from models.tasks import Task
from models.components import Component

# Builds our system 
def build_system(tasks, budgets, cores):
    for budget in budgets:
        for task in tasks:
            if task.component_id == budget.component_id:
                budget.tasks.append(task)
    
    for core in cores:
        for budget in budgets:
            if budget.core_id == core.core_id:
                core.components.append(budget) 

    return cores

# ------------------------------------------------------------
# 1) Demand-Bound Functions (EDF & FPS), with WCET scaling
# ------------------------------------------------------------
def dbf_edf(tasks: List[Task], t: float, speed: float) -> float:
    """EDF dbf for implicit deadlines, scaling WCET by core speed."""
    return sum(floor(t / tau.period) * (tau.wcet / speed) for tau in tasks)

def dbf_fps(tasks: List[Task], t: float, target: Task, speed: float) -> float:
    """
    FPS (RM) dbf for task 'target', scaling WCET by core speed:
      C_target/speed + Σ_{hp} ⌈t/T_k⌉·(C_k/speed)
    hp = higher-priority tasks under RM.
    """
    demand = 0.0
    for τ in tasks:
        # only consider tasks whose RM-priority ≤ the target’s
        if τ.priority is not None and τ.priority <= target.priority:
            # count only jobs whose deadlines ≤ t
            count = floor((t - τ.period) / τ.period) + 1
            if count > 0:
                demand += count * (τ.wcet / speed)
    return demand

# ------------------------------------------------------------
# 2) BDR Supply-Bound Function
# ------------------------------------------------------------
def sbf_bdr(alpha: float, delta: float, t: float) -> float:
    """BDR supply bound: max(0, α·(t - Δ))."""
    return max(0.0, alpha * (t - delta))

# ------------------------------------------------------------
# 3) Scheduling Points (Periods & Deadlines)
# ------------------------------------------------------------
def scheduling_points(servers: List) -> List[float]:
    """
    Collect critical points (multiples of P and D) up to hyperperiod.
    Each server has .period and .deadline.
    """
    periods = [srv.period for srv in servers]
    H = lcm(*map(int, periods))
    pts = set()
    for srv in servers:
        for k in range(1, int(H // srv.period) + 1):
            pts.add(k * srv.period)
            pts.add(k * srv.deadline)
    return sorted(pts)

# ------------------------------------------------------------
# 4) Compute BDR Interface (α, Δ) per component
# ------------------------------------------------------------
def compute_bdr_interface(comp: Component,
                          speed: float,
                          alpha_step: float = 0.001,
                          delta_step: float = 0.1
                         ) -> Tuple[float,float]:
    """
    Find minimal (α, Δ) s.t. ∀t: dbf ≤ sbf_bdr, using tasks in comp,
    with WCET scaled by core speed.
    """
    # time points: multiples of task periods
    task_periods = [tau.period for tau in comp.tasks]
    H = lcm(*map(int, task_periods))
    pts = sorted({k * T for T in task_periods for k in range(1, int(H // T) + 1)})

    # lower bound on α = total utilization (scaled WCET/period)
    U = sum((tau.wcet / speed) / tau.period for tau in comp.tasks)
    # HE is not overutilized
    # print(f"[DEBUG] Component {comp.component_id}: scaled utilization U = {U:.3f}")
    # if U > 1.0:
    #     raise RuntimeError(f"Component {comp.component_id} is over‐utilized (U={U:.3f}>1). No BDR interface possible.")

    best = None
    alpha = U
    while alpha <= 1.0:
        max_pt = lcm(*map(int, task_periods))   # allow Δ up to the hyperperiod
        Q = alpha * comp.period
        delta_min = comp.period - Q
        delta = max(0.0, delta_min)
        #delta = 0.0 creates a no delay system
        while delta <= max_pt:
            ok = True
            for t in pts:
                if comp.scheduler == 'EDF':
                    demand = dbf_edf(comp.tasks, t, speed)
                else:
                    demand = max(dbf_fps(comp.tasks, t, tau, speed) for tau in comp.tasks)
                supply = sbf_bdr(alpha, delta, t)
                if demand > supply:
                    ok = False
                    break
            if ok:
                best = (round(alpha,3), round(delta,3))
                break
            delta += delta_step
        if best:
            break
        alpha += alpha_step
    if not best:
        raise RuntimeError(f"No feasible BDR interface for component {comp.component_id}")
    return best

# ------------------------------------------------------------
# 5) Half-Half Transform → server task (Q, P, D)
# ------------------------------------------------------------
def half_half_server(alpha: float, delta: float, P: float) -> Tuple[float,float,float]:
    """
    Thm 3: BDR(α, Δ, P) ≡ server task (Q=αP, period=P, deadline=D=Δ).
    """
    Q = alpha * P
    D = delta
    return (Q, P, D)

# ------------------------------------------------------------
# 6) Core-Level Schedulability Test (Thm 1)
# ------------------------------------------------------------
def is_schedulable_core(servers: List[Tuple[float,float,float]],
                        scheduler: str) -> bool:
    """
    Test servers (Q,P,D) on core under EDF/RM:
    ∀t∈critical points, ∑⌊t/P⌋Q ≤ t.
    """
    class Srv:
        def __init__(self, Q,P,D):
            self.wcet = Q
            self.period = P
            self.deadline = D
    srvs = [Srv(Q,P,D) for Q,P,D in servers]

    pts = scheduling_points(srvs)
    for t in pts:
        if scheduler == 'EDF':
            demand = sum(floor(t/s.period) * s.wcet for s in srvs)
            if demand > t:
                return False
        else:
            # RM: check at each priority level
            sorted_srvs = sorted(srvs, key=lambda s: s.period)
            for i in range(len(sorted_srvs)):
                sub = sorted_srvs[:i+1]
                d_i = sum(floor(t/sj.period) * sj.wcet for sj in sub)
                if d_i > t:
                    return False
    return True


# ------------------------------------------------------------
# Main: compute and test BDR interfaces
# ------------------------------------------------------------
def main():
    tasks   = parse_task()
    budgets = parse_budget()
    cores   = parse_cores()
    system  = build_system(tasks, budgets, cores)

    # map core_id → speed_factor
    core_map = {core.core_id: core for core in cores}

    print("\n=== BDR Interfaces per Component ===")
    comp_servers = {}
    for comp in budgets:
        speed = core_map[comp.core_id].speed_factor
        alpha, delta = compute_bdr_interface(comp, speed)
        Q, P, D = half_half_server(alpha, delta, comp.period)
        comp_servers[comp.component_id] = (Q, P, D)
        print(f"Comp {comp.component_id}: alpha={alpha}, Delta={delta} -> (Q={Q:.2f},P={P},D={D:.2f})")

    print("\n=== Core-Level Schedulability (BDR) ===")
    for core in cores:
        servers = []
        for comp in budgets:
            if comp.core_id == core.core_id:
                Q, P, D = comp_servers[comp.component_id]
                # scale supply by speed: Q/speed
                #servers.append((Q / core.speed_factor, P, D)) # Might be double scaling
                servers.append((Q, P, D))
        ok = is_schedulable_core(servers, core.scheduler)
        print(f"Core {core.core_id} ({core.scheduler}): {'Schedulable' if ok else 'Not schedulable'}")



if __name__ == "__main__":
    main()
