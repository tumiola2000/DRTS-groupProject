import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Task:
    task_name: str
    wcet: int
    period: int
    deadline: int
    priority: int
    component_id: str

@dataclass
class Component:
    component_id: str
    scheduler: str          # 'RM' or 'EDF' for tasks within this component
    budget: int
    period: int             # server period
    core_id: str
    priority: int           # for core-level RM
    tasks: List[Task] = field(default_factory=list)
    remaining_budget: int = 0

@dataclass
class Core:
    core_id: str
    speed_factor: float     # unused for now, assume 1.0
    scheduler: str          # 'RM' or 'EDF' at component level
    components: List[Component] = field(default_factory=list)

def load_system():
    directory = "4-large-test-case/"
    tasks_csv = directory + 'tasks.csv'
    budgets_csv = directory + 'budgets.csv'
    arch_csv = directory + 'architecture.csv'

    # Load tasks
    tasks_df = pd.read_csv(tasks_csv)
    tasks = [
        Task(
            task_name=row['task_name'],
            wcet=int(row['wcet']),
            period=int(row['period']),
            deadline=int(row['period']),    # assume implicit deadline = period
            priority=int(row['priority']) if not pd.isna(row['priority']) else None,
            component_id=row['component_id']
        )
        for _, row in tasks_df.iterrows()
    ]
    # Load budgets/components
    comp_df = pd.read_csv(budgets_csv)
    components = {
        row['component_id']: Component(
            component_id=row['component_id'],
            scheduler=row['scheduler'],
            budget=int(row['budget']),
            period=int(row['period']),
            core_id=row['core_id'],
            priority=int(row['priority']) if not pd.isna(row['priority']) else 0
        )
        for _, row in comp_df.iterrows()
    }
    # Assign tasks to components
    for task in tasks:
        components[task.component_id].tasks.append(task)
    # Load cores
    arch_df = pd.read_csv(arch_csv)
    cores = {
        row['core_id']: Core(
            core_id=row['core_id'],
            speed_factor=float(row['speed_factor']),
            scheduler=row['scheduler']
        )
        for _, row in arch_df.iterrows()
    }
    # Assign components to cores
    for comp in components.values():
        cores[comp.core_id].components.append(comp)
    return list(cores.values())

def simulate_core(core: Core, sim_time: int) -> Dict[str,int]:
    # Initialize per-task WCRT and release times
    wcrt = {task.task_name: 0 for comp in core.components for task in comp.tasks}
    next_task_release = {task.task_name:0 for comp in core.components for task in comp.tasks}
    # Initialize component server budgets
    for comp in core.components:
        comp.remaining_budget = comp.budget
    # Simple time-stepped simulation
    jobs = []  # active jobs
    for t in range(sim_time):
        # Refill component budgets at server periods
        for comp in core.components:
            if t % comp.period == 0:
                comp.remaining_budget = comp.budget
        # Release task jobs
        for comp in core.components:
            for task in comp.tasks:
                if t % task.period == 0:
                    jobs.append({
                        'task': task,
                        'release': t,
                        'remaining': task.wcet,
                        'abs_deadline': t + task.deadline,
                        'component': comp
                    })
        # Collect ready jobs that have budget
        ready = [job for job in jobs
                 if job['release'] <= t
                 and job['remaining'] > 0
                 and job['component'].remaining_budget > 0]
        if ready:
            # Core-level: select component server
            # Group by component
            # comps_ready = {job['component'] for job in ready}
            # Build a map from component_id → Component
            comps_map = {job['component'].component_id: job['component'] for job in ready}
            # Then take its values() to get a unique list of Component
            comps_ready = list(comps_map.values())
            
            # Choose component by core scheduler
            if core.scheduler == 'RM':
                # lowest priority number first
                sel_comp = min(comps_ready, key=lambda c: c.priority)
            else:  # EDF at core: choose earliest next deadline (server period)
                sel_comp = min(
                    comps_ready,
                    key=lambda c: ((t//c.period + 1)*c.period)
                )
            # Within that component, pick job by comp.scheduler
            comp_jobs = [job for job in ready if job['component']==sel_comp]
            if sel_comp.scheduler == 'RM':
                sel_job = min(comp_jobs, key=lambda j: j['task'].priority)
            else:  # EDF within component
                sel_job = min(comp_jobs, key=lambda j: j['abs_deadline'])
            # Run 1 time unit
            sel_job['remaining'] -= 1
            sel_comp.remaining_budget -= 1
            # If job finishes, record WCRT
            if sel_job['remaining'] == 0:
                rt = (t+1) - sel_job['release']
                name = sel_job['task'].task_name
                wcrt[name] = max(wcrt[name], rt)
                jobs.remove(sel_job)
        # else idle for this core
    return wcrt

# Example usage:
cores = load_system()
sim_results = {}
for core in cores:
    core_res = simulate_core(core, sim_time=1000)
    sim_results.update(core_res)
# print(sim_results)
for task_name, wcrt in sim_results.items():
    print(f"Task {task_name} WCRT: {wcrt}")
