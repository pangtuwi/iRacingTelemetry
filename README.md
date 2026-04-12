# iRacing Telemetry Tools

Python tools using [pyirsdk](https://github.com/kutu/pyirsdk) to interface with iRacing and generate data for analysis.

## Requirements

- Python 3
- iRacing running on Windows (pyirsdk requires the iRacing shared memory interface)

Install dependencies:

```bash
pip install -r requirements.txt
```

`requirements.txt` includes: `pyirsdk`, `pyyaml`, `requests`, `customtkinter`

## Configuration

Create a `config.json` in the project root:

```json
{
    "api_endpoint": "https://your-server/endpoint"
}
```

Leave `api_endpoint` as an empty string to disable API posting.

## Tools

### `app.py` — GUI Incident Logger

A dark-mode desktop app that monitors a live iRacing session and logs off-track incidents.

**Features:**
- Live connection status showing track name, subsession ID, session type, and live race time
- Start/Stop logging button (enabled only when connected)
- Real-time incident feed showing race time, position, car number, cust ID, driver name, lap, and track %
- Resizable window
- **App > Settings** menu to edit `config.json` values (API endpoint) without restarting
- Writes incidents to `incidents_<track>_<HHMMSS>.csv`
- Optionally POSTs each incident to a REST API endpoint (configured via Settings or `config.json` directly)
- Correctly resets state on session change (e.g. practice → race) to avoid negative race timestamps

**Usage:**
```bash
python app.py
```

---

### `proofofconcept.py` — Headless Incident Logger

CLI version of the incident logger. Runs without a GUI and logs directly to CSV.

**Features:**
- Detects when any driver goes off-track (`CarIdxTrackSurface == 0`)
- Maps track position (0.0–1.0) to named corners using a configurable `TRACK_LIBRARY`
- Logs session time, timestamp, lap, race position, car number, corner, and driver info
- 2-second debounce to avoid duplicate entries
- POSTs incidents to API endpoint from `config.json`

**Usage:**
```bash
python proofofconcept.py
```

Output: `incidents_<trackname>_<HHMMSS>.csv`

---

### `summarise_incidents.py` — Incident Summary

Aggregates an incidents CSV into a per-driver summary sorted by incident count.

**Usage:**
```bash
python summarise_incidents.py incidents_<trackname>_<HHMMSS>.csv
```

Output: `incidents_<trackname>_<HHMMSS>_summary.csv` with columns `CustID`, `DriverName`, `IncidentCount`.

---

### Adding Track Corner Maps

Track corner maps live in the `tracklibrary/` folder as individual JSON files. The filename must match the iRacing internal track name exactly (as reported by `WeekendInfo.TrackName`).

Create `tracklibrary/<trackname>.json`:

```json
{
    "Turn 1": [0.04, 0.07],
    "Andretti Hairpin": [0.13, 0.18],
    "The Corkscrew": [0.65, 0.70]
}
```

Values are `[start, end]` as fractions of total track length (0.0–1.0). Ranges use an exclusive upper bound, so adjacent entries should share a boundary value without overlap. If no file exists for the current track, all incidents are logged as `Straight/Other`.

## Notes

- iRacing must be running and in an active session for data to be available
- All tools poll at 60Hz to match iRacing's telemetry update rate
- The GUI app (`app.py`) uses a background thread for telemetry; the UI stays responsive
