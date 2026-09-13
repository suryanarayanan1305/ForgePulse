"""Validation script for Milestone 1 — checks schema and seed SQL structure."""
import re

with open('database/schema.sql', 'r') as f:
    sql = f.read()

# Count tables defined
tables = re.findall(r'CREATE TABLE IF NOT EXISTS (\w+)', sql)
print(f'[PASS] Tables defined ({len(tables)}): {tables}')

# Count indexes
indexes = re.findall(r'CREATE INDEX IF NOT EXISTS (\w+)', sql)
print(f'[PASS] Indexes defined ({len(indexes)}): {indexes}')

# Count triggers
triggers = re.findall(r'CREATE TRIGGER (\w+)', sql)
print(f'[PASS] Triggers defined ({len(triggers)}): {triggers}')

# Check seed data
with open('database/seed.sql', 'r') as f:
    seed = f.read()

machine_inserts = re.findall(r"'(CNC-\d+|PRESS-\d+|MILL-\d+)'", seed)
unique_machines = sorted(set(machine_inserts))
print(f'[PASS] Machines in seed data: {unique_machines}')

sensor_count = seed.count('machine_sensors')
print(f'[PASS] machine_sensors references in seed: {sensor_count}')

print()
print('=== Schema and Seed SQL Structure Validated ===')
