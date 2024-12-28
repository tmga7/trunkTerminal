import yaml
import sys
from radio_system import RadioSystem
from call_manager import CallManager, CallRequested
from channel_manager import ChannelManager
from unit_manager import UnitManager
from site_controller import SiteController
from events import *
from logger import Logger  # Assuming a separate logger module


# Function to load configuration from YAML file
def load_config(filename):
    try:
        with open(filename, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{filename}' not found.")
        return None
    except yaml.YAMLError as e:
        print(f"Error parsing configuration file: {e}")
        return None


def process_command(command, radio_system, site_controllers, core_logger, site_logger):
    # ... (Existing CLI logic from previous response, modified to use new architecture)
    parts = command.split()
    if not parts:
        return

    action = parts[0].lower()
    if action == "ptt":
        if len(parts) != 3:
            print("Usage: ptt <rid> <tgid>")
            return
        try:
            rid = int(parts[1])
            tgid = int(parts[2])

            # Create a call request event
            call_id = 1  # temporary call id
            radio_system.event_bus.publish(CallRequested(rid, tgid, call_id))
        except ValueError:
            print("RID and TGID must be integers.")
    elif action == "show_core_activity":
        core_logger.show_logs()  # Assuming show_logs method in Logger
    elif action == "show_site_activity":
        if len(parts) != 2:
            print("Usage: show_site_activity <site_id>")
            return
        try:
            site_id = int(parts[1])
            if site_id not in site_controllers:
                print(f"Error: Site with ID {site_id} not found.")
                return
            site_logger.show_logs(site_id=site_id)  # Assuming show_logs with optional site_id
    else:
        print(f"Unknown command: {action}")


def run_cli(radio_system, site_controllers, core_logger, site_logger):
    while True:
        command = input("> ")
        process_command(command, radio_system, site_controllers, core_logger, site_logger)


if __name__ == "__main__":
    config_file = "config.yaml"
    config = load_config(config_file)
    if not config:
        sys.exit(1)

    # Create loggers for core and site activity
    core_logger = Logger("core_activity.log")  # Assuming Logger class for logging
    site_logger = Logger("site_activity.log")  # Assuming Logger class for logging

    # Initialize system components
    radio_system = RadioSystem(config)
    call_manager = CallManager(radio_system.event_bus)
    channel_manager = ChannelManager(radio_system.event_bus, config)
    unit_manager = UnitManager(radio_system.event_bus, config)

    # Create site controllers
    site_controllers = {}
    for site_id, site_config in config.get("sites", {}).items():
        site_controllers[int(site_id)] = SiteController(int(site_id), radio_system.event_bus, site_config)

    # Subscribe managers to events
    # ... (Existing subscriptions)
    radio_system.event_bus.subscribe("AllocateChannel", call_manager.handle_allocate_channel)

    # Run CLI loop
    run_cli(radio_system, site_controllers, core_logger, site_logger)
