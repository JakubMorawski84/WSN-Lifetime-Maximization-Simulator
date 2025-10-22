import random
import math
from collections import deque
from pulp import LpProblem, LpVariable, lpSum, LpMinimize, LpBinary, PULP_CBC_CMD
from models import MeasurementPoint, Sensor

ALPHA = 1000
BETA = 1

def generate_static_points(cfg):
    points = []
    while len(points) < cfg["NUM_POINTS"]:
        x = round(random.uniform(0, cfg["FIELD_WIDTH"]), 2)
        z = round(random.uniform(0, cfg["FIELD_HEIGHT"]), 2)
        point = MeasurementPoint(x, z)
        if point not in points:
            points.append(point)
    return points

def generate_grid_sensors_auto(width, height, num_sensors, cfg):
    sensors = []
    if num_sensors <= 0 or cfg is None:
        return sensors

    cols = int(math.sqrt(num_sensors * width / height))
    rows = int(math.ceil(num_sensors / cols))

    dx = width / max(cols - 1, 1)
    dz = height / max(rows - 1, 1)

    id = 0
    for i in range(rows):
        for j in range(cols):
            if id >= num_sensors:
                return sensors
            x = j * dx
            z = i * dz
            sensors.append(Sensor(id, x, z, cfg["INITIAL_ENERGY"]))
            id += 1
    return sensors

def add_sink(sensors, cfg):
    if cfg is None:
        return None
    sink = Sensor("SINK", cfg["FIELD_WIDTH"] / 2, cfg["FIELD_HEIGHT"] / 2, float("inf"))
    sensors.append(sink)
    return sink

def compute_neighbors(sensors, comm_range):
    for s in sensors:
        s.neighbors.clear()
        for other in sensors:
            if s is not other and s.distance_to(other) <= comm_range:
                s.neighbors.append(other)

def bfs_paths_to_sink(sink, sensors_with_energy):
    if sink is None:
        return {}
    
    available_graph = {s: [] for s in sensors_with_energy}
    for s in sensors_with_energy:
        for neighbor in s.neighbors:
            if neighbor in sensors_with_energy:
                available_graph[s].append(neighbor)
    
    paths = {}
    queue = deque([(sink, [sink])])
    visited = {sink}
    
    while queue:
        current, path = queue.popleft()
        for neighbor in available_graph.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                new_path = path + [neighbor]
                paths[neighbor] = new_path[::-1]
                queue.append((neighbor, new_path))
    return paths

def solve_ilp(points, sensors, cfg):
    available_sensors = [s for s in sensors if s.energy > 0 and s.id != "SINK" and not s.is_failed]
    if not available_sensors:
        return []

    A = [[1 if s.covers(p, cfg) else 0 for s in available_sensors] for p in points]

    prob = LpProblem("SensorCover", LpMinimize)
    x = [LpVariable(f"x_{j}", cat=LpBinary) for j in range(len(available_sensors))]
    y = [LpVariable(f"y_{i}", cat=LpBinary) for i in range(len(points))]

    prob += -ALPHA * lpSum(y) + BETA * lpSum((1 / (s.energy + 1e-5)) * x[j]
                                             for j, s in enumerate(available_sensors))

    for i in range(len(points)):
        prob += y[i] <= lpSum(A[i][j] * x[j] for j in range(len(available_sensors)))

    required = int(cfg["MIN_COVERAGE_PERCENT"] / 100 * len(points))
    prob += lpSum(y) >= required

    prob.solve(PULP_CBC_CMD(msg=0))

    if lpSum(y).value() is None or lpSum(y).value() < required:
        return []

    return [s for j, s in enumerate(available_sensors) if x[j].varValue == 1]

def transmit_data_along_path(path, cfg):
    if random.random() < cfg["PACKET_LOSS_PROB"]:
        return False
    
    if not path or len(path) < 2:
        return False

    for i in range(len(path) - 1):
        sender = path[i]
        receiver = path[i + 1]

        if sender.id != "SINK" and sender.energy > 0:
            sender.energy -= cfg["TX_COST"]
            if sender.energy <= 0:
                sender.energy = 0
                return False

        if receiver.id != "SINK" and receiver.energy > 0:
            receiver.energy -= cfg["RX_COST"]
            if receiver.energy <= 0:
                receiver.energy = 0
                return False
    return True
