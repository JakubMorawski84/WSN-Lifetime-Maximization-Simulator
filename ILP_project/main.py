import tkinter as tk
from tkinter import filedialog
import random
from logic import (
    generate_static_points,
    generate_grid_sensors_auto,
    add_sink,
    compute_neighbors,
    bfs_paths_to_sink,
    solve_ilp,
    transmit_data_along_path
)
from config import load_config, cfg, OFFSET_X, OFFSET_Y

class SensorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Symulacja Sieci Sensorów")
        self.running = False
        self.cycle = 0
        self.packets_sent = 0
        self.packets_delivered = 0
        self.packets_lost = 0
        self.latencies = []
        self.low_coverage_cycles = 0
        self.is_final_state = False
        self.final_colors = {}

        self.canvas_width = 800
        self.canvas_height = 800
        self.scale = 1.0
        
        self.cfg = None
        self.entries = {}

        self.canvas = tk.Canvas(root, width=self.canvas_width, height=self.canvas_height, bg="white")
        self.canvas.pack()

        self.frame = tk.Frame(root)
        self.frame.pack()
        
        tk.Button(self.frame, text="Start", command=self.start_simulation).grid(row=1, column=1, padx=5)
        tk.Button(self.frame, text="Pauza", command=self.pause_simulation).grid(row=1, column=2, padx=5)
        tk.Button(self.frame, text="Reset", command=self.reset_simulation).grid(row=1, column=3, padx=5)
        tk.Button(self.frame, text="Załaduj konfigurację", command=self.load_config_gui).grid(row=1, column=0, padx=5)
        tk.Button(self.frame, text="Ustawienia WSN", command=self.open_settings_window).grid(row=1, column=4, padx=5)

        self.status_label = tk.Label(self.frame, text="Status: Załaduj konfigurację")
        self.status_label.grid(row=2, column=0, columnspan=5)

        self.points = []
        self.sensors = []
        self.sink = None
        self.draw_scene()

    def load_config_gui(self):
        filename = filedialog.askopenfilename(filetypes=[("INI files", "*.ini")])
        if filename:
            global cfg
            self.cfg = load_config(filename)
            cfg = self.cfg
            max_canvas_size = 900
            self.scale = max_canvas_size / max(self.cfg["FIELD_WIDTH"], self.cfg["FIELD_HEIGHT"])
            self.canvas_width = int(self.cfg["FIELD_WIDTH"] * self.scale + OFFSET_X * 2)
            self.canvas_height = int(self.cfg["FIELD_HEIGHT"] * self.scale + OFFSET_Y * 2)

            self.canvas.config(width=self.canvas_width, height=self.canvas_height)

            self.reset_simulation()
            self.status_label.config(text="Status: Konfiguracja załadowana")

    def open_settings_window(self):
        if self.cfg is None:
            self.status_label.config(text="Załaduj konfigurację przed edycją")
            return

        settings_window = tk.Toplevel(self.root)
        settings_window.title("Ustawienia WSN")
        
        self.entries = {}
        row = 0
        for key, value in self.cfg.items():
            if key == "SEED":
                continue
            
            label = tk.Label(settings_window, text=f"{key}:")
            label.grid(row=row, column=0, padx=5, pady=2)
            
            entry = tk.Entry(settings_window)
            entry.insert(0, str(value))
            entry.grid(row=row, column=1, padx=5, pady=2)
            self.entries[key] = entry
            row += 1

        save_button = tk.Button(settings_window, text="Zapisz i Zastosuj", command=lambda: self.save_and_apply_settings(settings_window))
        save_button.grid(row=row, columnspan=2, pady=10)

    def save_and_apply_settings(self, window):
        new_cfg = self.cfg.copy()
        try:
            for key, entry in self.entries.items():
                value = entry.get()
                if isinstance(new_cfg[key], int):
                    new_cfg[key] = int(value)
                elif isinstance(new_cfg[key], float):
                    new_cfg[key] = float(value)
                else:
                    new_cfg[key] = value

            global cfg
            cfg = new_cfg
            self.cfg = cfg
            self.reset_simulation()
            self.status_label.config(text="Status: Ustawienia zapisane i zastosowane.")
            window.destroy()

        except ValueError:
            self.status_label.config(text="Błąd: Wartości muszą być numeryczne. Spróbuj ponownie.")

    def draw_scene(self, paths=None):
        self.canvas.delete("all")
        
        if not self.points or not self.sensors:
            self.canvas.create_text(self.canvas_width // 2, self.canvas_height // 2,
                                     text="Brak załadowanej konfiguracji.\nZaładuj plik konfiguracyjny.",
                                     font=("Arial", 16), fill="gray")
            return

        for p in self.points:
            x, y = p.x * self.scale + OFFSET_X, p.z * self.scale + OFFSET_Y
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="black")

        for s in self.sensors:
            x, y = s.x * self.scale + OFFSET_X, s.z * self.scale + OFFSET_Y
            outline = "black"

            if self.is_final_state:
                fill = self.final_colors.get(s.id, "blue")
            else:
                if s.is_failed:
                    fill = "gray"
                elif s.id == "SINK":
                    fill = "yellow"
                elif s.energy <= 0:
                    fill = "red"
                elif s.is_on:
                    fill = "green"
                else:
                    fill = "blue"

            self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill=fill, outline=outline)
            
            if s.id != "SINK":
                self.canvas.create_oval(
                    x - self.cfg["COVERAGE_RADIUS"] * self.scale,
                    y - self.cfg["COVERAGE_RADIUS"] * self.scale,
                    x + self.cfg["COVERAGE_RADIUS"] * self.scale,
                    y + self.cfg["COVERAGE_RADIUS"] * self.scale,
                    outline=outline, dash=(2, 2)
                )

        if paths and not self.is_final_state:
            for s in self.sensors:
                if s.is_on and s.id != "SINK":
                    path = paths.get(s)
                    if path:
                        for i in range(len(path) - 1):
                            x1, y1 = path[i].x * self.scale + OFFSET_X, path[i].z * self.scale + OFFSET_Y
                            x2, y2 = path[i + 1].x * self.scale + OFFSET_X, path[i + 1].z * self.scale + OFFSET_Y
                            self.canvas.create_line(x1, y1, x2, y2, fill="orange", width=2, arrow=tk.LAST)
    
    def display_final_status(self):
        """
        Funkcja do ustawienia ostatecznych kolorów czujników na podstawie ich energii
        i wyczyszczenia ścieżek routingu, zgodnie z podanymi regułami.
        """
        self.is_final_state = True
        for s in self.sensors:
            if s.id == "SINK":
                self.final_colors[s.id] = "yellow"
            elif s.is_failed:
                self.final_colors[s.id] = "gray"
            elif s.energy <= 0:
                self.final_colors[s.id] = "red"
            else:
                self.final_colors[s.id] = "blue"
        
        self.draw_scene()

    def save_logs(self):
        if not self.sensors:
            return
        with open("logs.txt", "a") as f:
            pdr = (self.packets_delivered / self.packets_sent * 100) if self.packets_sent > 0 else 0
            avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
            f.write(f"=== KONIEC | Cykl: {self.cycle} | PDR={pdr:.2f}% | Latency={avg_latency:.2f}\n")
            for s in self.sensors:
                color = self.final_colors.get(s.id, "blue")
                f.write(f"Czujnik {s.id}: energia={s.energy:.2f}, kolor={color}, sasiedzi={[n.id for n in s.neighbors]}\n")
            f.write("\n")

    def start_simulation(self):
        if self.cfg is None:
            self.status_label.config(text="Załaduj konfigurację przed startem")
            return
        if not self.running:
            self.running = True
            self.simulate_step()

    def pause_simulation(self):
        self.running = False

    def reset_simulation(self):
        self.running = False
        self.cycle = 0
        self.packets_sent = 0
        self.packets_delivered = 0
        self.packets_lost = 0
        self.latencies.clear()
        self.low_coverage_cycles = 0
        self.is_final_state = False
        self.final_colors = {}

        if self.cfg is None:
            self.points = []
            self.sensors = []
            self.sink = None
            self.status_label.config(text="Status: Brak konfiguracji")
        else:
            self.points = generate_static_points(self.cfg)
            self.sensors = generate_grid_sensors_auto(self.cfg["FIELD_WIDTH"], self.cfg["FIELD_HEIGHT"], self.cfg["MAX_SENSORS"], self.cfg)
            self.sink = add_sink(self.sensors, self.cfg)
            comm_range = self.cfg["COVERAGE_RADIUS"] * 1.5
            compute_neighbors(self.sensors, comm_range)
            self.status_label.config(text="Status: Symulacja zresetowana")

        self.draw_scene()

    def simulate_step(self):
        if not self.running or self.cfg is None:
            if self.cfg is None:
                self.status_label.config(text="Brak konfiguracji - przerwano symulację")
            return

        self.cycle += 1
        
        for s in self.sensors:
            if s.id != "SINK" and not s.is_failed and random.random() < self.cfg["FAILURE_PROB"]:
                s.is_failed = True
                s.energy = 0
        
        selected = solve_ilp(self.points, self.sensors, self.cfg)
        
        covered_points = set()
        active_this_cycle = set()
        
        sensors_with_energy = [s for s in self.sensors if s.energy > 0 and not s.is_failed]
        paths = bfs_paths_to_sink(self.sink, sensors_with_energy)
        
        for s in selected:
            if s.is_failed:
                continue
            
            hops = paths.get(s, [])
            self.packets_sent += 1

            if hops:
                delivered = transmit_data_along_path(hops, self.cfg)
                if delivered:
                    self.packets_delivered += 1
                    self.latencies.append(len(hops) - 1)
                    for sensor_in_path in hops:
                        if sensor_in_path.id != "SINK":
                            active_this_cycle.add(sensor_in_path)
                    
                    covered_now = [i for i, p in enumerate(self.points) if s.covers(p, self.cfg)]
                    covered_points.update(covered_now)
                else:
                    self.packets_lost += 1

        for s in self.sensors:
            if s.id != "SINK" and not s.is_failed:
                if s in active_this_cycle:
                    s.is_on = True
                else:
                    s.is_on = False
                    s.energy -= self.cfg["SLEEP_COST"]
        
        coverage = len(covered_points) / len(self.points) * 100 if self.points else 0
        active = sum(1 for s in self.sensors if s.energy > 0 and s.id != "SINK")
        on_count = sum(1 for s in self.sensors if s.is_on)
        failed_count = sum(1 for s in self.sensors if s.is_failed)
        required_coverage = self.cfg["MIN_COVERAGE_PERCENT"]

        if self.low_coverage_cycles >= 3 or active == 0:
            self.status_label.config(
                text=f"KONIEC SYMULACJI | Cykl: {self.cycle}",
                fg="black"
            )
            self.running = False
            self.save_logs()
            self.display_final_status()
        else:
            if coverage < required_coverage:
                self.low_coverage_cycles += 1
            else:
                self.low_coverage_cycles = 0

            self.status_label.config(
                text=f"Cykl: {self.cycle} | Pokrycie: {coverage:.2f}% | ON: {on_count} | Aktywne: {active} | Awaria: {failed_count} | Utracone Pakiety: {self.packets_lost}",
                fg="black"
            )
            self.draw_scene(paths)
            self.root.after(self.cfg["FREQUENCY"], self.simulate_step)

if __name__ == "__main__":
    root = tk.Tk()
    app = SensorGUI(root)
    root.mainloop()
