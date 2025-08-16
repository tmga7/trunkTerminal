import sys
import time
from radio_system import RadioSystem
from controller import ZoneController


def run_simulation_cli(system: RadioSystem, controller: ZoneController):
    """
    Provides the main simulation loop and an interactive command-line interface
    to control the simulation.
    """
    print("\n--- Trunked Radio System Simulator ---")
    print("System is now running. Enter commands below.")
    print("Commands:")
    print("  radio <id> on          - Powers on a specific unit.")
    print("  radio <id> move <site> - Moves a unit to a new site.")
    print("  info unit <id>         - Shows the current status of a unit.")
    print("  info site <id> affiliations         - Shows all units registered to a site.")
    print("  info site <id>         - Shows details about a site.")
    print("  exit                   - Shuts down the simulator.")
    print("------------------------------------")

    last_tick_time = time.time()

    # This is now the main simulation loop.
    while True:
        try:
            # --- Core Simulation Tick ---
            current_time = time.time()
            # Calculate time elapsed since the last loop iteration.
            delta_time = current_time - last_tick_time
            last_tick_time = current_time

            # This advances the simulation clock and processes any scheduled events.
            controller.tick(delta_time)

            # --- Handle User Input ---
            # NOTE: A simple input() call is "blocking", meaning the simulation
            # pauses while waiting for you to type. For a real-time UI
            # (like with WebSockets), you would use non-blocking input.
            # For our terminal simulation, this is acceptable.
            command = input("> ")
            if not command:
                continue

            parts = command.strip().lower().split()
            action = parts[0]

            if action == "exit":
                print("Shutting down simulation.")
                sys.exit(0)

            elif action == "radio":
                unit_id = int(parts[1])
                # We now publish an event instead of calling a method directly.
                # The ZoneController will handle the rest.
                if parts[2] == "on":
                    controller.publish_event(UnitPowerOnRequest(unit_id=unit_id))
                else:
                    print(f"Invalid radio action. Usage: radio <id> on")

            elif action == "info":
                info_type = parts[1]
                if info_type == "unit":
                    unit_id = int(parts[2])
                    # We need to specify the zione to find the unit.
                    # For simplicity, we'll assume zone 101 for now.
                    unit = system.get_unit(unit_id, zone_id=101)
                    if unit:
                        site_info = f"Site {unit.current_site.id} ({unit.current_site.alias})" if unit.current_site else "None"
                        tg_info = f"TG {unit.affiliated_talkgroup.id} ({unit.affiliated_talkgroup.alias})" if unit.affiliated_talkgroup else "None"
                        print(f"  Unit {unit.id} ({unit.alias}):")
                        print(f"    - Powered On: {unit.powered_on}")
                        print(f"    - Current Site: {site_info}")
                        print(f"    - Affiliated TG: {tg_info}")

                    else:
                        print(f"Error: Unit {unit_id} not found.")

                elif info_type == "site":
                    site_id = int(parts[2])
                    # Assuming we're looking for a site in zone 101
                    site = system.get_site(site_id, zone_id=101)
                    if not site:
                        print(f"Error: Site {site_id} not found in zone 101.")
                        continue

                    # --- NEW COMMAND LOGIC ---
                    if len(parts) > 3 and parts[3] == "affiliations":
                        print(f"  Affiliations for Site {site.id} ({site.alias}):")
                        if not site.registrations:
                            print("    - No units registered.")
                        else:
                            for reg in site.registrations:
                                # Determine the type (Unit or Console) and display info
                                reg_type = type(reg).__name__
                                tg_info = f"TG {reg.affiliated_talkgroup.id} ({reg.affiliated_talkgroup.alias})" if reg.affiliated_talkgroup else "None"
                                print(f"    - [{reg_type}] ID: {reg.id} ({reg.alias}) | Affiliated TG: {tg_info}")
                    else:
                        # This is the original 'info site <id>' command
                        print(f"  Site {site.id} ({site.alias}):")
                        print(f"    - Status: {site.status.value}")
                        print(f"    - Control Channel: {site.control_channel.id if site.control_channel else 'None'}")
                        print(f"    - Channels: {len(site.channels)}")
                        print(f"    - Registrations: {len(site.registrations)}")


            else:
                print(f"Unknown command: '{action}'")

        except (IndexError, ValueError):
            print("Invalid command format. Please check usage and try again.")
        except Exception as e:
            print(f"An unexpected error occurred in the main loop: {e}")


if __name__ == "__main__":
    config_file = "config.yaml"
    radio_system = RadioSystem(config_path=config_file)

    if radio_system.config:
        # Create the 'brain' of the system.
        zone_controller = ZoneController(radio_system)

        # Run the system startup sequence.
        zone_controller.initialize_system()

        # Start the main simulation loop and CLI.
        run_simulation_cli(radio_system, zone_controller)
    else:
        print("Could not initialize radio system. Exiting.")
        sys.exit(1)