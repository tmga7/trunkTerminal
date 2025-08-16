import sys
import time
import yaml
import threading
from radio_system import RadioSystem
from controller import ZoneController
import events
from events import *
from p25.packets import EventPriority # Import from the new location


# A global flag to signal the simulation thread to stop
simulation_running = True


def simulation_loop(controllers: dict[int, ZoneController]):
    """The core simulation tick loop, runs in a separate thread."""
    print("Simulation thread started.")
    last_tick_time = time.time()
    while simulation_running:
        current_time = time.time()
        delta_time = current_time - last_tick_time
        last_tick_time = current_time

        for controller in controllers.values():
            controller.tick(delta_time)

        time.sleep(0.1) # Increased tick rate for smoother simulation
    print("Simulation thread stopped.")


def load_scenario(controllers: dict[int, ZoneController], scenario_file: str):
    """Loads a scenario file and schedules all events on the correct controllers."""
    with open(scenario_file, 'r') as f:
        scenario = yaml.safe_load(f)

    for item in scenario:
        zone_id = item.get('zone_id')
        controller = controllers.get(zone_id)

        if not controller:
            print(f"Warning: Zone {zone_id} not found for an event. Skipping.")
            continue

        # --- UPDATED LOGIC TO USE NEW COMMAND NAMES ---
        event_class_name = item['event']
        event_class = getattr(events, event_class_name, None)

        if event_class:
            params = item.get('params', {})
            event = event_class(**params)
            controller.schedule_event(item['time'], event)
        else:
            print(f"Warning: Unknown event type '{event_class_name}' in scenario file.")


def run_simulation_cli(system: RadioSystem, controllers: dict[int, ZoneController]):
    """Starts the simulation in a background thread and provides the CLI."""
    global simulation_running

    sim_thread = threading.Thread(target=simulation_loop, args=(controllers,), daemon=True)
    sim_thread.start()

    print("\n--- Trunked Radio System Simulator (P25 Model) ---")
    print("Commands:")
    print("  zone <zone_id> unit <id> on           - Powers on a unit.")
    print("  zone <zone_id> unit <id> info         - Shows status of a unit.")
    print("  zone <zone_id> queue info             - Shows event queue status.")
    print("  load <filename.yaml>                  - Loads a scenario file.")
    print("  exit                                  - Shuts down the simulator.")
    print("-------------------------------------------------")

    while True:
        try:
            command = input("> ")
            if not command: continue
            parts = command.strip().lower().split()
            action = parts[0]

            if action == "exit":
                simulation_running = False
                time.sleep(0.2)
                sys.exit(0)

            elif action == "load":
                load_scenario(controllers, parts[1])

            elif action == "zone":
                zone_id = int(parts[1])
                controller = controllers.get(zone_id)
                if not controller:
                    print(f"Error: Zone {zone_id} not found.")
                    continue

                cmd = parts[2]
                if cmd == "unit":
                    unit_id = int(parts[3])
                    sub_cmd = parts[4]
                    if sub_cmd == "on":
                        # --- USE NEW UnitPowerOnCommand ---
                        controller.publish_event(UnitPowerOnCommand(unit_id=unit_id))
                    elif sub_cmd == "info":
                        unit = system.get_unit(unit_id, zone_id)
                        if unit:
                            print(f"  Unit {unit.id} ({unit.alias}) Status:")
                            print(f"    - State: {unit.state.value}")
                            print(f"    - Site: {'N/A' if not unit.current_site else unit.current_site.id}")
                            print(f"    - Affiliated TG: {'N/A' if not unit.affiliated_talkgroup else unit.affiliated_talkgroup.alias}")
                        else:
                            print(f"Unit {unit_id} not found in Zone {zone_id}.")

                elif cmd == "queue" and parts[3] == "info":
                     print(f"Queue Status for Zone {zone_id}:")
                     print(controller.get_queue_status())

            else:
                print(f"Unknown command: '{action}'.")

        except (IndexError, ValueError):
            print("Invalid command format.")
        except KeyboardInterrupt:
            simulation_running = False
            time.sleep(0.2)
            sys.exit(0)


if __name__ == "__main__":
    config_file = "config.yaml"
    scenario_file = "scenario.yaml"
    radio_system = RadioSystem(config_path=config_file)

    if radio_system.config:
        zone_controllers = {}
        for zone_id, zone in radio_system.config.wacn.zones.items():
            print(f"Creating controller for Zone {zone_id}...")
            controller = ZoneController(radio_system, zone_id)
            zone_controllers[zone_id] = controller

            # --- NEW: Pre-select a talkgroup for each unit ---
            # This simulates the user turning the knob before powering on.
            # Without this, the unit wouldn't know which TG to affiliate to.
            if zone.talkgroups:
                default_tg = list(zone.talkgroups.values())[0]
                for unit in zone.units.values():
                    unit.selected_talkgroup = default_tg
                    print(f"  -> Pre-selected TG '{default_tg.alias}' for Unit {unit.id}")

            controller.initialize_system()

        try:
            print(f"\nPreloading scenario from '{scenario_file}'...")
            load_scenario(zone_controllers, scenario_file)
            print("Scenario loaded successfully.\n")
        except FileNotFoundError:
            print(f"Warning: Scenario file '{scenario_file}' not found. Starting without a scenario.")

        run_simulation_cli(radio_system, zone_controllers)
    else:
        print("Could not initialize radio system. Exiting.")
        sys.exit(1)