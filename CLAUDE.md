# iRacing Telemetry — Claude Instructions

## Project
Python tools using pyirsdk to interface with iRacing and generate data for analysis.

## Stack
- Python 3
- pyirsdk (`import irsdk`) — wraps iRacing's shared memory API
- customtkinter — dark-mode GUI framework
- requests — for posting incidents to an external API
- No test framework currently in use (Python project, not Node)

## Files
- `proofofconcept.py` — Headless incident logger (CLI); reads `config.json` for API endpoint
- `app.py` — GUI incident logger using customtkinter; background telemetry thread + queue
- `config.json` — Config file with `api_endpoint` key
- `summarise_incidents.py` — CLI tool: aggregates an incidents CSV into a per-driver summary CSV

## Key Patterns
- `ir = irsdk.IRSDK(); ir.startup()` to connect to iRacing
- `ir['FieldName']` to read telemetry values
- `CarIdx`-prefixed fields return arrays indexed by car index
- Poll at `1/60` seconds to match iRacing's 60Hz telemetry rate
- `ir['DriverInfo']['Drivers']` gives the full driver list with `CarIdx` mappings
- Surface state: `0` = off-track, `3` = on-track; detect transition `current==0 and previous!=0`
- GUI app uses `threading.Thread` (daemon) + `queue.Queue` to pass messages to the main thread
- `load_config('config.json')` → `config['api_endpoint']` for the POST endpoint
- `post_incident(endpoint, subsession_id, session_type, cust_id, lap, track_pct)` — fire-and-forget POST

## Conventions
- Track corner maps use 0.0–1.0 fractional track position ranges
- CSV output files are named `incidents_<trackname>_<HHMMSS>.csv`
- Do not commit or push unless explicitly asked
