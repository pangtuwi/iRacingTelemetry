import customtkinter as ctk
import tkinter as tk
import threading
import queue
import time
import csv
import json
import os
import requests
import irsdk
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Track library ────────────────────────────────────────────────────────────

TRACK_LIBRARY_DIR = 'tracklibrary'
_track_cache = {}

def load_track(track_name):
    if track_name in _track_cache:
        return _track_cache[track_name]
    path = os.path.join(TRACK_LIBRARY_DIR, f"{track_name}.json")
    try:
        with open(path) as f:
            _track_cache[track_name] = json.load(f)
    except FileNotFoundError:
        _track_cache[track_name] = {}
    return _track_cache[track_name]

# ── Utility functions ────────────────────────────────────────────────────────

CONFIG_PATH = 'config.json'

def load_config(path=CONFIG_PATH):
    with open(path) as f:
        return json.load(f)

def save_config(data, path=CONFIG_PATH):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def get_corner_name(dist_pct, track_name):
    for corner, (start, end) in load_track(track_name).items():
        if start <= dist_pct < end:
            return corner
    return "Straight/Other"

def post_incident(endpoint, subsession_id, session_type, cust_id, driver_name, race_time, lap_no, track_pct, corner):
    payload = {
        'subsession_id': subsession_id,
        'session_type': session_type,
        'cust_id': cust_id,
        'driver_name': driver_name,
        'race_time': race_time,
        'lap_no': lap_no,
        'track_pct': track_pct,
        'corner': corner,
    }
    try:
        requests.post(endpoint, json=payload, timeout=5)
    except requests.RequestException as e:
        print(f"API post failed: {e}")

# ── App ──────────────────────────────────────────────────────────────────────

class IRacingApp:
    def __init__(self, root):
        self.root = root
        self.ir = irsdk.IRSDK()
        self.q = queue.Queue()
        self.logging_active = False
        self.csv_file = None
        self.csv_writer = None

        try:
            self.config = load_config()
        except Exception:
            self.config = {'api_endpoint': ''}

        self.build_gui()
        self.build_menu()
        self.poll_queue()

        t = threading.Thread(target=self.background_thread, daemon=True)
        t.start()

    # ── GUI construction ─────────────────────────────────────────────────────

    def build_gui(self):
        self.root.resizable(True, True)

        # Header frame
        header = ctk.CTkFrame(self.root, corner_radius=0)
        header.pack(fill='x', padx=10, pady=(10, 0))

        self.lbl_status = ctk.CTkLabel(header, text="Status: DISCONNECTED",
                                       text_color='gray',
                                       font=ctk.CTkFont(size=12, weight='bold'))
        self.lbl_status.grid(row=0, column=0, sticky='w', padx=10, pady=(8, 2))

        self.lbl_track = ctk.CTkLabel(header, text="Track: —", text_color='gray',
                                      font=ctk.CTkFont(size=12))
        self.lbl_track.grid(row=0, column=1, sticky='w', padx=(0, 20), pady=(8, 2))

        self.lbl_subsession = ctk.CTkLabel(header, text="SubSession: —", text_color='gray',
                                           font=ctk.CTkFont(size=12))
        self.lbl_subsession.grid(row=1, column=0, sticky='w', padx=10, pady=(2, 8))

        self.lbl_session_type = ctk.CTkLabel(header, text="Type: —", text_color='gray',
                                             font=ctk.CTkFont(size=12))
        self.lbl_session_type.grid(row=1, column=1, sticky='w', padx=(0, 20), pady=(2, 8))

        header.columnconfigure(2, weight=1)
        self.lbl_race_time = ctk.CTkLabel(header, text="Race Time: —", text_color='gray',
                                          font=ctk.CTkFont(size=12, weight='bold'))
        self.lbl_race_time.grid(row=0, column=2, rowspan=2, sticky='e', padx=(0, 16))

        # Button frame
        btn_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color='transparent')
        btn_frame.pack(fill='x', padx=10, pady=6)

        self.btn_log = ctk.CTkButton(btn_frame, text="Start Logging", width=140,
                                     command=self.toggle_logging, state='disabled')
        self.btn_log.pack(side='left')

        # Incident feed
        feed_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color='transparent')
        feed_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        self.feed = ctk.CTkTextbox(feed_frame, state='disabled', width=700, height=400,
                                   font=ctk.CTkFont(family='Courier', size=11))
        self.feed.pack(fill='both', expand=True)

    def build_menu(self):
        menubar = tk.Menu(self.root)
        app_menu = tk.Menu(menubar, tearoff=0)
        app_menu.add_command(label="Settings", command=self.open_settings)
        menubar.add_cascade(label="App", menu=app_menu)
        self.root.configure(menu=menubar)

    def open_settings(self):
        win = ctk.CTkToplevel(self.root)
        win.title("Settings")
        win.resizable(False, False)
        win.grab_set()  # modal

        ctk.CTkLabel(win, text="Settings", font=ctk.CTkFont(size=14, weight='bold')).grid(
            row=0, column=0, columnspan=2, padx=20, pady=(16, 8), sticky='w')

        ctk.CTkLabel(win, text="API Endpoint:").grid(
            row=1, column=0, padx=(20, 8), pady=8, sticky='w')
        entry_endpoint = ctk.CTkEntry(win, width=340)
        entry_endpoint.insert(0, self.config.get('api_endpoint', ''))
        entry_endpoint.grid(row=1, column=1, padx=(0, 20), pady=8)

        ctk.CTkLabel(win, text="Min Off-Track Duration (s):").grid(
            row=2, column=0, padx=(20, 8), pady=8, sticky='w')
        entry_min_dur = ctk.CTkEntry(win, width=100)
        entry_min_dur.insert(0, str(self.config.get('min_offtrack_seconds', 0.0)))
        entry_min_dur.grid(row=2, column=1, padx=(0, 20), pady=8, sticky='w')

        def save():
            try:
                min_dur = float(entry_min_dur.get().strip())
            except ValueError:
                ctk.CTkLabel(win, text="Duration must be a number.", text_color='#cc4444').grid(
                    row=4, column=0, columnspan=2, padx=20, pady=(0, 8))
                return
            self.config['api_endpoint'] = entry_endpoint.get().strip()
            self.config['min_offtrack_seconds'] = min_dur
            try:
                save_config(self.config)
            except Exception as e:
                ctk.CTkLabel(win, text=f"Save failed: {e}", text_color='#cc4444').grid(
                    row=4, column=0, columnspan=2, padx=20, pady=(0, 8))
                return
            win.destroy()

        btn_frame = ctk.CTkFrame(win, fg_color='transparent')
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(4, 16))
        ctk.CTkButton(btn_frame, text="Save", width=100, command=save).pack(side='left', padx=6)
        ctk.CTkButton(btn_frame, text="Cancel", width=100, fg_color='gray30',
                      hover_color='gray40', command=win.destroy).pack(side='left', padx=6)

    # ── Logging toggle ───────────────────────────────────────────────────────

    def toggle_logging(self):
        if not self.logging_active:
            self.logging_active = True
            track = self.lbl_track.cget('text').replace('Track: ', '') or 'unknown'
            filename = f"incidents_{track}_{datetime.now().strftime('%H%M%S')}.csv"
            self.csv_file = open(filename, mode='w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow([
                'SessionTime', 'RaceTime', 'Lap', 'Position',
                'CarNumber', 'Corner', 'TrackPct', 'DriverName', 'CustID',
            ])
            self.btn_log.configure(text="Stop Logging")
        else:
            self.logging_active = False
            if self.csv_file:
                self.csv_file.flush()
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None
            self.btn_log.configure(text="Start Logging")

    # ── Queue polling (main thread) ──────────────────────────────────────────

    def poll_queue(self):
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == 'status' and msg[1] == 'connected':
                    _, _, track, subsession, session_type = msg
                    self.lbl_status.configure(text="Status: CONNECTED", text_color='#44cc44')
                    self.lbl_track.configure(text=f"Track: {track}", text_color='white')
                    self.lbl_subsession.configure(text=f"SubSession: {subsession}", text_color='white')
                    self.lbl_session_type.configure(text=f"Type: {session_type}", text_color='white')
                    self.btn_log.configure(state='normal')
                elif msg[0] == 'status' and msg[1] == 'disconnected':
                    self.lbl_status.configure(text="Status: DISCONNECTED", text_color='#cc4444')
                    self.lbl_track.configure(text="Track: —", text_color='gray')
                    self.lbl_subsession.configure(text="SubSession: —", text_color='gray')
                    self.lbl_session_type.configure(text="Type: —", text_color='gray')
                    self.lbl_race_time.configure(text="Race Time: —", text_color='gray')
                    self.btn_log.configure(state='disabled')
                    if self.logging_active:
                        self.toggle_logging()
                elif msg[0] == 'racetime':
                    self.lbl_race_time.configure(text=f"Race Time: {msg[1]}", text_color='white')
                elif msg[0] == 'incident':
                    line = msg[1]
                    self.feed.configure(state='normal')
                    self.feed.insert('end', line + '\n')
                    self.feed.see('end')
                    self.feed.configure(state='disabled')
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)

    # ── Background telemetry thread ──────────────────────────────────────────

    def background_thread(self):
        last_logged_time = {}
        last_known_lap = {}
        last_surface_state = {}
        offtrack_since = {}
        finished_cars = set()
        race_start_time = None
        seeded = False
        last_session_num = None

        while True:
            if not self.ir.is_connected:
                connected = self.ir.startup()
                if not connected:
                    self.q.put(('status', 'disconnected'))
                    seeded = False
                    last_logged_time.clear()
                    last_known_lap.clear()
                    last_surface_state.clear()
                    offtrack_since.clear()
                    finished_cars.clear()
                    race_start_time = None
                    last_session_num = None
                    time.sleep(1)
                    continue

            # Seed surface state once on (re)connect to avoid spurious incidents
            if not seeded:
                initial_surfaces = self.ir['CarIdxTrackSurface'] or []
                last_surface_state = {i: s for i, s in enumerate(initial_surfaces)}
                seeded = True

            # Gather session info for the header
            try:
                track = self.ir['WeekendInfo']['TrackName']
                subsession_id = self.ir['WeekendInfo']['SubSessionID']
                sessions = self.ir['SessionInfo']['Sessions']
                current_num = self.ir['SessionNum']
                session_type = sessions[current_num]['SessionType']
            except (TypeError, IndexError, KeyError):
                time.sleep(1)
                continue

            # Reset all state when the session changes (e.g. practice → race)
            if current_num != last_session_num:
                last_session_num = current_num
                seeded = False
                last_logged_time.clear()
                last_known_lap.clear()
                last_surface_state.clear()
                offtrack_since.clear()
                finished_cars.clear()
                race_start_time = None

            self.q.put(('status', 'connected', track, subsession_id, session_type))

            # Telemetry arrays
            surfaces = self.ir['CarIdxTrackSurface']
            laps = self.ir['CarIdxLap']
            laps_completed = self.ir['CarIdxLapCompleted']
            positions = self.ir['CarIdxLapDistPct']
            race_positions = self.ir['CarIdxPosition']
            car_session_flags = self.ir['CarIdxSessionFlags']
            drivers = self.ir['DriverInfo']['Drivers']
            session_time = self.ir['SessionTime']

            if session_time is None or surfaces is None or positions is None or drivers is None:
                time.sleep(1 / 60)
                continue

            # Track race start
            if race_start_time is None and self.ir['SessionState'] == 4:
                race_start_time = session_time

            # Update race time display
            if race_start_time is not None:
                re = session_time - race_start_time
                rt = (f"{int(re // 3600):02d}:"
                      f"{int((re % 3600) // 60):02d}:"
                      f"{int(re % 60):02d}")
                self.q.put(('racetime', rt))

            for driver in drivers:
                idx = driver['CarIdx']

                if idx >= len(surfaces) or idx >= len(positions) or positions[idx] < 0:
                    continue

                # Mark car as finished when it receives the checkered flag; skip thereafter
                if car_session_flags and idx < len(car_session_flags):
                    if car_session_flags[idx] & 0x0001:  # checkered flag bit
                        finished_cars.add(idx)
                if idx in finished_cars:
                    last_surface_state[idx] = surfaces[idx]
                    continue

                if laps and idx < len(laps) and laps[idx] > 0:
                    last_known_lap[idx] = laps[idx]
                elif laps_completed and idx < len(laps_completed) and laps_completed[idx] >= 0:
                    last_known_lap[idx] = laps_completed[idx] + 1

                current_surface = surfaces[idx]
                previous_surface = last_surface_state.get(idx, 3)

                if current_surface == 0:
                    if previous_surface != 0:
                        offtrack_since[idx] = session_time
                else:
                    offtrack_since.pop(idx, None)

                min_dur = self.config.get('min_offtrack_seconds', 0.0)
                if (current_surface == 0
                        and idx in offtrack_since
                        and session_time - offtrack_since[idx] >= min_dur
                        and session_time > last_logged_time.get(idx, -5) + 2):
                        name = driver['UserName']
                        cust_id = driver['UserID']
                        car_number = driver['CarNumber']
                        race_pos = (race_positions[idx]
                                    if race_positions and idx < len(race_positions) else '?')
                        lap = laps[idx] if laps and idx < len(laps) else -1
                        if lap <= 0:
                            lap = last_known_lap.get(idx, '?')
                        corner = get_corner_name(positions[idx], track)
                        race_elapsed = (session_time - race_start_time
                                        if race_start_time is not None else session_time)
                        timestamp = (f"{int(race_elapsed // 3600):02d}:"
                                     f"{int((race_elapsed % 3600) // 60):02d}:"
                                     f"{int(race_elapsed % 60):02d}")
                        track_pct = round(positions[idx], 4)

                        if self.logging_active and self.csv_writer:
                            self.csv_writer.writerow([
                                round(session_time, 2), timestamp, lap, race_pos,
                                car_number, corner, track_pct, name, cust_id,
                            ])
                            self.csv_file.flush()
                            api_endpoint = self.config.get('api_endpoint', '')
                            if api_endpoint:
                                post_incident(api_endpoint, subsession_id,
                                              session_type, cust_id, name, timestamp, lap, track_pct, corner)

                        line = (f"{timestamp} | P{race_pos} | #{car_number} "
                                f"| {cust_id} | {name} "
                                f"| Lap {lap} | {corner} | {track_pct*100:.2f}%")
                        self.q.put(('incident', line))
                        last_logged_time[idx] = session_time
                        offtrack_since.pop(idx, None)

                last_surface_state[idx] = current_surface

            time.sleep(1 / 60)

# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    root = ctk.CTk()
    root.title("iRacing Off-Track Logger")
    IRacingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
