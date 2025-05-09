import csv
from parser import parse_task, parse_budget, parse_cores
from fixed_budget_sch import build_system as build_analysis_system, is_component_schedulable  # analysis functions
from simulator import build_system as build_sim_system, simulate_core                              # simulation functions
from math import lcm

def main():
    # Parse input files
    tasks = parse_task()
    budgets = parse_budget()
    cores = parse_cores()

    # Build systems for analysis and simulation
    analysis_system = build_analysis_system(tasks, budgets, cores)
    sim_tasks = parse_task()
    sim_budgets = parse_budget()
    sim_cores = parse_cores()
    simulation_system = build_sim_system(sim_tasks, sim_budgets, sim_cores)

    # Compute hyperperiod for simulation horizon
    horizon = 1
    for t in sim_tasks:
        horizon = lcm(horizon, int(t.period))

    # Precompute component-level analysis results
    comp_analysis = {}
    for core in analysis_system:
        for comp in core.components:
            ok, _ = is_component_schedulable(comp)
            comp_analysis[comp.component_id] = ok

    # Simulate each core and collect per-task metrics
    sim_results = {}
    for core_s in simulation_system:
        res = simulate_core(core_s, horizon)
        sim_results.update(res)

    # Prepare solution.csv
    out_file = "solution_large.csv"
    with open(out_file, "w", newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow([
            "task_name", "component_id", "task_schedulable",
            "avg_response_time", "max_response_time", "component_schedulable"
        ])
        # Write rows per task
        for task in sim_tasks:
            comp_id = task.component_id
            # Analysis: component-level schedulability
            comp_sched = 1 if comp_analysis.get(comp_id, False) else 0
            # Simulation metrics
            m = sim_results.get(task.task_name, {})
            avg_rt = m.get('avg_rt', 0.0)
            max_rt = m.get('max_rt', 0.0)
            missed = m.get('missed', False)
            task_sched = 0 if missed else 1
            writer.writerow([
                task.task_name,
                comp_id,
                task_sched,
                f"{avg_rt:.3f}",
                f"{max_rt:.3f}",
                comp_sched
            ])

    print(f"Solution written to {out_file}")

if __name__ == "__main__":
    main()
