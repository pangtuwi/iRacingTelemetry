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
- `proofofconcept.py` — Headless incident logger (CLI); reads `config.json` for API endpoint. Reference only — do not modify.
- `app.py` — GUI incident logger using customtkinter; background telemetry thread + queue
- `config.json` — Config file with `api_endpoint` key
- `summarise_incidents.py` — CLI tool: aggregates an incidents CSV into a per-driver summary CSV
- `tracklibrary/<trackname>.json` — Per-track corner maps; filename must match `ir['WeekendInfo']['TrackName']` exactly

## Key Patterns
- `ir = irsdk.IRSDK(); ir.startup()` to connect to iRacing
- `ir['FieldName']` to read telemetry values
- `CarIdx`-prefixed fields return arrays indexed by car index
- Poll at `1/60` seconds to match iRacing's 60Hz telemetry rate
- `ir['DriverInfo']['Drivers']` gives the full driver list with `CarIdx` mappings
- Surface state: `0` = off-track, `3` = on-track; detect transition `current==0 and previous!=0`
- GUI app uses `threading.Thread` (daemon) + `queue.Queue` to pass messages to the main thread
- `load_config('config.json')` / `save_config(data)` — read/write `config.json`
- `self.config` on `IRacingApp` holds live config; background thread reads from it so changes apply without restart
- Settings dialog: `App > Settings` menu (standard `tk.Menu` on the `CTk` root); modal `CTkToplevel`
- `post_incident(endpoint, subsession_id, session_type, cust_id, driver_name, race_time, lap_no, track_pct)` — fire-and-forget POST
- Track library: `load_track(track_name)` loads `tracklibrary/<track_name>.json`, cached in `_track_cache`
- Corner lookup uses `start <= dist_pct < end` (exclusive upper bound) to avoid boundary ambiguity
- Session change detection: background thread tracks `last_session_num`; resets all state when `SessionNum` changes (e.g. practice → race) to prevent stale `race_start_time`
- Race time display: header label `lbl_race_time` updated via `('racetime', timestamp)` queue messages at 60Hz

## Conventions
- Track corner maps use 0.0–1.0 fractional track position ranges, stored as JSON arrays `[start, end]`
- CSV output files are named `incidents_<trackname>_<HHMMSS>.csv`
- Do not commit or push unless explicitly asked
