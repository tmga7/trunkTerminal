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
    parts = command.split(",")
    if not parts:
        return

    action = parts[0].lower()

    if action == "site-start":
        if len(parts) != 2:
            print("Usage: site-start <site_id>")
            return
        try:
            site_id = int(parts[1])
            radio_system.event_bus.publish(SiteStartRequested(site_id))
        except ValueError:
            print("Site ID must be an integer.")
    elif action == "site-stop":
        if len(parts) != 2:
            print("Usage: site-stop <site_id>")
            return
        try:
            site_id = int(parts[1])
            radio_system.event_bus.publish(SiteStopRequested(site_id))
        except ValueError:
            print("Site ID must be an integer.")
    elif action == "site-fail":
        if len(parts) != 3:
            print("Usage: site-fail <site_id> <reason>")
            return
        try:
            site_id = int(parts[1])
            reason = parts[2]
            radio_system.event_bus.publish(SiteFailRequested(site_id, reason))
        except ValueError:
            print("Site ID must be an integer.")
    elif action == "radio":
        parts = command.split(",")
        if len(parts) < 2:
            print("Usage: RADIO <rid>, <action> [<argument>]")
            return

        try:
            rid = int(parts[0].split()[1])
            radio_action = parts[1].strip().lower()

            if radio_action == "on":
                radio_system.event_bus.publish(RadioPowerOn(rid))
            elif radio_action == "aff":
                tgid = int(parts[2])
                radio_system.event_bus.publish(RadioAffiliateRequested(rid, tgid))
            elif radio_action == "ptt":
                if len(parts) < 4:
                    print("Usage: RADIO <rid>, PTT <call_length>, <tgid>, [<ckr>]")
                    return
                call_length = float(parts[2].strip())
                tgid = int(parts[3].strip())
                ckr = int(parts[4].strip()) if len(parts) == 5 else None
                radio_system.event_bus.publish(RadioPtt(rid, tgid, call_length, ckr))
            else:
                print("Invalid radio action.")
        except ValueError:
            print("RID and TGID must be integers, call_length must be a float")
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
        except ValueError:
            print("Site ID must be an integer.")
    elif action == "exit":
        sys.exit(0)
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
    call_manager = CallManager(radio_system.event_bus, config, site_controllers)
    channel_manager = ChannelManager(radio_system.event_bus, config)
    unit_manager = UnitManager(radio_system.event_bus, config)

    # Create site controllers
    site_controllers = {}
    for site_id, site_config in config.get("sites", {}).items():
        site_controllers[int(site_id)] = SiteController(int(site_id), radio_system.event_bus, site_config)

    # Subscribe managers to events
    radio_system.event_bus.subscribe(SiteStartRequested, site_controllers[1].handle_site_start_requested)
    radio_system.event_bus.subscribe(SiteStopRequested, site_controllers[1].handle_site_stop_requested)
    radio_system.event_bus.subscribe(SiteFailRequested, site_controllers[1].handle_site_fail_requested)

    radio_system.event_bus.subscribe(SiteStartRequested, site_controllers[2].handle_site_start_requested)
    radio_system.event_bus.subscribe(SiteStopRequested, site_controllers[2].handle_site_stop_requested)
    radio_system.event_bus.subscribe(SiteFailRequested, site_controllers[2].handle_site_fail_requested)

    radio_system.event_bus.subscribe("CallStartRequested", call_manager.handle_call_request)
    radio_system.event_bus.subscribe("ChannelAllocatedOnSite", call_manager.handle_channel_allocated_on_site)

    radio_system.event_bus.subscribe(RadioPowerOn, unit_manager.handle_radio_power_on)
    radio_system.event_bus.subscribe(RadioSiteListRequested, unit_manager.handle_radio_site_list_requested)
    radio_system.event_bus.subscribe(RadioSiteListReceived, unit_manager.handle_radio_site_list_received)
    radio_system.event_bus.subscribe(RadioRegisterRequested, unit_manager.handle_radio_register_requested)
    radio_system.event_bus.subscribe(RadioAffiliateRequested, unit_manager.handle_radio_affiliate_requested)
    radio_system.event_bus.subscribe(RadioPtt, unit_manager.handle_radio_ptt)

    radio_system.event_bus.subscribe("CallEnded", site_controllers[1].handle_call_ended)
    radio_system.event_bus.subscribe("CallEnded", site_controllers[2].handle_call_ended)

    # Run CLI loop
    run_cli(radio_system, site_controllers, core_logger, site_logger)
