# controller.py
import heapq
import time
from collections import deque
from event_bus import EventBus
from models import *
from geo_utils import get_distance, estimate_rssi, get_random_point_in_area

from events import *
from p25.packets import *
from p25.control_status import *
from p25.voice_service import *


# --- Constants ---
REGISTRATION_BAN_TIME_SECONDS = 30.0


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
        self.event_queue = []  # Priority queue: (execution_time, priority, counter, event)
        self.call_busy_queue = deque()  # Simple FIFO queue for now
        self.current_time = 0.0
        self.event_counter = 0
        self._register_handlers()

    def _register_handlers(self):
        """Subscribe methods to handle specific events and packets."""
        # --- High-Level Simulation Commands ---
        self.event_bus.subscribe(UnitPowerOnCommand, self.handle_unit_power_on_command)
        self.event_bus.subscribe(UnitInitiateCallCommand, self.handle_unit_initiate_call_command)
        self.event_bus.subscribe(ControlChannelEstablishRequest, self.handle_control_channel_establish)
        self.event_bus.subscribe(UnitUpdateLocationCommand, self.handle_unit_update_location_command)
        self.event_bus.subscribe(UnitScanForSitesCommand, self.handle_unit_scan_for_sites_command)
        self.event_bus.subscribe(UnitUnbanFromSiteCommand, self.handle_unit_unban_from_site_command)

        # --- P25 Inbound Signaling Packets (ISPs) ---
        self.event_bus.subscribe(UnitRegistrationRequest, self.handle_unit_registration_request)
        self.event_bus.subscribe(GroupAffiliationRequest, self.handle_group_affiliation_request)
        self.event_bus.subscribe(GroupVoiceServiceRequest, self.handle_group_voice_request)

    def schedule_event(self, delay_seconds: float, event: Event):
        """Schedules an event or packet to be processed in the future."""
        execution_time = self.current_time + delay_seconds
        heapq.heappush(self.event_queue, (execution_time, event.priority, self.event_counter, event))
        self.event_counter += 1

        event_name = type(event).__name__
        log_msg = f"  (T={execution_time:.2f}s) Zone {self.zone_id}: {event_name}"

        if isinstance(event, InboundSignalingPacket):
            print(f"  [ISP QUEUED] {log_msg} from Unit {event.unit_id}")
        elif isinstance(event, OutboundSignalingPacket):
            if hasattr(event, 'unit_id'):
                print(f"  [OSP QUEUED] {log_msg} to Unit {event.unit_id}")
            else:
                print(f"  [OSP QUEUED] {log_msg}")
        else:
            print(f"  [EVENT QUEUED] {log_msg}")

    def handle_unit_power_on_command(self, command: UnitPowerOnCommand):
        """Handles the high-level command to power on a unit."""
        unit = self.radio_system.get_unit(command.unit_id)
        if not unit:
            print(f"Error: Unit {command.unit_id} not found anywhere in the system.")
            return

        if not unit.location:
            group_area = next((g.area for g in unit.groups if g.area), None)
            if group_area:
                unit.location = get_random_point_in_area(group_area)
                print(f"  -> Unit {unit.id} ({unit.alias}): Using group area. Placed at {unit.location.latitude:.4f}, {unit.location.longitude:.4f}")
            else:
                wacn_area = self.radio_system.config.wacn.area
                unit.location = get_random_point_in_area(wacn_area)
                print(f"  -> Unit {unit.id} ({unit.alias}): No group area. Placed in WACN at {unit.location.latitude:.4f}, {unit.location.longitude:.4f}")

        unit.power_on()
        print(f"  -> Triggering scan for Unit {unit.id}...")
        self.publish_event(UnitScanForSitesCommand(unit_id=unit.id))

    def handle_unit_update_location_command(self, command: UnitUpdateLocationCommand):
        """Handles a unit's location change and triggers a re-scan."""
        unit = self.radio_system.get_unit(command.unit_id, self.zone_id)
        if unit:
            unit.location = command.new_location
            print(f"  -> Unit {unit.id} ({unit.alias}): Location updated. Triggering site re-scan.")
            self.publish_event(UnitScanForSitesCommand(unit_id=unit.id))

    def handle_unit_scan_for_sites_command(self, command: UnitScanForSitesCommand):
        """Scans all non-banned subsites to find the one with the best RSSI."""
        unit = self.radio_system.get_unit(command.unit_id)
        if not unit or not unit.location:
            print(f"Warning: Could not scan for Unit {command.unit_id}. Unit not found or has no location.")
            return

        print(f"--- Unit {unit.id} ({unit.alias}) RF Scan Results ---")
        print(f"Scanning from Location: {unit.location.latitude:.5f}, {unit.location.longitude:.5f}")

        unit.visible_sites.clear()
        best_site, best_subsite, best_rssi, best_zone_id = None, None, -1, None
        scan_results = []

        for zone in self.radio_system.config.wacn.zones.values():
            for site in zone.sites.values():
                if site.status != SiteStatus.ONLINE: continue
                if site.id in unit.banned_sites:
                    print(f"  [Debug] Skipping Site '{site.alias}' (Zone {zone.id}) - Currently banned for this unit.")
                    continue

                for subsite in site.subsites:
                    dist_km = get_distance(unit.location, subsite.location)
                    dbm, rssi_level = estimate_rssi(dist_km, subsite)
                    scan_results.append({ "zone_id": zone.id, "site_alias": site.alias, "subsite_alias": subsite.alias, "distance_km": dist_km, "dbm": dbm, "rssi_level": rssi_level })
                    if rssi_level > best_rssi:
                        best_rssi, best_site, best_subsite, best_zone_id = rssi_level, site, subsite, zone.id

        print("┌" + "─" * 85 + "┐")
        print(f"| {'Zone':<5} | {'Site Alias':<15} | {'Subsite Alias':<15} | {'Distance (km)':<15} | {'RSSI (dBm)':<12} | {'Level':<5} |")
        print("├" + "─" * 85 + "┤")
        for result in sorted(scan_results, key=lambda x: x['rssi_level'], reverse=True):
            print(f"| {result['zone_id']:<5} | {result['site_alias']:<15} | {result['subsite_alias']:<15} | {result['distance_km']:<15.2f} | {result['dbm']:<12.1f} | {result['rssi_level']:<5} |")
        print("└" + "─" * 85 + "┘")

        if best_site and best_rssi > 0:
            print(f"  -> Best signal from Subsite '{best_subsite.alias}' (Site '{best_site.alias}') with RSSI Level {best_rssi}")
            if unit.state == UnitState.SEARCHING_FOR_SITE:
                print(f"  -> Attempting registration on Site '{best_site.alias}'...")
                unit.current_site = best_site
                unit.state = UnitState.REGISTERING
                reg_request = UnitRegistrationRequest(unit_id=unit.id, site_id=best_site.id)
                self.schedule_event(0.1, reg_request)
        else:
            unit.state = UnitState.FAILED
            print(f"  -> FAILED. No usable sites found in range.")

    def handle_unit_unban_from_site_command(self, command: UnitUnbanFromSiteCommand):
        """Removes a site from a unit's ban list."""
        unit = self.radio_system.get_unit(command.unit_id)
        if unit and command.site_id in unit.banned_sites:
            unit.banned_sites.remove(command.site_id)
            print(f"  -> Unit {unit.id} ({unit.alias}): Cool-off period ended. Site {command.site_id} is no longer banned.")

    def publish_event(self, event: Event):
        self.schedule_event(0, event)

    def tick(self, delta_time: float):
        self.current_time += delta_time
        while self.event_queue and self.event_queue[0][0] <= self.current_time:
            execution_time, priority, counter, event = heapq.heappop(self.event_queue)
            self.event_bus.publish(event)
        self._service_blocked_calls()

    def handle_unit_registration_request(self, packet: UnitRegistrationRequest):
        """Handles a U_REG_REQ packet, including failure and banning logic."""
        unit = self.radio_system.get_unit(packet.unit_id)
        site = self.radio_system.get_site(packet.site_id, self.zone_id)
        response_packet = None

        if not (unit and site):
            return

        if len(site.registrations) < 1000:
            site.registrations.append(unit)
            response_packet = UnitRegistrationResponse(status=RegistrationStatus.GRANTED, unit_id=unit.id, site_id=site.id)
        else:
            response_packet = UnitRegistrationResponse(status=RegistrationStatus.FAILED_SYSTEM_FULL, unit_id=unit.id, site_id=site.id)

        next_isp = unit.handle_registration_response(response_packet)

        if response_packet.status != RegistrationStatus.GRANTED:
            self.schedule_event(
                REGISTRATION_BAN_TIME_SECONDS,
                UnitUnbanFromSiteCommand(unit_id=unit.id, site_id=site.id)
            )
            self.publish_event(UnitScanForSitesCommand(unit_id=unit.id))

        elif next_isp:
            self.schedule_event(0.1, next_isp)

    def handle_group_affiliation_request(self, packet: GroupAffiliationRequest):
        """
        Handles a GRP_AFF_REQ packet and sends the appropriate P25 response.
        """
        unit = self.radio_system.get_unit(packet.unit_id, self.zone_id)
        talkgroup = self.radio_system.get_talkgroup(packet.talkgroup_id, self.zone_id)
        response_status = None

        if not unit: return

        if not talkgroup:
            # Per standard, if the group address is invalid, send REFUSED
            response_status = AffiliationStatus.REFUSED
        else:
            # Simple logic for now: all known talkgroups are accepted.
            # In a real system, this would check a provisioning database.
            response_status = AffiliationStatus.ACCEPTED

        response_packet = GroupAffiliationResponse(
            status=response_status,
            unit_id=unit.id,
            talkgroup_id=packet.talkgroup_id
        )

        # "Send" the response back to the unit to be handled by its state machine
        unit.handle_affiliation_response(response_packet)

    # ... (the rest of the ZoneController class remains the same) ...
    def handle_unit_initiate_call_command(self, command: UnitInitiateCallCommand):
        """Handles the high-level command for a unit to start a call using the new priority logic."""
        unit = self.radio_system.get_unit(command.unit_id, self.zone_id)
        talkgroup = self.radio_system.get_talkgroup(command.talkgroup_id, self.zone_id)

        if not (unit and talkgroup and unit.state == UnitState.IDLE_AFFILIATED):
            print(f"ZoneController: Call request from Unit {command.unit_id} denied (invalid state or objects).")
            return

        final_priority = talkgroup.priority

        if unit.groups:
            group_priority = unit.groups[0].priority
            if final_priority == EventPriority.NORMAL and group_priority != EventPriority.NORMAL:
                final_priority = group_priority
                print(f"  -> Using Group default priority: {final_priority.name}")

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
        print(
            f"ZoneController (Zone {self.zone_id}): Establishing permanent CC for Site {event.site_id} on Channel {event.channel_id}.")
        # TODO: Logic to create a special, permanent 'RadioCall' for the CC

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
            console.power_on()
            for site in zone.sites.values():
                if site.status == SiteStatus.ONLINE:
                    site.registrations.append(console)
            print(f"  -> Console {console.id} ({console.alias}): Powered ON and registered on all online sites.")
        print(f"--- Zone {self.zone_id} Initialization Complete ---\n")

    def _service_blocked_calls(self):
        """Checks if any blocked calls can now be processed."""
        pass

    def get_queue_status(self) -> str:
        """Returns a string summarizing the state of the event and busy queues."""
        return "Queue status display logic here."