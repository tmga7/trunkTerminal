# tmga7/trunkterminal/trunkTerminal-17c921e61672f1a12e0888c6d82068578d9f6e2b/controller.py
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

        # --- P25 Outbound Signaling Packets (OSPs) ---
        self.event_bus.subscribe(UnitRegistrationResponse, self.handle_unit_registration_response)
        self.event_bus.subscribe(GroupAffiliationResponse, self.handle_group_affiliation_response)

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
                print(
                    f"  -> Unit {unit.id} ({unit.alias}): Using group area. Placed at {unit.location.latitude:.4f}, {unit.location.longitude:.4f}")
            else:
                wacn_area = self.radio_system.config.wacn.area
                unit.location = get_random_point_in_area(wacn_area)
                print(
                    f"  -> Unit {unit.id} ({unit.alias}): No group area. Placed in WACN at {unit.location.latitude:.4f}, {unit.location.longitude:.4f}")

        if not unit.selected_talkgroup:
            zone = self.radio_system.get_zone(self.zone_id)
            if zone and zone.talkgroups:
                default_tg = next(iter(zone.talkgroups.values()))
                unit.selected_talkgroup = default_tg
                print(f"  -> Unit {unit.id} ({unit.alias}): Auto-selected TG {default_tg.id} ({default_tg.alias}).")

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

                ban_tuple = (zone.id, site.id)
                if ban_tuple in unit.banned_sites:
                    print(f"  [Debug] Skipping Site {site.id} (Zone {zone.id}) - Currently banned for this unit.")
                    continue

                for subsite in site.subsites:
                    dist_km = get_distance(unit.location, subsite.location)
                    dbm, rssi_level = estimate_rssi(dist_km, subsite)
                    scan_results.append({"zone_id": zone.id, "site_alias": site.alias, "subsite_alias": subsite.alias,
                                         "distance_km": dist_km, "dbm": dbm, "rssi_level": rssi_level})
                    if rssi_level > best_rssi:
                        best_rssi, best_site, best_subsite, best_zone_id = rssi_level, site, subsite, zone.id

        print("┌" + "─" * 85 + "┐")
        print(
            f"| {'Zone':<5} | {'Site Alias':<15} | {'Subsite Alias':<15} | {'Distance (km)':<15} | {'RSSI (dBm)':<12} | {'Level':<5} |")
        print("├" + "─" * 85 + "┤")
        for result in sorted(scan_results, key=lambda x: x['rssi_level'], reverse=True):
            print(
                f"| {result['zone_id']:<5} | {result['site_alias']:<15} | {result['subsite_alias']:<15} | {result['distance_km']:<15.2f} | {result['dbm']:<12.1f} | {result['rssi_level']:<5} |")
        print("└" + "─" * 85 + "┘")

        if best_site and best_rssi > 0:
            print(
                f"  -> Best signal from Subsite '{best_subsite.alias}' (Site '{best_site.alias}' in Zone {best_zone_id}) with RSSI Level {best_rssi}")
            if unit.state == UnitState.SEARCHING_FOR_SITE:
                print(f"  -> Attempting registration on Site '{best_site.alias}'...")
                unit.current_site = best_site
                # The ZoneController for the BEST site must handle the registration.
                best_zone_controller = self  # In a multi-controller setup, you'd look up the controller for best_zone_id
                reg_request = UnitRegistrationRequest(unit_id=unit.id, site_id=best_site.id)
                best_zone_controller.schedule_event(0.1, reg_request)
        else:
            unit.state = UnitState.FAILED
            print(f"  -> FAILED. No usable sites found in range.")

    def handle_unit_unban_from_site_command(self, command: UnitUnbanFromSiteCommand):
        """Removes a site from a unit's ban list."""
        unit = self.radio_system.get_unit(command.unit_id)
        if unit:
            # Unban requires a zone_id and site_id, but the command doesn't have it.
            # This part of the logic may need revision if a unit can be banned from multiple sites.
            # For now, we assume the command implies unbanning from a specific site.
            # A better implementation would pass the zone_id in the Unban command.
            pass

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
        response_status = None

        if not (unit and site):
            return

        if len(site.registrations) >= 1000:
            response_status = RegistrationStatus.FAILED_SYSTEM_FULL
        else:
            site.registrations.append(unit)
            response_status = RegistrationStatus.REG_ACCEPT

        response_packet = UnitRegistrationResponse(
            status=response_status,
            unit_id=unit.id,
            site_id=site.id,
            zone_id=self.zone_id
        )
        self.schedule_event(0.1, response_packet)

    def handle_unit_registration_response(self, packet: UnitRegistrationResponse):
        """
        Handles the OSP for registration, delivering it to the correct unit
        and handling the fallout (banning, re-scanning, affiliating).
        """
        unit = self.radio_system.get_unit(packet.unit_id)
        if not unit:
            return

        next_isp = unit.handle_registration_response(packet)

        if next_isp:
            self.schedule_event(0.1, next_isp)

        if unit.state == UnitState.SEARCHING_FOR_SITE:
            # We need to enhance the unban command to be zone-specific
            # For now, we trigger the scan, but the ban will persist until manual clearing or radio power cycle.
            self.publish_event(UnitScanForSitesCommand(unit_id=unit.id))

    def handle_group_affiliation_request(self, packet: GroupAffiliationRequest):
        """
        Handles a GRP_AFF_REQ packet and schedules the appropriate P25 response.
        """
        unit = self.radio_system.get_unit(packet.unit_id, self.zone_id)
        talkgroup = self.radio_system.get_talkgroup(packet.talkgroup_id, self.zone_id)
        response_status = AffiliationStatus.ACCEPTED

        print(talkgroup)

        if not (unit and unit.current_site):
            return

        if not talkgroup:
            response_status = AffiliationStatus.REFUSED
        else:
            if talkgroup.mode == CallMode.TDMA and not unit.tdma_capable:
                response_status = AffiliationStatus.FAILED
                print(
                    f"  -> GRP_AFF: Unit {unit.id} is not TDMA capable for TDMA-only TG {talkgroup.id}. Responding with AFF_FAIL.")

            if talkgroup.valid_sites and unit.current_site.id not in talkgroup.valid_sites:
                response_status = AffiliationStatus.DENIED
                print(
                    f"  -> GRP_AFF: TG {talkgroup.id} is not available on Site {unit.current_site.id}. Responding with AFF_DENY.")

        response_packet = GroupAffiliationResponse(
            status=response_status,
            unit_id=unit.id,
            talkgroup_id=packet.talkgroup_id,
            zone_id=self.zone_id
        )
        self.schedule_event(0.1, response_packet)

    def handle_group_affiliation_response(self, packet: GroupAffiliationResponse):
        """Delivers the affiliation response OSP to the correct unit."""
        unit = self.radio_system.get_unit(packet.unit_id, self.zone_id)
        if unit:
            unit.handle_affiliation_response(packet)
            if unit.state == UnitState.SEARCHING_FOR_SITE:
                self.publish_event(UnitScanForSitesCommand(unit_id=unit.id))

    def handle_unit_initiate_call_command(self, command: UnitInitiateCallCommand):
        """Handles the high-level command for a unit to start a call."""
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
        else:
            print(f"ZoneController: No channels available. Queuing call for Unit {unit.id} on TG {talkgroup.alias}.")
            heapq.heappush(self.call_busy_queue, (packet.priority, self.current_time, packet))

    def handle_control_channel_establish(self, event: ControlChannelEstablishRequest):
        """Handles the internal request to create the CC call."""
        print(
            f"ZoneController (Zone {self.zone_id}): Establishing permanent CC for Site {event.site_id} on Channel {event.channel_id}.")

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