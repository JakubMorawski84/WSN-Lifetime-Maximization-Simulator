import math

class MeasurementPoint:
    def __init__(self, x, z):
        self.x = x
        self.z = z

class Sensor:
    def __init__(self, id, x, z, energy):
        self.id = id
        self.x = x
        self.z = z
        self.energy = energy
        self.is_on = False
        self.is_failed = False
        self.neighbors = []

    def distance_to(self, other):
        return math.hypot(self.x - other.x, self.z - other.z)

    def covers(self, point, cfg):
        return self.distance_to(point) <= cfg["COVERAGE_RADIUS"]
