#├── call_manager.py      # Manages call requests, queue, resource allocation (core logic)
#├── channel_manager.py   # Manages channel states (core logic)
#├── config.yaml          # YAML configuration for static data
#├── event_bus.py         # Handler class
#├── events.py            # Definitions for all events
#├── main.py              # Main entry point, CLI loop, system initialization
#├── radio_system.py      # Core radio system logic, event bus, high-level management
#├── site_controller.py   # Manages individual site state and channel allocation
#├── unit_manager.py      # Manages unit registration, affiliation, and status

import yaml
import sys
from radio_system import RadioSystem
from call_manager import CallManager
from channel_manager import ChannelManager
from unit_manager import UnitManager
from site_controller import SiteController
from events import *




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


def process_command(command, radio_system, site_controllers):
    parts = command.split(",")
    if not parts:
        return

    first_part = parts[0].strip().split()  # Split the first part by spaces
    action = first_part[0].lower()

    if action == "start":  # New START command
        for site_id in site_controllers:
            radio_system.event_bus.publish(SiteStartRequested(site_id))
        print("Starting all sites...")
    elif action == "site-start":
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
        if len(first_part) != 2:  # check if the first part has the radio ID
            print("Usage: RADIO <rid>, <action> [<argument>]")
            return
        try:
            rid = int(first_part[1])
            if len(parts) < 2:
                print("Usage: RADIO <rid>, <action> [<argument>]")
                return
            radio_action = parts[1].strip().lower()

            if radio_action == "on":
                radio_system.event_bus.publish(RadioPowerOn(rid))

            elif radio_action == "check-range":
                radio_system.event_bus.publish(RadioCheckRange(rid))
            elif radio_action == "status":
                radio_system.event_bus.publish(RadioStatusCheck(rid))
            elif radio_action == "select":
                if len(parts) != 3:
                    print("Usage: RADIO <rid>, SELECT <tgid>")
                    return
                try:
                    tgid = int(parts[2])
                    radio_system.event_bus.publish(RadioSelectTalkgroup(rid, tgid))
                except ValueError:
                    print("TGID must be an integer.")
            elif radio_action == "aff":
                if len(parts) != 3:
                    print("Usage: RADIO <rid>, AFF <tgid>")
                    return
                tgid = int(parts[2])
                radio_system.event_bus.publish(RadioAffiliateRequested(rid, tgid))
            elif radio_action == "ptt":
                if len(parts) < 4:
                    print("Usage: RADIO <rid>, PTT <call_length>, <tgid>, [<ckr>]")
                    return
                call_length = float(parts[2].strip())
                tgid = int(parts[3].strip())
                ckr = int(parts[4].strip()) if len(parts) == 5 else None
                radio_system.event_bus.publish(RadioPTT(rid, tgid, call_length, ckr))
            else:
                print("Invalid radio action.")
        except ValueError:
            print("RID and TGID must be integers, call_length must be a float, CKR must be an integer")

    elif action == "show_core_activity":
        print("logging activity")
        # core_logger.show_logs()  # Assuming show_logs method in Logger
    elif action == "show_site_activity":
        if len(parts) != 2:
            print("Usage: show_site_activity <site_id>")
            return
        try:
            site_id = int(parts[1])
            if site_id not in site_controllers:
                print(f"Error: Site with ID {site_id} not found.")
                return
        except ValueError:
            print("Site ID must be an integer.")
    elif action == "exit":
        sys.exit(0)
    else:
        print(f"Unknown command: {action}")


def run_cli(radio_system, site_controllers):
    while True:
        command = input("> ")
        process_command(command, radio_system, site_controllers)


if __name__ == "__main__":

    # Specify the configuration file path
    config_file = "config.yaml"

    # Create a RadioSystem object, passing the configuration file
    radio_system = RadioSystem(config_file)

    # Now you can access the parsed configuration data through the radio_system object
    print(f"System ID: {radio_system.system_id}")
    print(f"System Alias: {radio_system.alias}")
    print(f"WACN: {radio_system.wacn}")

    #Access system config safely
    system_config = config.get("system", {})  #Get the system config, default to empty dict if it does not exist
    default_talkgroup = system_config.get(
        "default_talkgroup")  #Get the default talkgroup, default to None if it does not exist
    print(system_config)

    radio_system = RadioSystem(config)

    site_controllers = {}
    for site_id, site_config in config.get("sites", {}).items():
        site_controllers[int(site_id)] = SiteController(int(site_id), radio_system.event_bus, site_config)

    call_manager = CallManager(radio_system.event_bus, config, site_controllers)
    unit_manager = UnitManager(radio_system.event_bus, config, site_controllers,
                               default_talkgroup)  #Pass default talkgroup

    #Start consoles
    for unit_id, unit_config in config.get("units", {}).items():
        if unit_config["prop_type"] == "console":
            radio_system.event_bus.publish(RadioPowerOn(int(unit_id)))

    channel_manager = ChannelManager(radio_system.event_bus, config)

    # radio_system.event_bus.subscribe(CallStartRequested, call_manager.handle_call_request)
    # radio_system.event_bus.subscribe(ChannelAllocatedOnSite, call_manager.handle_channel_allocated_on_site)
    radio_system.event_bus.subscribe(RadioPowerOn, unit_manager.handle_radio_power_on)
    radio_system.event_bus.subscribe(RadioSiteListRequested, unit_manager.handle_radio_site_list_requested)
    radio_system.event_bus.subscribe(RadioSiteListReceived, unit_manager.handle_radio_site_list_received)
    radio_system.event_bus.subscribe(RadioRegisterRequested, unit_manager.handle_radio_register_requested)
    # radio_system.event_bus.subscribe(RadioAffiliateRequested, unit_manager.handle_radio_affiliate_requested)
    radio_system.event_bus.subscribe(RadioPTT, unit_manager.handle_radio_ptt)
    # radio_system.event_bus.subscribe(RadioCheckRange, unit_manager.handle_radio_check_range)
    radio_system.event_bus.subscribe(UnitRegistrationSuccess, unit_manager.handle_unit_registration_success)
    radio_system.event_bus.subscribe(UnitRegistrationFailed, unit_manager.handle_unit_registration_failed)
    radio_system.event_bus.subscribe(UnitAffiliationSuccess, unit_manager.handle_unit_affiliation_success)
    radio_system.event_bus.subscribe(UnitAffiliationFailed, unit_manager.handle_unit_affiliation_failed)
    radio_system.event_bus.subscribe(RadioStatusCheck, unit_manager.handle_radio_status_check)
    radio_system.event_bus.subscribe(RadioSelectTalkgroup, unit_manager.handle_radio_select_talkgroup)

    radio_system.event_bus.subscribe(ConsoleCallStartRequested, call_manager.handle_console_call_start_requested)
    radio_system.event_bus.subscribe(ConsoleCallPreempted, unit_manager.handle_console_call_preempt)
    radio_system.event_bus.subscribe(SubscriberCallPreempted, unit_manager.handle_subscriber_call_preempt)

    # Run CLI loop
    run_cli(radio_system, site_controllers)
