from models.tasks import Task
from models.components import Component
from models.cores import Core

import csv
#DIR = "test-cases/1-tiny-test-case/"
#DIR = "test-cases/2-small-test-case/"
#DIR = "test-cases/3-medium-test-case/"
#DIR = "test-cases/4-large-test-case/"
#DIR = "test-cases/5-huge-test-case/"
DIR = "test-cases/6-gigantic-test-case/"
#DIR = "test-cases/7-unschedulable-test-case/" #skoða
#DIR = "test-cases/8-unschedulable-test-case/"
#DIR = "test-cases/9-unschedulable-test-case/"
#DIR = "test-cases/10-unschedulable-test-case/"

TASK_FILE = "tasks.csv"
ARCHITECTURE_FILE = "architecture.csv"
BUDGET_FILE = "budgets.csv"


def parse_task():
    tasks = []
    with open(DIR + TASK_FILE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            tasks.append(Task(
                task_name=row['task_name'],
                wcet=float(row['wcet']),
                period=float(row['period']),
                component_id=row['component_id'],
                priority=int(row['priority']) if row['priority'] else None,
            ))
    return tasks


def parse_budget():
    budgets = []
    with open(DIR + BUDGET_FILE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            budgets.append(Component(
                component_id=row['component_id'],
                scheduler=row['scheduler'],
                budget=float(row['budget']),
                period=float(row['period']),
                core_id=row['core_id'],
                priority=int(row['priority']) if row['priority'] else None,
                tasks=[]
            ))
    return budgets


def parse_cores():
    cores = []
    with open(DIR + ARCHITECTURE_FILE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            cores.append(Core(
                core_id=row['core_id'],
                speed_factor=float(row['speed_factor']),
                scheduler=row['scheduler'],
                components=[]
            ))
    return cores


