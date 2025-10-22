import configparser

cfg = None
OFFSET_X = 40
OFFSET_Y = 40

def load_config(filename="config.ini"):
    config = configparser.ConfigParser()
    config.read(filename)
    p = config["PARAMS"]
    return {
        "FIELD_WIDTH": int(p["FIELD_WIDTH"]),
        "FIELD_HEIGHT": int(p["FIELD_HEIGHT"]),
        "NUM_POINTS": int(p["NUM_POINTS"]),
        "MAX_SENSORS": int(p["MAX_SENSORS"]),
        "COVERAGE_RADIUS": float(p["COVERAGE_RADIUS"]),
        "INITIAL_ENERGY": float(p["INITIAL_ENERGY"]),
        "MIN_COVERAGE_PERCENT": float(p["MIN_COVERAGE_PERCENT"]),
        "TX_COST": float(p["TX_COST"]),
        "RX_COST": float(p["RX_COST"]),
        "IDLE_COST": float(p["IDLE_COST"]),
        "SLEEP_COST": float(p["SLEEP_COST"]),
        "SEED": int(p.get("SEED", -1)),
        "FAILURE_PROB": float(p.get("FAILURE_PROB", 0.01)),
        "PACKET_LOSS_PROB": float(p.get("PACKET_LOSS_PROB", 0.05)),
        "FREQUENCY": int(p.get("FREQUENCY", 500)),
    }