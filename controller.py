# controller.py
import heapq
import time
from collections import deque
from event_bus import EventBus
from models import *

from events import *
from p25.packets import P25Packet
from p25.control_status import (
    UnitRegistrationRequest,
    UnitRegistrationResponse,
    GroupAffiliationRequest,
    GroupAffiliationResponse,
    RegistrationStatus,
    AffiliationStatus
)
from p25.voice_service import GroupVoiceServiceRequest


# Forward declaration for type hinting to avoid circular import
class RadioSystem:
    pass


class ZoneController:
    """
    Orchestrates all activity within a single Zone (RFSS), processing
    P25 packets and managing simulation events.
    """

    def __init__(self, radio_system: 'RadioSystem', zone_id: int):
        self.radio_system = radio_system
        self.zone_id = zone_id
        self.event_bus = EventBus()
        self.event_queue = []  # Priority queue: (execution_time, priority, event)
        self.call_busy_queue = deque() # Simple FIFO queue for now
        self.current_time = 0.0
        self._register_handlers()

    def _register_handlers(self):
        """Subscribe methods to handle specific events and packets."""
        # --- High-Level Simulation Commands ---
        self.event_bus.subscribe(UnitPowerOnCommand, self.handle_unit_power_on_command)
        self.event_bus.subscribe(UnitInitiateCallCommand, self.handle_unit_initiate_call_command)
        self.event_bus.subscribe(ControlChannelEstablishRequest, self.handle_control_channel_establish)

        # --- P25 Inbound Signaling Packets (ISPs) ---
        self.event_bus.subscribe(UnitRegistrationRequest, self.handle_unit_registration_request)
        self.event_bus.subscribe(GroupAffiliationRequest, self.handle_group_affiliation_request)
        self.event_bus.subscribe(GroupVoiceServiceRequest, self.handle_group_voice_request)

    def schedule_event(self, delay_seconds: float, event: Event):
        """Schedules an event or packet to be processed in the future."""
        execution_time = self.current_time + delay_seconds
        # Use event's priority attribute for sorting in the heap
        heapq.heappush(self.event_queue, (execution_time, event.priority, event))

    def publish_event(self, event: Event):
        """A convenience method to publish an event for immediate processing."""
        self.schedule_event(0, event)

    def tick(self, delta_time: float):
        """The main heartbeat of the simulation."""
        self.current_time += delta_time
        while self.event_queue and self.event_queue[0][0] <= self.current_time:
            execution_time, priority, event = heapq.heappop(self.event_queue)
            self.event_bus.publish(event)
        self._service_blocked_calls()

    # --- Command Handlers (triggered by scenario/CLI) ---

    def handle_unit_power_on_command(self, command: UnitPowerOnCommand):
        """Handles the high-level command to power on a unit."""
        unit = self.radio_system.get_unit(command.unit_id, self.zone_id)
        if unit:
            # Tell the unit to power on. The unit itself will generate
            # the first P25 packet (U_REG_REQ) needed.
            initial_packet = unit.power_on()
            if initial_packet:
                # Schedule the unit's request packet to be processed by the controller.
                # We add a small delay to simulate transmission time.
                self.schedule_event(0.1, initial_packet)

    def handle_unit_initiate_call_command(self, command: UnitInitiateCallCommand):
        """Handles the high-level command for a unit to start a call using the new priority logic."""
        unit = self.radio_system.get_unit(command.unit_id, self.zone_id)
        talkgroup = self.radio_system.get_talkgroup(command.talkgroup_id, self.zone_id)

        if not (unit and talkgroup and unit.state == UnitState.IDLE_AFFILIATED):
            print(f"ZoneController: Call request from Unit {command.unit_id} denied (invalid state or objects).")
            return

        final_priority = talkgroup.priority  # Start with the talkgroup's priority

        # 1. Check if the unit is in a group with a non-default priority
        if unit.groups:
            # Simple logic: use the priority of the first group the unit belongs to
            group_priority = unit.groups[0].priority
            # If the TG priority is just NORMAL, the group's default is a better choice
            if final_priority == EventPriority.NORMAL and group_priority != EventPriority.NORMAL:
                final_priority = group_priority
                print(f"  -> Using Group default priority: {final_priority.name}")

        # 2. Check if the initiator is a Console (highest priority)
        if isinstance(unit, Console):
            final_priority = EventPriority.PREEMPT
            print(f"  -> Console preemption: Using {final_priority.name} priority.")

        call_request_packet = GroupVoiceServiceRequest(
            unit_id=command.unit_id,
            talkgroup_id=command.talkgroup_id,
            priority=final_priority
        )
        print(f"  -> Final call priority for TG {talkgroup.alias}: {final_priority.name}")
        self.publish_event(call_request_packet)

    # --- P25 ISP Handlers (System Logic) ---

    def handle_unit_registration_request(self, packet: UnitRegistrationRequest):
        """Handles a U_REG_REQ packet from a unit."""
        unit = self.radio_system.get_unit(packet.unit_id, self.zone_id)
        zone = self.radio_system.get_zone(self.zone_id)
        response_packet = None

        if not unit or not zone:
            # This case shouldn't happen in our simulation but is critical in a real system
            return

        # Simple logic: register to the first available online site
        online_sites = [s for s in zone.sites.values() if s.status == SiteStatus.ONLINE]
        if online_sites:
            best_site = online_sites[0]
            unit.current_site = best_site
            best_site.registrations.append(unit)
            print(f"ZoneController (Zone {self.zone_id}): Unit {unit.id} registered on Site {best_site.id}.")
            response_packet = UnitRegistrationResponse(
                status=RegistrationStatus.GRANTED,
                unit_id=unit.id,
                site_id=best_site.id
            )
        else:
            print(f"ZoneController (Zone {self.zone_id}): No sites available for Unit {unit.id} to register.")
            response_packet = UnitRegistrationResponse(
                status=RegistrationStatus.FAILED_SYSTEM_FULL, # Not quite accurate, but close enough for now
                unit_id=unit.id,
                site_id=0
            )

        # "Send" the response back to the unit by calling its handler.
        # The unit's own logic will then decide what to do next.
        next_isp = unit.handle_registration_response(response_packet)
        if next_isp:
            # If the unit's logic generated another packet (like GRP_AFF_REQ), schedule it.
            self.schedule_event(0.1, next_isp)


    def handle_group_affiliation_request(self, packet: GroupAffiliationRequest):
        """Handles a GRP_AFF_REQ packet from a unit."""
        unit = self.radio_system.get_unit(packet.unit_id, self.zone_id)
        talkgroup = self.radio_system.get_talkgroup(packet.talkgroup_id, self.zone_id)
        response_packet = None

        if unit and talkgroup:
            unit.affiliated_talkgroup = talkgroup
            response_packet = GroupAffiliationResponse(
                status=AffiliationStatus.GRANTED,
                unit_id=unit.id,
                talkgroup_id=talkgroup.id
            )
        elif not talkgroup:
             response_packet = GroupAffiliationResponse(
                status=AffiliationStatus.FAILED_UNKNOWN_GROUP,
                unit_id=unit.id,
                talkgroup_id=packet.talkgroup_id
            )

        if response_packet:
            # "Send" the response to the unit.
            unit.handle_affiliation_response(response_packet)


    def handle_group_voice_request(self, packet: GroupVoiceServiceRequest):
        """Handles a GRP_V_REQ packet, initiating a call."""
        unit = self.radio_system.get_unit(packet.unit_id, self.zone_id)
        talkgroup = self.radio_system.get_talkgroup(packet.talkgroup_id, self.zone_id)
        site = unit.current_site

        if not all([unit, talkgroup, site]):
            print(f"ZoneController: Invalid call request from unit {packet.unit_id}")
            return

        if site.has_available_voice_channel():
            print(f"ZoneController: Granting call for Unit {unit.id} on TG {talkgroup.alias}.")
            # TODO: Add logic to create a RadioCall and send GRP_V_CH_GRANT
        else:
            print(f"ZoneController: No channels available. Queuing call for Unit {unit.id} on TG {talkgroup.alias}.")
            heapq.heappush(self.call_busy_queue, (packet.priority, self.current_time, packet))


    def handle_control_channel_establish(self, event: ControlChannelEstablishRequest):
        """Handles the internal request to create the CC call."""
        print(f"ZoneController (Zone {self.zone_id}): Establishing permanent CC for Site {event.site_id} on Channel {event.channel_id}.")
        # TODO: Logic to create a special, permanent 'RadioCall' for the CC


    # --- System Initialization ---
    def initialize_system(self):
        """Initializes the zone this controller manages."""
        print(f"\n--- Initializing Zone {self.zone_id} ---")
        zone = self.radio_system.get_zone(self.zone_id)
        if not zone:
            print(f"Error: Zone {self.zone_id} not found.")
            return

        for site in zone.sites.values():
            control_channel_event = site.initialize(zone_id=self.zone_id)
            if control_channel_event:
                self.publish_event(control_channel_event)

        for console in zone.consoles.values():
            console.power_on() # Using the inherited Unit method
            for site in zone.sites.values():
                if site.status == SiteStatus.ONLINE:
                    site.registrations.append(console)
            print(f"  -> Console {console.id} ({console.alias}): Powered ON and registered on all online sites.")
        print(f"--- Zone {self.zone_id} Initialization Complete ---\n")


    # --- Misc Methods ---
    def _service_blocked_calls(self):
        """Checks if any blocked calls can now be processed."""
        # This logic remains largely the same for now
        pass

    def get_queue_status(self) -> str:
        """Returns a string summarizing the state of the event and busy queues."""
        # This method is still useful for debugging
        # ... (implementation is the same) ...
        return "Queue status display logic here."