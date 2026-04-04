# iRacing Telemetry Tools

Python tools using [pyirsdk](https://github.com/kutu/pyirsdk) to interface with iRacing and generate data for analysis.

## Requirements

- Python 3
- [pyirsdk](https://github.com/kutu/pyirsdk): `pip install pyirsdk`
- iRacing running on Windows (pyirsdk requires the iRacing shared memory interface)

## Tools

### `proofofconcept.py` — Incident Logger

Monitors a live iRacing session and logs off-track incidents to a CSV file.

**Features:**
- Detects when any driver goes off-track (`CarIdxTrackSurface == -1`)
- Maps track position (0.0–1.0) to named corners using a configurable `TRACK_LIBRARY`
- Logs session time, timestamp, lap number, track name, corner, and driver name
- 2-second debounce to avoid duplicate entries

**Usage:**
```bash
python proofofconcept.py
```

Output: `incidents_<trackname>_<HHMMSS>.csv`

**Adding track corner maps:**

Edit `TRACK_LIBRARY` in the script to add corner ranges for your track. Values are fractions of total track length (0.0–1.0):

```python
TRACK_LIBRARY = {
    "lagunaseca": {
        "Turn 1": (0.04, 0.07),
        "Andretti Hairpin": (0.13, 0.18),
    }
}
```

### `test1.py` — SDK Connectivity Test

Minimal script to verify pyirsdk is working and iRacing is connected. Prints the current car speed.

```bash
python test1.py
```

## Notes

- iRacing must be running and in an active session for data to be available
- All tools poll at 60Hz to match iRacing's telemetry update rate
