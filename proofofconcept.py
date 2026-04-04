import irsdk
import time
import csv
from datetime import datetime

ir = irsdk.IRSDK()

# Master Map: Add your custom corner ranges here for each track
TRACK_LIBRARY = {
    "lagunaseca": {
        "Turn 1": (0.04, 0.07),
        "Andretti Hairpin": (0.13, 0.18),
        "The Corkscrew": (0.65, 0.70),
    },
    "spa": {
        "La Source": (0.01, 0.05),
        "Eau Rouge": (0.11, 0.15),
        "Raidillon": (0.15, 0.18),
        "Pouhon": (0.55, 0.60),
    }
}

def get_track_name():
    """Extracts the internal track name from SessionInfo."""
    if ir['WeekendInfo']:
        return ir['WeekendInfo']['TrackName']
    return None

def get_corner_name(dist_pct, track_name):
    """Checks the car's track percentage against the specific track's map."""
    if track_name in TRACK_LIBRARY:
        for corner, (start, end) in TRACK_LIBRARY[track_name].items():
            if start <= dist_pct <= end:
                return corner
    return "Straight/Other"

def log_incidents_to_csv():
    if not ir.startup():
        return

    # Identify the track once at the start
    current_track = get_track_name()
    print(f"Track Detected: {current_track}")

    filename = f"incidents_{current_track}_{datetime.now().strftime('%H%M%S')}.csv"
    last_surface_state = {}
    last_logged_time = {}

    with open(filename, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['SessionTime', 'Timestamp', 'Lap', 'TrackName', 'Corner', 'DriverName'])

        try:
            while True:
                if not ir.is_connected:
                    break
                
                # Fetch telemetry arrays
                surfaces = ir['CarIdxTrackSurface']
                laps = ir['CarIdxLap']
                positions = ir['CarIdxLapDistPct']
                drivers = ir['DriverInfo']['Drivers']
                session_time = ir['SessionTime']

                for driver in drivers:
                    idx = driver['CarIdx']
                    
                    # Skip cars not currently in the world
                    if idx >= len(surfaces) or surfaces[idx] == -2:
                        continue

                    current_surface = surfaces[idx]
                    previous_surface = last_surface_state.get(idx, 2)

                    # Detection: Entering "Off-Track" state
                    if current_surface == -1 and previous_surface != -1:
                        # Replay-friendly debounce (2 second window)
                        if session_time > last_logged_time.get(idx, -5) + 2:
                            
                            name = driver['UserName']
                            lap = laps[idx]
                            corner = get_corner_name(positions[idx], current_track)
                            timestamp = f"{int(session_time // 60)}:{int(session_time % 60):02d}"

                            writer.writerow([round(session_time, 2), timestamp, lap, current_track, corner, name])
                            f.flush()
                            
                            print(f"Lap {lap} | {corner}: {name} OFF TRACK")
                            last_logged_time[idx] = session_time

                    last_surface_state[idx] = current_surface

                time.sleep(1/60)

        except KeyboardInterrupt:
            print("Logging stopped by user.")
        finally:
            ir.shutdown()

if __name__ == "__main__":
    log_incidents_to_csv()