import pandas as pd
import math
import random
import sys


def load_tasks(filename):
    """
    Loads task parameters from a CSV file.
    The file should contain columns: Task, BCET, WCET, Period, Deadline, Priority.
    """
    df = pd.read_csv(filename)
    tasks = []
    for _, row in df.iterrows():
        tasks.append(
            {
                "Task": row["Task"],
                "BCET": int(row["BCET"]),
                "WCET": int(row["WCET"]),
                "Period": int(row["Period"]),
                "Deadline": int(row["Deadline"]),
                "Priority": int(row["Priority"]),
            }
        )
    return tasks


def simulate(tasks, simulation_time):
    """
    Event-based simulation of fixed-priority preemptive scheduling.

    Jobs are released at their scheduled times (all tasks are released initially at time 0).
    For each ready job, the scheduler computes how long it can run until either:
      - The job finishes, or
      - A new job is released that might preempt it.

    The simulation clock is advanced directly to the next event time.

    Returns a dictionary mapping each task name to the worst-case response time (WCRT)
    observed in this simulation run.
    """
    # Initialize worst-case response times.
    worst_response = {task["Task"]: 0 for task in tasks}
    # For each task, track the next scheduled release time.
    next_release = {task["Task"]: 0 for task in tasks}
    # List to hold active jobs.
    jobs = []

    currentTime = 0
    while currentTime < simulation_time:
        # Release new jobs if their release time has arrived
        for task in tasks:
            task_name = task["Task"]
            while next_release[task_name] <= currentTime:
                # Use the scheduled release time as the job's release time.
                exec_time = random.randint(task["BCET"], task["WCET"])
                job = {
                    "task": task_name,
                    "release": next_release[task_name],
                    "remaining": exec_time,
                    "priority": task["Priority"],
                }
                jobs.append(job)
                # Schedule the next release for this task.
                next_release[task_name] += task["Period"]

        # Get all ready jobs (released and not finished)
        ready_jobs = [
            job
            for job in jobs
            if job["release"] <= currentTime and job["remaining"] > 0
        ]

        if ready_jobs:
            # Select the highest-priority ready job (lowest numerical Priority).
            current_job = min(ready_jobs, key=lambda job: job["priority"])
            # Compute when this job would finish if it ran uninterrupted.
            finish_time = currentTime + current_job["remaining"]
            # Determine the next release event (the earliest among all tasks).
            next_release_event = min(next_release.values())
            # The next event time is the earliest of:
            #   - The current job finishing,
            #   - The next job release,
            #   - The simulation end time.
            event_time = min(finish_time, next_release_event, simulation_time)
            delta = event_time - currentTime
            # Run the current job for delta time.
            current_job["remaining"] -= delta
            currentTime = event_time
            # If the job finishes, record its response time.
            if current_job["remaining"] <= 0:
                response_time = currentTime - current_job["release"]
                worst_response[current_job["task"]] = max(
                    worst_response[current_job["task"]], response_time
                )
                jobs.remove(current_job)
        else:
            # If no jobs are ready, jump to the next release event.
            next_release_event = min(next_release.values())
            # Make sure we don't advance past simulation_time.
            currentTime = min(next_release_event, simulation_time)

    return worst_response


def response_time_analysis(tasks):
    """
    Performs Response-Time Analysis (RTA) for fixed-priority tasks using worst-case execution times (WCET).

    The algorithm works as follows for each task τi (tasks are processed in order of decreasing priority,
    i.e., highest priority first):

       1. Set R = C_i (WCET of task τi).
       2. Repeat:
            - Compute the interference from higher-priority tasks:
                  I = Σ (ceil(R / T_j) * C_j) over all tasks j with higher priority.
            - Set R = C_i + I.
            - If R > D_i (deadline), the task is unschedulable.
       3. Until R converges.

    Returns a dictionary mapping each task name to its computed worst-case response time.
    If a task is unschedulable, its value is set to None.
    """
    # Sort tasks by Priority (lowest number indicates highest priority).
    sorted_tasks = sorted(tasks, key=lambda x: x["Priority"])
    response_times = {}

    # Process tasks in order of decreasing priority (highest priority first).
    for i, task in enumerate(sorted_tasks):
        C_i = task["WCET"]
        D_i = task["Deadline"]
        R_prev = 0
        R = C_i  # Initial guess: the WCET of the task.

        while R != R_prev:
            R_prev = R
            interference = 0
            # Sum interference from all higher-priority tasks.
            for j in range(i):
                higher_task = sorted_tasks[j]
                interference += (
                    math.ceil(R / higher_task["Period"]) * higher_task["WCET"]
                )
            R = C_i + interference
            # If the computed response time exceeds the deadline, the task is unschedulable.
            if R > D_i:
                R = None
                break
        response_times[task["Task"]] = R

    return response_times


def simulate_multiple_runs(tasks, simulation_time, num_runs):
    """
    Runs the simulation for num_runs times and keeps an updated reference to each task's worst-case response time.

    For each simulation run, the worst-case response time (WCRT) for each task is computed.
    Across all runs, the global WCRT for a task is the maximum WCRT observed.

    Returns:
        A dictionary mapping each task name to the maximum WCRT observed across all simulation runs.
    """
    global_wcrt = {task["Task"]: 0 for task in tasks}

    for _ in range(num_runs):
        run_wcrt = simulate(tasks, simulation_time)
        for task in tasks:
            task_name = task["Task"]
            if run_wcrt[task_name] > global_wcrt[task_name]:
                global_wcrt[task_name] = run_wcrt[task_name]

    return global_wcrt


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python3 simulator.py <filename.csv> <simulation_time> <simulation_iterations>"
        )
        sys.exit(1)

    filename = sys.argv[1]

    try:
        simulation_time = int(sys.argv[2])  # Total simulation time in time units.
    except ValueError:
        print("simulation_time must be a integer")
        sys.exit(1)

    try:
        num_runs = int(sys.argv[3])  # Total simulation time in time units.
    except ValueError:
        print("simulation_iterations must be a integer")
        sys.exit(1)

    # Load task model from the CSV file.
    tasks = load_tasks(filename)

    print("Running Very Simple Simulator (VSS)...")
    # sim_wcrt = simulate(tasks, simulation_time)
    sim_wcrt = simulate_multiple_runs(tasks, simulation_time, num_runs)

    for task, wcrt in sim_wcrt.items():
        print(f"Task {task}: Simulated WCRT = {wcrt} time units")

    # Run Response-Time Analysis (RTA)
    print("\nRunning Response-Time Analysis (RTA)...")
    rta_results = response_time_analysis(tasks)
    # Print results in the original order as in the CSV file.
    for task in tasks:
        t_name = task["Task"]
        wcrt = rta_results[t_name]
        if wcrt is None:
            print(f"Task {t_name}: UNSCHEDULABLE")
        else:
            print(f"Task {t_name}: RTA WCRT = {wcrt} time units")


if __name__ == "__main__":
    main()
