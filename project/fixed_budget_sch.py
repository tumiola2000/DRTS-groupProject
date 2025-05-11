from parser import parse_task, parse_budget, parse_cores
from math import gcd
from functools import reduce
from math import floor

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

# This is analysis code for the system
def dbf(tasks, t, speed):
    """EDF demand-bound for implicit‐deadline jobs."""
    return sum(floor(t // task.period) * (task.wcet / speed) for task in tasks)

def sbf(component, t):
    """BDR supply bound with budget Q and period P."""
    Q, P = component.budget, component.period
    alpha = Q / P
    delta = P - Q
    return max(0.0, alpha * (t - delta))

def scheduling_points(component):
    """
    Return all t = k*P and t = k*D (D = P-Q) up to the hyperperiod.
    """
    P = int(component.period)
    Q = component.budget
    D = P - Q

    # compute hyperperiod over the sub‐task periods
    periods = [int(t.period) for t in component.tasks]
    hyper = reduce(lambda a, b: a * b // gcd(a, b), periods, 1)
    pts = set()
    for k in range(1, hyper // P + 1):
        pts.add(k * P)

    if D > 0:
        n = int(hyper // D)
        for k in range(1, n + 1):
            pts.add(k * D)
    return sorted(pts)


# Cheks if component is schedulable
def is_component_schedulable(comp, speed):
    pts = scheduling_points(comp)
    for t in pts:
        # Computing if the tasks demand for CPU is less than the supply bound. If the demand is greater than the supply, then the system is not schedulable.
        if dbf(comp.tasks, t, speed) > sbf(comp, t):
            return False, t
    return True, None


def main():
    tasks = parse_task()
    budgets = parse_budget()
    cores = parse_cores()
    system = build_system(tasks, budgets, cores)

    print("System built successfully.")
    print("Fixed Budget Scheduling Analysis")
    print("===================================")

    for core in system:
        print(f"-- Core {core.core_id} --")
        for comp in core.components:
            Q     = comp.budget
            P     = comp.period
            alpha = Q / P                
            delta = P - Q               

            # check schedulability
            ok, miss_t = is_component_schedulable(comp, core.speed_factor)
            status = "Schedulable" if ok else f"Miss at t={miss_t}"

            # print full stats
            print(f" {comp.component_id}: "
                  f"alpha={alpha:.3f}, Delta={delta:.3f}, "
                  f"Q={Q}, P={P} -> {status}")
        print()



if __name__ == "__main__":
    main()