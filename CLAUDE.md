# iRacing Telemetry — Claude Instructions

## Project
Python tools using pyirsdk to interface with iRacing and generate data for analysis.

## Stack
- Python 3
- pyirsdk (`import irsdk`) — wraps iRacing's shared memory API
- No test framework currently in use (Python project, not Node)

## Key Patterns
- `ir = irsdk.IRSDK(); ir.startup()` to connect to iRacing
- `ir['FieldName']` to read telemetry values
- `CarIdx`-prefixed fields return arrays indexed by car index
- Poll at `1/60` seconds to match iRacing's 60Hz telemetry rate
- `ir['DriverInfo']['Drivers']` gives the full driver list with `CarIdx` mappings

## Conventions
- Track corner maps use 0.0–1.0 fractional track position ranges
- CSV output files are named with track name and timestamp
- Do not commit or push unless explicitly asked
