import heapq
import time
import cmd
import threading

class Radio:
    def __init__(self, id):
        self.id = id
        self.current_call = None

    def ptt(self, system, talkgroup, duration):
        event = {"type": "ptt", "radio": self, "talkgroup": talkgroup, "duration": duration}
        system.schedule_user_event(system.current_time, event)
        print(f"Radio {self.id}: PTT pressed for {duration}ms on TG {talkgroup} at {system.current_time}")

    def end_call(self):
        if self.current_call:
            print(f"Radio {self.id}: Call ended on TG {self.current_call['talkgroup']} at {system.current_time}")
            self.current_call = None

class System:
    def __init__(self):
        self.system_event_queue = []
        self.user_command_queue = []
        self.trunked_radio_queue = []
        self.channels = {}
        self.current_time = 0
        self.running = True
        self.radios = []

    def schedule_system_event(self, event_data):
        heapq.heappush(self.system_event_queue, (time.time(), event_data))

    def schedule_user_event(self, event_time, event_data):
        heapq.heappush(self.user_command_queue, (event_time, event_data))

    def schedule_trunked_queue_event(self, event_time, event_data):
        heapq.heappush(self.trunked_radio_queue, (event_time, event_data))

    def process_system_events(self):
        while self.system_event_queue:
            event_time, event_data = heapq.heappop(self.system_event_queue)
            self.handle_system_event(event_data)

    def handle_system_event(self, event):
        pass

    def process_user_events(self):
        if self.user_command_queue:
            next_event_time, next_event_data = self.user_command_queue[0]
            if next_event_time <= self.current_time:
                _, event_data = heapq.heappop(self.user_command_queue)
                self.handle_user_event(event_data)

    def handle_user_event(self, event):
        if event["type"] == "ptt":
            self.start_call(event["radio"], event["talkgroup"], event["duration"])
        elif event['type'] == 'call_end':
            self.end_call(event['radio'], event['talkgroup'])

    def process_trunked_queue(self):
        if self.trunked_radio_queue:
            next_event_time, next_event_data = self.trunked_radio_queue[0]
            if next_event_time <= self.current_time:
                _, event_data = heapq.heappop(self.trunked_radio_queue)
                self.start_call(event_data["radio"], event_data["talkgroup"], event_data["duration"])

    def start_call(self, radio, talkgroup, duration):
        if talkgroup not in self.channels:
            self.channels[talkgroup] = {"in_use": False}

        if not self.channels[talkgroup]["in_use"]:
            self.channels[talkgroup]["in_use"] = True
            radio.current_call = {'talkgroup': talkgroup}
            print(f"System: Starting call on TG {talkgroup} at {self.current_time}")
            self.schedule_user_event(self.current_time + duration / 1000, {"type": "call_end", "radio": radio, "talkgroup": talkgroup})
        else:
            print(f"System: Talkgroup {talkgroup} is busy. Queuing call at {self.current_time}")
            self.schedule_trunked_queue_event(self.current_time, {"type": "ptt", "radio": radio, "talkgroup": talkgroup, "duration": duration})

    def end_call(self, radio, talkgroup):
        if talkgroup in self.channels and self.channels[talkgroup]["in_use"]:
            self.channels[talkgroup]["in_use"] = False
            radio.end_call()
            print(f"System: Call ended on TG {talkgroup} at {self.current_time}")
            self.process_trunked_queue()

    def run_simulation(self, end_time):
        while self.current_time <= end_time and self.running:
            self.process_system_events()
            self.process_user_events()
            self.process_trunked_queue()
            self.current_time += 0.001
            time.sleep(0.001)
        self.running = True

class RadioSimulatorCLI(cmd.Cmd):
    intro = "Welcome to the Trunked Radio Simulator. Type help or ? to list commands.\n"
    prompt = "(RadioSim) "

    def __init__(self, system):
        super().__init__()
        self.system = system
        self.simulation_running = False
        self.simulation_thread = None

    def do_ptt(self, arg):
        """Usage: ptt <radio_id> <talkgroup> <duration>
        Initiates a PTT call."""
        try:
            radio_id, talkgroup, duration = map(int, arg.split())
            radio = next((r for r in self.system.radios if r.id == radio_id), None)
            if radio:
                radio.ptt(self.system, talkgroup, duration)
            else:
                print(f"Radio {radio_id} not found.")

        except ValueError:
            print("Invalid arguments. Use: ptt <radio_id> <talkgroup> <duration>")

    def do_schedule(self, arg):
        """Usage: schedule <time> <radio_id> <talkgroup> <duration>
        Schedules a PTT call at a specific simulated time."""
        try:
            sim_time, radio_id, talkgroup, duration = map(int, arg.split())
            radio = next((r for r in self.system.radios if r.id == radio_id), None)
            if radio:
                self.system.schedule_user_event(sim_time, {"type": "ptt", "radio": radio, "talkgroup": talkgroup, "duration": duration})
            else:
                print(f"Radio {radio_id} not found.")
        except ValueError:
            print("Invalid arguments. Use: schedule <time> <radio_id> <talkgroup> <duration>")

    def do_run(self, arg):
        """Usage: run <end_time>
        Starts the simulation in a separate thread."""
        if self.simulation_running:
            print("Simulation is already running.")
            return

        try:
            end_time = int(arg)
            self.simulation_running = True
            self.simulation_thread = threading.Thread(target=self.run_simulation_thread, args=(end_time,))
            self.simulation_thread.start()
            print("Simulation started in background.")

        except ValueError:
            print("Invalid argument. Use: run <end_time>")

    def run_simulation_thread(self, end_time):
        self.system.run_simulation(end_time)
        self.simulation_running = False
        print("Simulation finished.")

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

    def preloop(self):
        self.system.radios = [Radio(1), Radio(2), Radio(3)]
        pass

    def postloop(self):
        print("Goodbye!")

# Example usage
system = System()
cli = RadioSimulatorCLI(system)
cli.cmdloop()