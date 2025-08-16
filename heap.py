import uuid
import heapq
import time
import cmd
import signal
import sys
import threading
import queue
import time
import random
import math
from datetime import datetime, timedelta


class SystemInstance:
    def __init__(self, id):
        self.id = id
        self.event_queue = queue.PriorityQueue()
        self.busy_queue = queue.PriorityQueue()
        self.lock = threading.Lock()
        self.stop_flag = threading.Event()
        self.channel_free = True

    def start(self):
        self.thread = threading.Thread(target=self.queue_monitor)
        self.thread.start()

    def stop(self):
        self.stop_flag.set()
        self.thread.join()

    def add_event(self, priority, event, event_time_seconds, metadata=None):
        # Calculate the event time
        current_time = datetime.now()
        event_time_delta = timedelta(seconds=event_time_seconds)
        event_time = current_time + event_time_delta

        # Handle rollover to the next day
        event_time_seconds_total = (current_time.hour * 3600 + current_time.minute * 60 +
                                    current_time.second + current_time.microsecond / 1e6 + event_time_seconds)
        event_time_seconds_total %= 86400  # Total seconds in a day
        event_time = (current_time.replace(hour=0, minute=0, second=0, microsecond=0) +
                      timedelta(seconds=event_time_seconds_total))

        precise_event_time = event_time.timestamp()
        self.event_queue.put((priority, precise_event_time, event, metadata))

        # Add timestamp to the print statement
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        print(
            f"[{timestamp}] System {self.id}: Added event: {event} with priority {priority}, scheduled for {datetime.fromtimestamp(precise_event_time).strftime('%Y-%m-%d %H:%M:%S.%f')}")

    def queue_monitor(self):
        while not self.stop_flag.is_set():
            try:
                current_time = time.time()

                # Print the contents of the event queue for debugging
                print(f"System {self.id} Event Queue State: {list(self.event_queue.queue)}")

                # Process Event Queue
                while not self.event_queue.empty():
                    priority, event_time, event, metadata = self.event_queue.get()
                    if current_time >= event_time:
                        self.process_event(priority, event, metadata)
                    else:
                        self.event_queue.put((priority, event_time, event, metadata))
                        break

                # Process Busy Queue
                self.process_busy_queue()

                # Print the contents of the busy queue for debugging
                print(f"System {self.id} Busy Queue State: {list(self.busy_queue.queue)}")

                # Sleep for 500ms to avoid busy waiting
                time.sleep(0.5)

            except queue.Empty:
                continue

    def process_event(self, priority, event, metadata):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        print(f"[{timestamp}] System {self.id}: Processing event: {event} with priority {priority}")
        print(f"System {self.id}: Processing event: {event} with priority {priority}")
        # Simulate event processing
        time.sleep(random.uniform(0.4, 0.8))
        # If event needs to be reprocessed, move it to the busy queue
        if metadata and metadata.get('reprocess'):
            self.busy_queue.put((priority, time.time(), event, metadata))

        # Example condition to free the channel
        if event == "End Call":
            self.channel_free = True

    def process_busy_queue(self):
        while not self.busy_queue.empty():
            priority, event_time, event, metadata = self.busy_queue.get()
            if self.channel_free or (metadata and metadata.get('force_process')):
                print(f"System {self.id}: Processing busy queue event: {event} with priority {priority}")
                # Simulate processing time
                time.sleep(random.uniform(0.4, 0.7))
                # Move the event back to the event queue for reprocessing
                self.event_queue.put((priority, event_time, event, metadata))
                self.busy_queue.task_done()
            else:
                self.busy_queue.put((priority, event_time, event, metadata))
                break


class SimulationManager:
    def __init__(self):
        self.simulations = {}
        self.simulation_threads = {}
        self.current_simulation = None

    def create_simulation(self):
        simulation_id = str(uuid.uuid4())
        simulation_id = "a"
        system = System()
        self.simulations[simulation_id] = system
        print(f"Simulation {simulation_id} created.")
        return simulation_id

    def start_simulation(self, simulation_id):
        if simulation_id in self.simulations:
            system = self.simulations[simulation_id]
            if simulation_id not in self.simulation_threads:  # check if the simulation is already running
                simulation_thread = threading.Thread(target=system.run_simulation)
                simulation_thread.daemon = True
                simulation_thread.start()
                self.simulation_threads[simulation_id] = simulation_thread
                self.prompt = simulation_id = " >>"

                print(f"Simulation {simulation_id} started in a new thread.")
            else:
                print(f"Simulation {simulation_id} is already running.")
        else:
            print(f"Simulation {simulation_id} not found.")

    def stop_simulation(self, simulation_id):
        if simulation_id in self.simulations:
            self.simulations[simulation_id].running = False
            if simulation_id in self.simulation_threads:
                del self.simulation_threads[simulation_id]
            print(f"Stopping simulation {simulation_id}...")
        else:
            print(f"Simulation {simulation_id} not found.")

    def get_simulation(self, simulation_id):
        return self.simulations.get(simulation_id)


# ... (CLI class with commands to interact with SimulationManager)

# Example usage
simulation_manager = SimulationManager()


# ... (CLI setup and thread)

class Radio:
    def __init__(self, id):
        self.id = id
        self.current_call = None

    def ptt(self, system, talkgroup, duration, priority):
        print(
            f"Radio {self.id}: PTT pressed for {duration}ms on TG {talkgroup} at {system.current_time} with priority {priority}")
        event_data = {"type": "ptt", "radio": self, "talkgroup": talkgroup, "duration": duration, "priority": priority}
        system.schedule_user_event(system.current_time, event_data)

    def end_call(self):
        self.current_call = None


class System:
    def __init__(self):
        self.queue_events_lock = threading.Lock()
        self.queue_busy_lock = threading.Lock()
        self.output_queue_lock = threading.Lock()
        self.queue_events = []
        self.queue_busy = []
        self.output_queue = []
        self.channels = {}
        self.current_time = 0
        self.running = True
        self.radios = [Radio(1), Radio(2), Radio(3)]  # radios are initialized here
        self.last_event_time = None  # Track the time of the last processed event
        self.inactivity_timeout = 3600  # 1 hour in seconds

    def schedule_system_event(self, event_data):
        priority = event_data.get("priority", 0)
        with self.queue_system_lock:
            heapq.heappush(self.queue_system, (time.time(), event_data))

    def schedule_user_event(self, event_time, event_data):
        with self.queue_events_lock:
            heapq.heappush(self.queue_events, (event_time, event_data["priority"], event_data))

    def schedule_busy_event(self, event_time, event_data):
        with self.queue_busy_lock:
            heapq.heappush(self.queue_busy, (event_time, event_data["priority"], event_data))

    def schedule_announcement(self, time, message):
        self.schedule_system_event({"type": "announcement", "message": message})

    def process_output_queue(self):
        # output_message = {"type": "announcement", "message": message, "timestamp": self.current_time}
        with self.output_queue_lock:
            while self.output_queue:
                message = heapq.heappop(self.output_queue)[1]  # remove the priority from the tuple
                if message["type"] == "announcement":
                    print(f"System Announcement at {message['timestamp']}: {message['message']}")
                # Add other message types here

    def process_system_events(self):
        with self.queue_system_lock:
            while self.queue_system:
                event_time, event_data = heapq.heappop(self.queue_system)
                self.handle_system_event(event_data)

    def handle_system_event(self, event):
        if event['type'] == 'announcement':
            print(f"System Announcement at {self.current_time}: {event['message']}")

    def process_user_events(self):
        with self.queue_events_lock:
            if self.queue_events:
                next_event_time, next_event_priority, next_event_data = self.queue_events[0]
                if next_event_time <= self.current_time:
                    _, _, event_data = heapq.heappop(self.queue_events)
                    print(
                        f"System: Processing user event of type '{event_data['type']}' at time {self.current_time}")
                    self.last_event_time = self.current_time  # update the last event time
                    if event_data["type"] == "scheduled_command":
                        self.handle_scheduled_command(event_data)
                    elif event_data["type"] == "call_end":
                        self.handle_user_event(event_data)

    def handle_user_event(self, event):
        if event["type"] == "ptt":
            self.start_call(event["radio"], event["talkgroup"], event["duration"], event["priority"])
        elif event['type'] == 'call_end':
            self.end_call(event['radio'], event['talkgroup'])

    def start_call(self, radio, talkgroup, duration, priority):
        if talkgroup not in self.channels:
            self.channels[talkgroup] = {"in_use": False}

        if not self.channels[talkgroup]["in_use"]:
            self.channels[talkgroup]["in_use"] = True
            radio.current_call = {'talkgroup': talkgroup}
            print(f"System: Starting call on TG {talkgroup} at {self.current_time}")
            self.schedule_user_event(self.current_time + duration / 1000,
                                     {"type": "call_end", "radio": radio, "talkgroup": talkgroup, "duration": duration,
                                      "priority": 5})  # Call end event now has a default priority
        else:
            print(
                f"System: Talkgroup {talkgroup} is busy. Queuing call at {self.current_time} with priority {priority}")
            self.schedule_busy_event(self.current_time,
                                     {"type": "ptt", "radio": radio, "talkgroup": talkgroup, "duration": duration,
                                      "priority": priority})

    def end_call(self, radio, talkgroup):
        if talkgroup in self.channels and self.channels[talkgroup]["in_use"]:
            self.channels[talkgroup]["in_use"] = False
            radio.end_call()
            print(f"System: Call ended on TG {talkgroup} at {self.current_time}")

            # Process waiting calls on this talkgroup
            busy_calls_to_process = []
            for time, priority, event in list(self.queue_busy):
                if event['talkgroup'] == talkgroup:
                    busy_calls_to_process.append((time, priority, event))

            for time, priority, event in sorted(busy_calls_to_process):
                if not self.channels[talkgroup]["in_use"]:
                    self.channels[talkgroup]["in_use"] = True
                    heapq.heappop(self.queue_busy)
                    self.start_call(event["radio"], event["talkgroup"], event["duration"], event["priority"])
                    print(f"System: Granting queued access to Radio {event['radio'].id} on TG {talkgroup}")
                    break
                else:
                    break

    def run_simulation(self):
        self.running = True
        print(f"Starting simulation at {self.current_time}")
        self.last_event_time = self.current_time  # initialize last event time
        while self.running:
            next_event_time = float('inf')  # Initialize to infinity

            with self.queue_events_lock:
                if self.queue_events:
                    next_event_time = min(next_event_time, self.queue_events[0][0])
            with self.queue_busy_lock:
                if self.queue_busy:
                    next_event_time = min(next_event_time, self.queue_busy[0][0])
            with self.output_queue_lock:
                if self.output_queue:
                    next_event_time = min(next_event_time, self.output_queue[0][0])

            if next_event_time <= self.current_time:
                self.process_user_events()
                self.process_output_queue()
            else:
                time_to_advance = min(next_event_time - self.current_time, 0.01)  # limit time to advance
                self.current_time += time_to_advance
                time.sleep(time_to_advance)

            if self.last_event_time is not None and (
                    self.current_time - self.last_event_time) >= self.inactivity_timeout:
                print(f"Simulation timed out due to inactivity ({self.inactivity_timeout} seconds).")
                self.running = False

        print(f"Simulation finished at {self.current_time}")


class RadioSimulatorCLI(cmd.Cmd):
    intro = "Welcome to the Trunked Radio Simulator. Type help or ? to list commands.\n"
    prompt = "() >"

    def __init__(self, simulation_manager):
        super().__init__()
        self.simulation_manager = simulation_manager

    def do_create(self, arg):
        """Creates a new simulation."""
        simulation_id = self.simulation_manager.create_simulation()
        print(f"Created simulation with ID: {simulation_id}")

    def do_use(self, arg):
        """Usage: use <simulation_id>
        Selects the active simulation."""
        self.simulation_manager.current_simulation = arg
        if self.simulation_manager.get_simulation(arg):
            print(f"Using simulation: {arg}")
        else:
            print(f"Simulation {arg} not found.")

    def do_run(self, arg):
        """Usage: run <simulation_id>
        Starts the specified simulation."""
        self.simulation_manager.start_simulation(arg)

    def do_stop(self, arg):
        """Usage: stop <simulation_id>
        Stops the specified simulation."""
        self.simulation_manager.stop_simulation(arg)

    def do_list(self, arg):
        """Lists all running simulations."""
        if self.simulation_manager.simulations:
            print("Running simulations:")
            for sim_id in self.simulation_manager.simulations:
                print(f"- {sim_id}")
        else:
            print("No simulations running.")

    def default(self, line):
        def default(self, line):
            if self.simulation_manager.current_simulation:
                simulation = self.simulation_manager.get_simulation(self.simulation_manager.current_simulation)
                if simulation:
                    system = simulation  # Access system through simulation
                    try:
                        parts = line.split()
                        command = parts[0]
                        arguments = parts[1:]

                        if command == "ptt":
                            radio_id, talkgroup, duration, priority = map(int, arguments)
                            radio = next((r for r in system.radios if r.id == radio_id), None)
                            if radio:
                                radio.ptt(system, talkgroup, duration, priority)
                            else:
                                print(f"Radio {radio_id} not found.")

                        elif command == "schedule":
                            priority, delay_ms, command, *arguments = line.split()[1:]
                            priority = int(priority)
                            delay_ms = int(delay_ms)
                            scheduled_time = system.current_time + (delay_ms / 1000)

                            event_data = {
                                "type": "scheduled_command",
                                "priority": priority,
                                "command": command,
                                "arguments": arguments,
                            }
                            system.schedule_user_event(scheduled_time, event_data)
                            print(
                                f"Command '{command}' scheduled with priority {priority} for {delay_ms}ms from now (at {scheduled_time})")

                        elif command == "announce":
                            message = " ".join(arguments)
                            system.schedule_announcement(message)

                        elif command == "showqueues":
                            def format_queue(queue, queue_name):
                                print(f"\n{queue_name}:")
                                if not queue:
                                    print("  (Empty)")
                                    return

                                for item in queue:
                                    if len(item) == 2:  # (time, event) or (time, message)
                                        time, data = item
                                        if isinstance(data,
                                                      dict) and "message" in data:  # check if the data is a message
                                            print(f"  Time: {time}, Message: {data['message']}")
                                        else:
                                            print(f"  Time: {time}, Event: {data}")
                                    elif len(item) == 3:  # (time, priority, event)
                                        time, priority, event = item
                                        print(f"  Time: {time}, Priority: {priority}, Event: {event}")
                                    else:
                                        print(f"  Unexpected queue format: {item}")

                            with system.queue_events_lock:
                                format_queue(system.queue_events, "User Events Queue")
                            with system.queue_busy_lock:
                                format_queue(system.queue_busy, "Busy Talkgroups Queue")
                            with system.output_queue_lock:
                                format_queue(system.output_queue, "Output Queue")

                        else:
                            print(f"Unknown command: {command}")

                    except ValueError:
                        print("Invalid arguments for command.")
                    except IndexError:
                        print("Not enough arguments for command.")
                else:
                    print("No simulation selected. Use 'create' and 'use' first.")
            else:
                print("No simulation selected. Use 'create' and 'use' first.")

    def do_showqueues(self, arg):
        """Usage: showqueues
        Displays the contents of all event queues and the output queue."""

        def format_queue(queue, queue_name):
            print(f"\n{queue_name}:")
            if not queue:
                print("  (Empty)")
                return

            for item in queue:
                if len(item) == 2:  # (time, event) or (time, message)
                    time, data = item
                    if isinstance(data, dict) and "message" in data:  # check if the data is a message
                        print(f"  Time: {time}, Message: {data['message']}")
                    else:
                        print(f"  Time: {time}, Event: {data}")
                elif len(item) == 3:  # (time, priority, event)
                    time, priority, event = item
                    print(f"  Time: {time}, Priority: {priority}, Event: {event}")
                else:
                    print(f"  Unexpected queue format: {item}")

        with self.system.queue_events_lock:
            format_queue(self.system.queue_events, "User Events Queue")
        with self.system.queue_busy_lock:
            format_queue(self.system.queue_busy, "Busy Talkgroups Queue")
        with self.system.output_queue_lock:
            format_queue(self.system.output_queue, "Output Queue")

    def do_announce(self, arg):
        try:
            sim_time, message = arg.split(maxsplit=1)
            sim_time = int(sim_time)
            self.system.schedule_announcement(sim_time, {"type": "announcement", "message": message, "priority": 0})
        except ValueError:
            print("Usage: announce <time> <message>")

    def do_ptt(self, arg):
        if self.simulation_manager.current_simulation:
            simulation = self.simulation_manager.get_simulation(self.simulation_manager.current_simulation)
            if simulation:
                system = simulation
                try:
                    radio_id, talkgroup, duration, priority = map(int, arg.split())
                    radio = next((r for r in system.radios if r.id == radio_id), None)
                    if radio:
                        radio.ptt(system, talkgroup, duration, priority)
                    else:
                        print(f"Radio {radio_id} not found.")

                except ValueError:
                    print("Invalid arguments. Use: ptt <radio_id> <talkgroup> <duration> <priority>")
            else:
                print("No simulation selected. Use 'create' and 'use' first.")
        else:
            print("No simulation selected. Use 'create' and 'use' first.")

    def do_schedule(self, arg):
        if self.simulation_manager.current_simulation:
            simulation = self.simulation_manager.get_simulation(self.simulation_manager.current_simulation)
            if simulation:
                system = simulation
                try:
                    parts = arg.split()
                    priority = int(parts[0])
                    delay_ms = int(parts[1])
                    command = parts[2]
                    arguments = parts[3:]
                    scheduled_time = system.current_time + (delay_ms / 1000)

                    event_data = {
                        "type": "scheduled_command",
                        "priority": priority,
                        "command": command,
                        "arguments": arguments,
                    }
                    system.schedule_user_event(scheduled_time, event_data)
                    print(
                        f"Command '{command}' scheduled with priority {priority} for {delay_ms}ms from now (at {scheduled_time})")

                except ValueError:
                    print("Invalid arguments. Use: schedule <priority> <delay_ms> <command> <arguments>")
                except IndexError:
                    print("Invalid arguments. Use: schedule <priority> <delay_ms> <command> <arguments>")
            else:
                print("No simulation selected. Use 'create' and 'use' first.")
        else:
            print("No simulation selected. Use 'create' and 'use' first.")

    def handle_scheduled_command(self, event_data):
        """Handles the execution of a scheduled command."""
        command = event_data["command"]
        arguments = event_data["arguments"]
        priority = event_data["priority"]

        if command == "ptt":
            try:
                radio_id, talkgroup, duration = map(int, arguments)
                radio = next((r for r in self.system.radios if r.id == radio_id), None)
                if radio:
                    radio.ptt(self.system, talkgroup, duration, priority)
                else:
                    print(f"Radio {radio_id} not found.")
            except ValueError:
                print("Invalid arguments for ptt command. Use: ptt <radio_id> <talkgroup> <duration>")
        # Add other commands here as needed (e.g., "mute", "unmute", etc.)
        else:
            print(f"Unknown command: {command}")

    def do_run(self, arg):
        """Usage: run <simulation_id>
        Starts the specified simulation in a new thread."""
        try:
            simulation_id = arg
            self.simulation_manager.start_simulation(simulation_id)
        except ValueError:
            print("Invalid arguments. Use: run <simulation_id>")
        except IndexError:
            print("Please provide a simulation id.")

    def do_stop(self, arg):
        """Stops the simulation."""
        self.system.running = False
        print("Stopping simulation...")

    def do_stop(self, arg):
        """Stops the simulation"""
        if self.simulation_running:
            self.system.running = False
            self.simulation_thread.join()
            self.simulation_running = False
            print("Simulation stopped.")
        else:
            print("No simulation running.")

    def do_exit(self, arg):
        """Exits the simulator."""
        if self.simulation_running:
            self.do_stop("")
        return True

    def postloop(self):
        print("Goodbye!")


def run_cli(simulation_manager):
    cli = RadioSimulatorCLI(simulation_manager)
    cli.cmdloop()


class MainProgram:
    def __init__(self):
        self.system_instances = []

    def create_system_instance(self, id):
        instance = SystemInstance(id)
        self.system_instances.append(instance)
        instance.start()

    def stop_system_instances(self):
        for instance in self.system_instances:
            instance.stop()


if __name__ == "__main__":
    main_program = MainProgram()

    # Create system instances
    for i in range(3):
        main_program.create_system_instance(i)

    # Add events to the first system instance for testing
    # Add events to the first system instance for testing
    system_instance = main_program.system_instances[0]
    system_instance.add_event(3, "Start Call", 10)  # Event with priority 1 and a delay of 2.55 seconds
    system_instance.add_event(2, "Event 2", 5)  # Event with priority 2 and a delay of 1.25 seconds
    system_instance.add_event(1, "Emergency Event", 5)  # Emergency event with immediate processing and reprocess
    system_instance.add_event(0, "End Call", 5.0)  # Event to end a call and free the channel after 5 seconds

    # Add a busy command that will be processed when the channel is free
    # system_instance.busy_queue.put((1, time.time(), "Busy Command", {'force_process': True}))

    # Run for a short period and then stop
    # time.sleep(5)
    # main_program.stop_system_instances()

# Example usage
# simulation_manager = SimulationManager()

# Create and start the CLI thread
# cli_thread = threading.Thread(target=run_cli, args=(simulation_manager,))
# cli_thread.daemon = True
# cli_thread.start()

# try:
#    while True:
#        time.sleep(0.1)
# except KeyboardInterrupt:
#    pass
