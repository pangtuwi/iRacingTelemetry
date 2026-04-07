import irsdk
import time
import csv
import json
import requests
from datetime import datetime

ir = irsdk.IRSDK()

def load_config(path='config.json'):
    with open(path) as f:
        return json.load(f)

def get_session_type():
    sessions = ir['SessionInfo']['Sessions']
    current_num = ir['SessionNum']
    return sessions[current_num]['SessionType']

def post_incident(endpoint, subsession_id, session_type, cust_id, lap_no, track_pct):
    payload = {
        'subsession_id': subsession_id,
        'session_type': session_type,
        'cust_id': cust_id,
        'lap_no': lap_no,
        'track_pct': track_pct,
    }
    try:
        requests.post(endpoint, json=payload, timeout=5)
    except requests.RequestException as e:
        print(f"API post failed: {e}")

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
    }, 
    "nurburgring combinedshortb": {
        # GP Section (Short w/out Arena)
        "Sabine Schmitz Kurve": (0.01, 0.03),
        "Valvoline-Kurve": (0.05, 0.07),
        "Opel-Kurve": (0.09, 0.11),
        
        # Nordschleife Entry & Early Section
        "Hatzenbach": (0.13, 0.16),
        "Hocheichen": (0.17, 0.19),
        "Flugplatz": (0.22, 0.25),
        "Schwedenkreuz": (0.28, 0.30),
        "Aremberg": (0.31, 0.33),
        "Adenauer Forst": (0.38, 0.41),
        "Metzgesfeld": (0.44, 0.46),
        
        # Mid Section
        "Wehrseifen": (0.51, 0.53),
        "Ex-Mühle": (0.55, 0.57),
        "Bergwerk": (0.61, 0.63),
        "Kesselchen": (0.66, 0.69),
        "Karussell": (0.72, 0.75),
        "Hohe Acht": (0.78, 0.81),
        
        # Final Section
        "Pflanzgarten": (0.84, 0.87),
        "Schwalbenschwanz": (0.90, 0.93),
        "Döttinger Höhe (Straight)": (0.94, 0.98),
        "Tiergarten": (0.98, 0.99)
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

    config = load_config()
    api_endpoint = config['api_endpoint']
    subsession_id = ir['WeekendInfo']['SubSessionID']

    # Identify the track once at the start
    current_track = get_track_name()
    print(f"Track Detected: {current_track}")

    filename = f"incidents_{current_track}_{datetime.now().strftime('%H%M%S')}.csv"
    last_logged_time = {}
    last_known_lap = {}
    race_start_time = None

    # Seed initial surface state so we don't log incidents for cars
    # already off-track at the moment the script connects
    initial_surfaces = ir['CarIdxTrackSurface'] or []
    last_surface_state = {i: s for i, s in enumerate(initial_surfaces)}

    with open(filename, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['SessionTime', 'RaceTime', 'Lap', 'Position', 'CarNumber', 'Corner', 'TrackPct', 'DriverName', 'CustID'])

        try:
            while True:
                if not ir.is_connected:
                    break
                
                # Fetch telemetry arrays
                surfaces = ir['CarIdxTrackSurface']
                laps = ir['CarIdxLap']
                laps_completed = ir['CarIdxLapCompleted']
                positions = ir['CarIdxLapDistPct']
                race_positions = ir['CarIdxPosition']
                drivers = ir['DriverInfo']['Drivers']
                session_time = ir['SessionTime']

                # Capture the session time at the moment the race goes green
                if race_start_time is None and ir['SessionState'] == 4:
                    race_start_time = session_time

                for driver in drivers:
                    idx = driver['CarIdx']

                    # Skip cars not currently in the world
                    if idx >= len(surfaces) or idx >= len(positions) or positions[idx] < 0:
                        continue

                    # Cache lap whenever we get a valid reading
                    if laps and idx < len(laps) and laps[idx] > 0:
                        last_known_lap[idx] = laps[idx]
                    elif laps_completed and idx < len(laps_completed) and laps_completed[idx] >= 0:
                        last_known_lap[idx] = laps_completed[idx] + 1

                    current_surface = surfaces[idx]
                    previous_surface = last_surface_state.get(idx, 3)

                    # Detection: Entering "Off-Track" state
                    if current_surface == 0 and previous_surface != 0:
                        # Replay-friendly debounce (2 second window)
                        if session_time > last_logged_time.get(idx, -5) + 2:
                            
                            name = driver['UserName']
                            cust_id = driver['UserID']
                            car_number = driver['CarNumber']
                            race_pos = race_positions[idx] if race_positions and idx < len(race_positions) else '?'
                            lap = laps[idx] if laps and idx < len(laps) else -1
                            if lap <= 0:
                                lap = last_known_lap.get(idx, '?')
                            corner = get_corner_name(positions[idx], current_track)
                            race_elapsed = session_time - race_start_time if race_start_time is not None else session_time
                            timestamp = f"{int(race_elapsed // 3600):02d}:{int((race_elapsed % 3600) // 60):02d}:{int(race_elapsed % 60):02d}"

                            track_pct = round(positions[idx], 4)
                            writer.writerow([round(session_time, 2), timestamp, lap, race_pos, car_number, corner, track_pct, name, cust_id])
                            f.flush()

                            post_incident(api_endpoint, subsession_id, get_session_type(), cust_id, lap, track_pct)
                            print(f"Race Time {timestamp} | P{race_pos} | Car #{car_number} | Lap {lap} | {corner} ({track_pct}) | {name} ({cust_id}) OFF TRACK")
                            last_logged_time[idx] = session_time

                    last_surface_state[idx] = current_surface

                time.sleep(1/60)

        except KeyboardInterrupt:
            print("Logging stopped by user.")
        finally:
            ir.shutdown()

if __name__ == "__main__":
    log_incidents_to_csv()