# zone_controller.py
import heapq
import time
from collections import deque
from event_bus import EventBus
from events import *
from models import *



# Forward declaration for type hinting to avoid circular import
class RadioSystem:
    pass


class ZoneController:
    """
    Orchestrates all activity within a RadioSystem, managing events,
    call queuing, and scheduling.
    """

    def __init__(self, radio_system: 'RadioSystem', zone_id: int):
        self.radio_system = radio_system
        self.zone_id = zone_id  # Each controller is tied to a specific zone
        self.event_bus = EventBus()


        # Priority queue for scheduled events: (execution_time, event)
        self.event_queue = []

        # Simple FIFO queue for calls waiting for resources
        self.call_busy_queue = deque()

        self._register_handlers()

        # Keep track of simulation time
        self.current_time = 0.0

    def _register_handlers(self):
        """Subscribe methods to handle specific events."""
        self.event_bus.subscribe(UnitPowerOnRequest, self.handle_unit_power_on)
        self.event_bus.subscribe(UnitRegistrationRequest, self.handle_unit_registration)
        self.event_bus.subscribe(CallRequestEvent, self.handle_call_request)  # New handler
        self.event_bus.subscribe(ControlChannelCallRequest, self.handle_control_channel_call)


    def schedule_event(self, delay_seconds: float, event: Event):
        """Schedules an event to be processed in the future."""
        execution_time = self.current_time + delay_seconds
        heapq.heappush(self.event_queue, (execution_time, event.priority, event))

    def publish_event(self, event: Event):
        """A convenience method to publish an event for immediate processing."""
        self.schedule_event(0, event)

    def tick(self, delta_time: float):
        """
        The main heartbeat of the simulation. Advances time and processes due events.
        This should be called continuously from the main simulation loop.
        """
        self.current_time += delta_time

        # Process all events that are due
        while self.event_queue and self.event_queue[0][0] <= self.current_time:
            execution_time, priority, event = heapq.heappop(self.event_queue)
            self.event_bus.publish(event)

        # After processing events, check if we can service any blocked calls
        self._service_blocked_calls()

    # --- Event Handlers ---

    def handle_unit_registration(self, event: UnitRegistrationRequest):
        """Handles a unit's request to register with the system."""
        unit = self.radio_system.get_unit(event.unit_id, self.zone_id)
        if not unit:
            return

        zone = self.radio_system.get_zone(self.zone_id)
        if not zone:
            print(f"ZoneController: Zone {self.zone_id} not found.")
            return

        # Find a site within this controller's zone.
        if zone.sites:
            best_site = list(zone.sites.values())[0]
            unit.current_site = best_site
            best_site.registrations.append(unit)

            self.publish_event(UnitRegisteredEvent(unit_id=unit.id, site_id=best_site.id))
            print(
                f"ZoneController (Zone {self.zone_id}): Unit {unit.id} successfully registered on Site {best_site.id}.")
        else:
            print(f"ZoneController (Zone {self.zone_id}): No sites available for Unit {unit.id} to register.")

    def initialize_system(self):
        """Initializes the specific zone this controller manages."""
        print(f"\n--- Initializing Zone {self.zone_id} ---")
        zone = self.radio_system.get_zone(self.zone_id)
        if not zone:
            print(f"Error: Zone {self.zone_id} not found in configuration.")
            return

        for site in zone.sites.values():
            self._initialize_site(site)

        for console in zone.consoles.values():
            self._initialize_console(console, zone)
        print(f"--- Zone {self.zone_id} Initialization Complete ---\n")


    def handle_unit_power_on(self, event: UnitPowerOnRequest):
        """Handles the initial power-on request for a unit."""
        unit = self.radio_system.get_unit(event.unit_id)
        if unit and not unit.powered_on:
            unit.power_on()
            # After powering on, a real radio waits a moment then tries to register.
            # We simulate this by scheduling the registration request.
            print(f"ZoneController: Scheduling registration for Unit {unit.id} in 2 seconds.")
            self.schedule_event(2.0, UnitRegistrationRequest(unit_id=unit.id))


    def handle_control_channel_call(self, event: ControlChannelCallRequest):
        """Handles the creation of the long-running control channel call."""
        # TODO: Logic to create a special 'RadioCall' that represents
        # the active control channel. This call would likely never end
        # unless a failure event is injected.
        print(f"ZoneController (Zone {self.zone_id}): Establishing permanent control channel call for Site {event.site_id} on Channel {event.channel_id}.")

    def handle_call_request(self, event: CallRequestEvent):
        """Handles a unit's request to make a call."""
        unit = self.radio_system.get_unit(event.unit_id, self.zone_id)
        talkgroup = self.radio_system.get_talkgroup(event.talkgroup_id,
                                                    self.zone_id)  # You'll need to add this to RadioSystem
        site = unit.current_site

        if not unit or not talkgroup or not site:
            print(f"ZoneController: Invalid call request from unit {event.unit_id}")
            return

        # Check for available channel resources at the site
        if site.has_available_voice_channel():  # You'll need to implement this in the Site model
            print(f"ZoneController: Granting call request for Unit {unit.id} on TG {talkgroup.alias}")
            # ... (Logic to start the call) ...
        else:
            # No channels available, add to the busy queue
            print(f"ZoneController: No channels available. Queuing call for Unit {unit.id} on TG {talkgroup.alias}")
            # The priority could come from the talkgroup or group model in a real scenario
            call_priority = event.priority
            heapq.heappush(self.call_busy_queue, (call_priority, self.current_time, event))

    def handle_control_channel_call(self, event: ControlChannelCallRequest):
        """Handles the creation of the long-running control channel call."""
        # TODO: Logic to create a special 'RadioCall' that represents
        # the active control channel. This call would likely never end
        # unless a failure event is injected.
        print(
            f"ZoneController (Zone {self.zone_id}): Establishing permanent control channel call for Site {event.site_id} on Channel {event.channel_id}.")

    def _service_blocked_calls(self):
        """Checks if any blocked calls can now be processed."""
        if not self.call_busy_queue:
            return

        # Check all sites in this zone for available channels
        # This is a simple example; a real system would be more complex
        for site in self.radio_system.get_zone(self.zone_id).sites.values():
            if site.has_available_voice_channel() and self.call_busy_queue:
                # Get the highest priority call from the queue
                priority, request_time, event = heapq.heappop(self.call_busy_queue)
                print(f"ZoneController: Servicing blocked call for Unit {event.unit_id}")
                # Re-publish the event for immediate processing
                self.publish_event(event)

    def _initialize_site(self, site: Site):
        """Performs the startup procedure for a single site by calling its own initialize method."""
        # The site now handles its own initialization logic.
        control_channel_event = site.initialize(zone_id=self.zone_id)

        if control_channel_event:
            # If initialization was successful, publish the event to create the call.
            self.publish_event(control_channel_event)

    def _initialize_console(self, console: Console, zone: RFSS):
        """Brings a console online and registers it with all available sites."""
        console.power_on()
        print(f"  -> Console {console.id} ({console.alias}): Powered ON.")

        # Register the console on every ONLINE site in its home zone
        for site in zone.sites.values():
            if site.status == SiteStatus.ONLINE:
                # We can differentiate registrations by checking the object type
                site.registrations.append(console)
                print(f"    - Registered on Site {site.id} ({site.alias}).")


    def get_queue_status(self) -> str:
        """Returns a string summarizing the state of the event and busy queues."""
        status_lines = []
        status_lines.append(f"  - Event Queue Size: {len(self.event_queue)}")
        if self.event_queue:
            # Show the next 3 events without consuming them from the queue
            next_events = heapq.nsmallest(3, self.event_queue)
            for i, (exec_time, priority, event) in enumerate(next_events):
                time_until = exec_time - self.current_time
                status_lines.append(
                    f"    - Next[{i}]: In {time_until:.2f}s, Prio {priority.name}, Event: {type(event).__name__}"
                )

        status_lines.append(f"\n  - Call Busy Queue Size: {len(self.call_busy_queue)}")
        if self.call_busy_queue:
            # Show the next 3 waiting calls
            next_calls = heapq.nsmallest(3, self.call_busy_queue)
            for i, (priority, req_time, event) in enumerate(next_calls):
                status_lines.append(
                    f"    - Next[{i}]: Prio {priority.name}, Event: {type(event).__name__} (Unit: {event.unit_id})"
                )

        return "\n".join(status_lines)