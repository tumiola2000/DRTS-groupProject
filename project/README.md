# Distributed Real-Time Systems (DRTS) Project

This project implements a hierarchical scheduling system simulator and analysis tool for distributed real-time systems. It supports both Rate Monotonic (RM) and Earliest Deadline First (EDF) scheduling algorithms at both the core and component levels.

## Project Structure

```
.
├── models/                 # Core system models
├── output/                # Output directory for simulation results
├── test-cases/           # Test cases and input files
├── simulator.py          # Main simulation engine
├── parser.py             # Input file parsing utilities
├── computed_budgets_sch.py # BDR interface computation
└── fixed_budget_sch.py   # Fixed budget scheduling implementation
```

## Prerequisites

- Python 3.6 or higher
- Required Python packages:
  - csv
  - heapq
  - statistics
  - math

## Input Files

The system requires three main input files in CSV format:

### 1. `tasks.csv`

Defines the task set with the following columns:

- `task_name`: Unique identifier for the task
- `wcet`: Worst-Case Execution Time (assuming nominal core speed)
- `period`: Task period in time units
- `component_id`: ID of the component the task belongs to
- `priority`: Task priority (only for RM-scheduled components)

### 2. `architecture.csv`

Defines the hardware platform:

- `core_id`: Unique identifier for the core
- `speed_factor`: Core speed relative to nominal speed (1.0 = nominal)
- `scheduler`: Top-level scheduler type ('RM' or 'EDF')

### 3. `budgets.csv`

Defines component budgets and mappings:

- `component_id`: Component identifier
- `scheduler`: Component-level scheduler ('RM' or 'EDF')
- `budget`: Initial budget in time units
- `period`: Component period in time units
- `core_id`: Assigned core identifier
- `priority`: Component priority (only for RM-scheduled cores)

## Running the Simulator

1. Place your input files in the appropriate directory:

   - Task definitions in `tasks.csv`
   - Architecture model in `architecture.csv`
   - Budget definitions in `budgets.csv`

You can modify which test case you want to use in the parse.py

2. Run the simulator:

   ```bash
   python simulator.py
   ```

3. The simulator will generate a `solution.csv` file containing:
   - Task schedulability results
   - Average and maximum response times
   - Component-level schedulability
   - Support utilization metrics

## Output Format

The `solution.csv` output file contains:

- `task_name`: Task identifier
- `component_id`: Component identifier
- `task_schedulable`: Boolean (0/1) indicating task schedulability
- `avg_response_time`: Average task response time
- `max_response_time`: Maximum task response time
- `sup_util`: Support utilization
- `component_schedulable`: Boolean indicating component schedulability

## Features

- Hierarchical scheduling system simulation
- Support for both RM and EDF scheduling
- BDR interface computation
- Response time analysis
- Component-level schedulability analysis
- Core-level schedulability analysis

## Implementation Details

The system implements:

1. A discrete-event simulator for real-time task execution
2. BDR interface computation for component-level analysis
3. Core-level schedulability analysis
4. Response time measurement and analysis

## Notes

- The initial budget and period values in `budgets.csv` are starting points derived from PRM-based analysis
- The system supports both fixed and computed budgets
- Response times are measured through simulation
- The analysis tool focuses on schedulability verification
