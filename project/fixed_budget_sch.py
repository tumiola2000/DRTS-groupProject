from parser import parse_task, parse_budget, parse_cores
from math import lcm

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
def dbf(tasks, t):
    """EDF demand‐bound for implicit‐deadline jobs."""
    return sum(int(t // task.period) * task.wcet for task in tasks)

def sbf(component, t: float) -> float:
    """BDR supply bound with budget Q and period P."""
    Q, P = component.budget, component.period
    alpha = Q / P
    delta = P - Q
    return max(0.0, alpha * (t - delta))

# TEsting inequilities 
def scheduling_points(tasks):
    periods = [tau.period for tau in tasks]
    horizon = lcm(*map(int, periods))
    pts = set()
    for T in periods:
        for k in range(1, int(horizon // T) + 1):
            pts.add(k * T)
    return sorted(pts)

# Cheks if component is schedulable
def is_component_schedulable(comp):
    pts = scheduling_points(comp.tasks)
    for t in pts:
        # Computing if the tasks demand for CPU is less than the supply bound. If the demand is greater than the supply, then the system is not schedulable.
        if dbf(comp.tasks, t) > sbf(comp, t):
            return False, t
    return True, None


def main():
    # Parse the input files
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
            # ok, miss_t = is_component_schedulable(comp)
            # if ok:
            #     print(f"  • {comp.component_id}: Schedulable")
            # else:
            #     print(f"  • {comp.component_id}: Miss at t={miss_t}")
            Q     = comp.budget
            P     = comp.period
            alpha = Q / P                # utilization
            delta = P - Q                # worst-case delay

            # check schedulability
            ok, miss_t = is_component_schedulable(comp)
            status = "Schedulable" if ok else f"Miss at t={miss_t}"

            # print full stats
            print(f"  • {comp.component_id}: "
                  f"α={alpha:.3f}, Δ={delta:.3f}, "
                  f"Q={Q}, P={P} → {status}")
        print()



if __name__ == "__main__":
    main()