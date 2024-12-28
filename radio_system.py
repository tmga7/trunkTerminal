from event_bus import EventBus
import yaml
import sys


class Talkgroup:
    def __init__(self, id, name=None):
        self.id = id
        self.name = name


class Subscriber:
    def __init__(self, id):
        self.id = id
        self.talkgroup = None  # Initially not assigned a talkgroup


class Site:
    def __init__(self, id, alias, prop_assignment_mode, allowed_talkgroups, channels, subsites=None):
        self.id = id
        self.alias = alias
        self.prop_assignment_mode = prop_assignment_mode
        self.allowed_talkgroups = allowed_talkgroups
        self.channels = channels
        self.subsites = subsites or {}  # Empty dictionary for subsites


class RFSS:
    def __init__(self, id, site):
        self.id = id
        self.sites = {site.id: site}  # Use a dictionary for better lookup


class RadioSystem:
    def __init__(self, filename):
        try:
            with open(filename, 'r') as f:
                config = yaml.safe_load(f)
                self.parse_config(config)
        except yaml.YAMLError as e:
            print(f"Error loading config file: {e}")
            sys.exit(1)

        self.config = config
        self.event_bus = EventBus()

    def parse_config(self, config):
        # Dynamically get the system ID (key of the "system" dictionary)
        system_id_key = list(config["system"].keys())[0]
        try:
            self.system_id = int(system_id_key, 16)  # Convert hex string to integer
        except ValueError:
            print(f"Error: Invalid system ID format: {system_id_key}")
            sys.exit(1)

        self.alias = config["system"].get(system_id_key).get("alias")
        self.wacn = int(config["system"][system_id_key]["wacn"], 16)  # Convert hex string to int
        self.talkgroups = {}
        for id, data in config["talkgroups"].items():
            self.talkgroups[int(id)] = Talkgroup(int(id), data.get("name"))
        self.subscribers = {int(id): Subscriber(int(id)) for id in config["subscribers"]}
        self.rfss = RFSS(1, self.parse_site(config["rfss"][1]))

    def parse_site(self, site_data):
        subsites = {}
        if "subsites" in site_data:
            for subsite_id, subsite_data in site_data["subsites"].items():
                subsites[int(subsite_id)] = Site(int(subsite_id), subsite_data.get("alias"),
                                                 subsite_data.get("prop_assignment_mode"),
                                                 subsite_data.get("allowed_talkgroups", []), site_data["channels"],
                                                 subsite_data.get("subsites"))
        site_id_key = list(site_data["site"].keys())[0]
        return Site(int(site_id_key), site_data["site"][site_id_key]["alias"],
                    site_data["site"][site_id_key]["prop_assignment_mode"],
                    site_data["site"][site_id_key]["allowed_talkgroups"], site_data["channels"], subsites)

    def start(self):
        # Start any background processes or services
        pass

    def stop(self):
        # Stop any background processes or services
        pass
