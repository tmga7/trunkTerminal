# radio_system.py (Final Parser Correction)
import yaml
from models import *


class RadioSystem:
    def __init__(self, config_path: str):
        self.config: SystemConfig = self._load_config_from_yaml(config_path)
        if self.config:
            print(
                f"RadioSystem initialized for WACN {self.config.wacn.id}. Loaded {len(self.config.wacn.zones)} zones.")
        else:
            print("Error: RadioSystem failed to initialize due to configuration errors.")

    def _load_config_from_yaml(self, file_path: str) -> SystemConfig:
        try:
            with open(file_path, "r") as f:
                raw_config = yaml.safe_load(f)

            wacn_data = raw_config['wacn']
            zones = {}
            for zone_id, zone_data in wacn_data.get("zones", {}).items():

                site_data_list = zone_data.pop("sites", {})
                sites = {}
                for site_id, site_data in site_data_list.items():
                    channel_data = site_data.pop("channels", {})
                    channels = {int(c_id): Channel(id=int(c_id), **c_data) for c_id, c_data in channel_data.items()}

                    subsite_data = site_data.pop("subsites", [])
                    subsites = [Subsite(location=Coordinates(**s.pop("location", {})), **s) for s in subsite_data]

                    sites[int(site_id)] = Site(id=int(site_id), channels=channels, subsites=subsites, **site_data)

                # --- (Rest of the parsing logic is the same) ---
                talkgroup_data = zone_data.pop("talkgroups", {})
                talkgroups = {int(tg_id): Talkgroup(id=int(tg_id), **tg_data) for tg_id, tg_data in
                              talkgroup_data.items()}

                unit_data = zone_data.pop("units", {})
                units = {int(u_id): Unit(id=int(u_id), **u_data) for u_id, u_data in unit_data.items()}

                console_data_list = zone_data.pop("consoles", {})
                consoles = {}
                for console_id, console_data in console_data_list.items():
                    # Find the actual Talkgroup objects from the list of IDs in the config
                    tg_ids = console_data.pop("affiliated_talkgroup_ids", [])
                    affiliated_tgs = [talkgroups.get(tg_id) for tg_id in tg_ids if talkgroups.get(tg_id)]

                    consoles[int(console_id)] = Console(
                        id=int(console_id),
                        affiliated_talkgroups=affiliated_tgs,
                        **console_data
                    )

                area_data = zone_data.pop("area", {})
                area = OperationalArea(
                    top_left=Coordinates(**area_data.get("top_left", {})),
                    bottom_right=Coordinates(**area_data.get("bottom_right", {}))
                )

                zones[int(zone_id)] = RFSS(
                    id=int(zone_id),
                    sites=sites,
                    talkgroups=talkgroups,
                    units=units,
                    consoles=consoles,  # Add consoles to the RFSS object
                    area=area,
                    **zone_data
                )

            wacn_id = wacn_data.pop('id', 0)
            wacn = WACN(id=wacn_id, zones=zones)

            return SystemConfig(wacn=wacn)

        except (FileNotFoundError, KeyError) as e:
            print(f"Error: Configuration file is missing a required key or not found. Details: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while loading the configuration: {e}")
            return None

    # --- (Accessor methods are unchanged) ---

    def get_unit(self, unit_id: int, zone_id: int = None) -> Unit:
        if zone_id:
            zone = self.config.wacn.zones.get(zone_id)
            return zone.units.get(unit_id) if zone else None

        for zone in self.config.wacn.zones.values():
            unit = zone.units.get(unit_id)
            if unit:
                return unit
        return None

    def get_site(self, site_id: int, zone_id: int) -> Site:
        zone = self.config.wacn.zones.get(zone_id)
        return zone.sites.get(site_id) if zone else None

    def get_talkgroup(self, talkgroup_id: int, zone_id: int) -> Talkgroup:
        """Gets a talkgroup by its ID from a specific zone."""
        zone = self.config.wacn.zones.get(zone_id)
        return zone.talkgroups.get(talkgroup_id) if zone else None

    def get_zone(self, zone_id: int) -> RFSS:
        """Gets a zone (RFSS) by its ID."""
        return self.config.wacn.zones.get(zone_id)