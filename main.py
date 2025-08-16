import sys
import time
import yaml
import threading
from radio_system import RadioSystem
from controller import ZoneController
import events
from events import UnitPowerOnRequest

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

        # Tick all zone controllers to advance their internal clocks and process events
        for controller in controllers.values():
            controller.tick(delta_time)

        # Sleep to prevent 100% CPU usage and to control simulation speed
        # This effectively sets the simulation's "tick rate".
        time.sleep(0.3)  # 10 ticks per second
    print("Simulation thread stopped.")


def load_scenario(controllers: dict[int, ZoneController], scenario_file: str):
    """Loads a scenario file and schedules all events on the correct controllers."""
    with open(scenario_file, 'r') as f:
        scenario = yaml.safe_load(f)

    for item in scenario:
        zone_id = item.get('zone_id')
        controller = controllers.get(zone_id)

        if not controller:
            print(f"Warning: Zone {zone_id} not found for an event in {scenario_file}. Skipping.")
            continue

        event_class_name = item['event']
        event_class = getattr(events, event_class_name, None)

        if event_class:
            event = event_class(**item['params'])
            controller.schedule_event(item['time'], event)
        else:
            print(f"Warning: Unknown event type '{event_class_name}' in scenario file.")


def run_simulation_cli(system: RadioSystem, controllers: dict[int, ZoneController]):
    """Starts the simulation in a background thread and provides the CLI."""
    global simulation_running

    # Start the simulation loop in a daemon thread.
    # A 'daemon' thread will exit automatically when the main program exits.
    sim_thread = threading.Thread(target=simulation_loop, args=(controllers,), daemon=True)
    sim_thread.start()

    print("\n--- Trunked Radio System Simulator ---")
    print("System is running live. Enter commands below or load a scenario.")
    print("Commands:")
    print("  zone <zone_id> radio <id> on          - Powers on a unit in a specific zone.")
    print("  zone <zone_id> info unit <id>         - Shows status of a unit in a zone.")
    print(
        "  zone <zone_id> info queue             - Shows the status of the event queues for a zone.")  # <-- New command
    print("  load <filename.yaml>                  - Loads and schedules a scenario file.")
    print("  exit                                  - Shuts down the simulator.")
    print("------------------------------------")

    # The main thread is now dedicated to handling user input
    while True:
        try:
            command = input("> ")
            if not command:
                continue

            parts = command.strip().lower().split()
            action = parts[0]

            if action == "exit":
                print("Shutting down simulation...")
                simulation_running = False
                time.sleep(0.5)  # Give the simulation thread a moment to stop
                sys.exit(0)

            elif action == "load":
                scenario_file = parts[1]
                print(f"Loading scenario from {scenario_file}...")
                load_scenario(controllers, scenario_file)

            elif action == "zone":
                zone_id = int(parts[1])
                controller = controllers.get(zone_id)
                if not controller:
                    print(f"Error: Zone {zone_id} not found.")
                    continue

                cmd = parts[2]
                if cmd == "radio":
                    unit_id = int(parts[3])
                    if parts[4] == "on":
                        controller.publish_event(UnitPowerOnRequest(unit_id=unit_id))
                elif cmd == "info":
                    info_type = parts[3]
                    if info_type == "unit":
                        # ... (info unit logic) ...
                        pass
                    # --- ADD THIS BLOCK ---
                    elif info_type == "queue":
                        print(f"Queue Status for Zone {zone_id}:")
                        status_report = controller.get_queue_status()
                        print(status_report)
                    # --------------------
            else:
                print(f"Unknown command: '{action}'.")

        except (IndexError, ValueError):
            print("Invalid command format. Please check usage and try again.")
        except KeyboardInterrupt:
            print("\nShutting down simulation...")
            simulation_running = False
            time.sleep(0.5)
            sys.exit(0)
        except Exception as e:
            print(f"An unexpected error occurred in the CLI loop: {e}")


if __name__ == "__main__":
    config_file = "config.yaml"
    scenario_file = "scenario.yaml"
    radio_system = RadioSystem(config_path=config_file)

    if radio_system.config:
        # Create a controller for each zone defined in the config
        zone_controllers = {}
        for zone_id in radio_system.config.wacn.zones.keys():
            print(f"Creating controller for Zone {zone_id}...")
            controller = ZoneController(radio_system, zone_id)
            controller.initialize_system()
            zone_controllers[zone_id] = controller

            # --- ALWAYS PRELOAD THE SCENARIO ---
            try:
                print(f"\nPreloading scenario from '{scenario_file}'...")
                load_scenario(zone_controllers, scenario_file)
                print("Scenario loaded successfully.\n")
            except FileNotFoundError:
                print(f"Error: Scenario file not found at '{scenario_file}'. Make sure it exists.")
                sys.exit(1)
            # ------------------------------------

        # Start the main simulation loop and CLI
        run_simulation_cli(radio_system, zone_controllers)
    else:
        print("Could not initialize radio system. Exiting.")
        sys.exit(1)
