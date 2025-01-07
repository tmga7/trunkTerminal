import math
import random


class GeospatialUtils:

    @staticmethod
    def distance_between_points(lat1, lon1, lat2, lon2):
        # Implementation of Haversine formula (or other accurate distance calculation)
        R = 6371  # Radius of the Earth in km
        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        lat2 = math.radians(lat2)
        lon2 = math.radians(lon2)
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    @staticmethod
    def estimate_rssi(distance_km, max_distance_km, variation_db=20, max_rssi_dbm=-40,
                      min_rssi_dbm=-125):

        print(f"distance_km: {distance_km} km and max_distance_km: {max_distance_km} km")

        if distance_km >= max_distance_km:
            print(f"tripped")
            return min_rssi_dbm, 0

            # Calculate base signal strength in dBm
        signal_strength_dbm = min_rssi_dbm + (max_rssi_dbm - min_rssi_dbm) * (1 - (distance_km / max_distance_km))
        print(f"signal_strength_dbm: {signal_strength_dbm}")

        # Add random variation
        random_variation = random.uniform(-variation_db, variation_db)
        signal_strength_dbm += random_variation

        # Ensure signal strength is within the dBm range
        signal_strength_dbm = max(min_rssi_dbm, min(max_rssi_dbm, signal_strength_dbm))

        # Convert dBm to RSSI level (0 to 4 bars)
        if signal_strength_dbm >= -70:
            rssi_level = 4
        elif signal_strength_dbm >= -90:
            rssi_level = 3
        elif signal_strength_dbm >= -110:
            rssi_level = 2
        elif signal_strength_dbm >= -125:
            rssi_level = 1
        else:
            rssi_level = 0

        return signal_strength_dbm, rssi_level
