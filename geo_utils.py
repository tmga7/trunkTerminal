import math
import random
from models import Coordinates, OperationalArea, Subsite

def get_distance(coord1: Coordinates, coord2: Coordinates) -> float:
    """
    Calculates the distance between two points using the Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Radius of the Earth in km
    lat1_rad = math.radians(coord1.latitude)
    lon1_rad = math.radians(coord1.longitude)
    lat2_rad = math.radians(coord2.latitude)
    lon2_rad = math.radians(coord2.longitude)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def estimate_rssi(distance_km: float, subsite: Subsite) -> tuple[float, int]:
    """
    Estimates the RSSI level based on distance from a subsite.
    Returns a tuple of (dBm, RSSI Level 0-4).
    """
    max_distance_km = subsite.operating_radius
    max_rssi_dbm = -50  # Strongest possible signal at the tower
    min_rssi_dbm = -125 # Weakest usable signal

    if distance_km >= max_distance_km:
        return min_rssi_dbm, 0

    # Calculate base signal strength, decreases linearly for simplicity
    signal_strength_dbm = max_rssi_dbm - (75 * (distance_km / max_distance_km))

    # Add some random variation to simulate real-world conditions
    signal_strength_dbm += random.uniform(-5, 5)
    signal_strength_dbm = max(min_rssi_dbm, min(max_rssi_dbm, signal_strength_dbm))

    # Convert dBm to RSSI level (0 to 4 bars)
    if signal_strength_dbm >= -70:
        rssi_level = 4
    elif signal_strength_dbm >= -90:
        rssi_level = 3
    elif signal_strength_dbm >= -110:
        rssi_level = 2
    else:
        rssi_level = 1

    return signal_strength_dbm, rssi_level

def get_random_point_in_area(area: OperationalArea) -> Coordinates:
    """Generates a random coordinate within a defined operational area."""
    random_lat = random.uniform(area.bottom_right.latitude, area.top_left.latitude)
    random_lon = random.uniform(area.top_left.longitude, area.bottom_right.longitude)
    return Coordinates(latitude=random_lat, longitude=random_lon)