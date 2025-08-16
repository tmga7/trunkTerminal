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

    def __init__(self, radio_system: 'RadioSystem'):
        self.radio_system = radio_system
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

    def schedule_event(self, delay_seconds: float, event: Event):
        """Schedules an event to be processed in the future."""
        execution_time = self.current_time + delay_seconds
        heapq.heappush(self.event_queue, (execution_time, event))

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
            execution_time, event = heapq.heappop(self.event_queue)
            self.event_bus.publish(event)

    # --- Event Handlers ---

    def handle_unit_power_on(self, event: UnitPowerOnRequest):
        """Handles the initial power-on request for a unit."""
        unit = self.radio_system.get_unit(event.unit_id)
        if unit and not unit.powered_on:
            unit.power_on()
            # After powering on, a real radio waits a moment then tries to register.
            # We simulate this by scheduling the registration request.
            print(f"ZoneController: Scheduling registration for Unit {unit.id} in 2 seconds.")
            self.schedule_event(2.0, UnitRegistrationRequest(unit_id=unit.id))

    def handle_unit_registration(self, event: UnitRegistrationRequest):
        """Handles a unit's request to register with the system."""
        unit = self.radio_system.get_unit(event.unit_id)
        if not unit:
            return

        # In a real system, we'd have logic to find the "best signal" site.
        # For now, we'll just assign it to the first available site.
        if self.radio_system.config.sites:
            best_site = list(self.radio_system.config.sites.values())[0]
            unit.move_to_site(best_site)
            # Announce that the registration was successful.
            self.publish_event(UnitRegisteredEvent(unit_id=unit.id, site_id=best_site.id))
            print(f"ZoneController: Unit {unit.id} successfully registered on Site {best_site.id}.")
        else:
            print(f"ZoneController: No sites available for Unit {unit.id} to register.")

    def initialize_system(self):
        """
        Runs the startup sequence for the entire radio system.
        This should be called once after the ZoneController is created.
        """
        print("\n--- System Initialization Started ---")
        wacn = self.radio_system.config.wacn
        for zone in wacn.zones.values():
            print(f"Initializing Zone {zone.id} ({zone.alias})...")

            # 1. Initialize all sites in the zone
            for site in zone.sites.values():
                site.status = SiteStatus.INITIALIZING
                self._initialize_site(site)

            # 2. Initialize all consoles in the zone
            for console in zone.consoles.values():
                self._initialize_console(console, zone)
        print("--- System Initialization Complete ---\n")

    def _initialize_site(self, site: Site):
        """Performs the startup procedure for a single site."""

        # Check for at least one enabled channel
        enabled_channels = [c for c in site.channels.values() if c.enabled]
        if not enabled_channels:
            site.status = SiteStatus.FAILED
            print(f"  -> Site {site.id} ({site.alias}): FAILED (No enabled channels).")
            return

        # Find and assign a control channel
        possible_ccs = sorted([c for c in enabled_channels if c.control], key=lambda c: c.id)
        if not possible_ccs:
            site.status = SiteStatus.FAILED
            print(f"  -> Site {site.id} ({site.alias}): FAILED (No suitable control channel).")
            return

        site.control_channel = possible_ccs[0]
        site.status = SiteStatus.ONLINE
        print(f"  -> Site {site.id} ({site.alias}): ONLINE. Control Channel set to {site.control_channel.id}.")

        # TODO: Create a long-lasting "ControlChannelCall" for this channel.

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
