from parser import parse_task, parse_budget, parse_cores

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







def main():
    # Parse the input files
    tasks = parse_task()
    budgets = parse_budget()
    cores = parse_cores()
    system = build_system(tasks, budgets, cores)
    print("System built successfully.")
    # Call the system function to process the parsed data
    

if __name__ == "__main__":
    main()