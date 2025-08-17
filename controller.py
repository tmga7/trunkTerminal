# tmga7/trunkterminal/trunkTerminal-17c921e61672f1a12e0888c6d82068578d9f6e2b/controller.py
# controller.py
import heapq
import time
from collections import deque, defaultdict
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
        self.active_calls: Dict[int, RadioCall] = {}
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
        self.event_bus.subscribe(UnitEndTransmissionCommand, self.handle_unit_end_transmission)
        self.event_bus.subscribe(CallTeardownCommand, self.handle_call_teardown)
        self.event_bus.subscribe(ConsoleInitiateCallCommand, self.handle_console_initiate_call)

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

    def handle_unit_end_transmission(self, command: UnitEndTransmissionCommand):
        """
        Handles the 'dekey' from a unit, starting the hangtime timer or an immediate teardown.
        """
        call = self.active_calls.get(command.call_id)
        if not call or call.status != CallStatus.ACTIVE:
            return  # Call is already over or doesn't exist

        talkgroup = call.talkgroup
        print(f"\n--- Unit {command.unit_id} Ended Transmission on Call {call.id} (TG: {talkgroup.alias}) ---")

        if talkgroup.ptt_id and talkgroup.hangtime > 0:
            hangtime_seconds = talkgroup.hangtime / 1000.0
            print(f"  -> Talkgroup has ptt_id enabled. Scheduling call teardown in {hangtime_seconds:.2f}s.")
            teardown_event = CallTeardownCommand(call_id=call.id)
            self.schedule_event(hangtime_seconds, teardown_event)
        else:
            print("  -> No hangtime. Scheduling immediate call teardown.")
            teardown_event = CallTeardownCommand(call_id=call.id)
            self.schedule_event(0, teardown_event)  # Schedule immediately

    def handle_call_teardown(self, command: CallTeardownCommand):
        """
        Releases all channel resources associated with a call across all involved sites.
        """
        call = self.active_calls.get(command.call_id)
        if not call:
            return

        # Check if another unit has keyed up during the hangtime
        if call.status == CallStatus.ACTIVE and not call.talkgroup.ptt_id:
            # This can happen if a new call starts on the same TG during hangtime.
            # In a more complex model, we'd check if the 'initiating_unit' changed.
            # For now, we'll assume if it's still ACTIVE, someone else keyed up.
            print(f"  -> Teardown for Call {call.id} cancelled; another transmission has started.")
            return

        print(f"--- Tearing Down Call {call.id} (TG: {call.talkgroup.alias}) ---")
        call.status = CallStatus.ENDED

        for site_id, voice_channel in call.assigned_channels_by_site.items():
            site = self.radio_system.get_site(site_id, self.zone_id)
            if site:
                site.release_voice_channel(voice_channel)

        # Remove the call from the active list
        del self.active_calls[command.call_id]
        print(f"----------------------------------------------------------\n")

        # After a call ends, check if we can service a queued call
        self._service_blocked_calls()

    def handle_console_initiate_call(self, command: ConsoleInitiateCallCommand):
        """Handles a console PTT, preempting any active call on the talkgroup."""
        console = self.radio_system.get_unit(command.console_id, self.zone_id)
        talkgroup = self.radio_system.get_talkgroup(command.talkgroup_id, self.zone_id)

        if not (console and talkgroup):
            return

        print(f"\n--- CONSOLE PTT on TG {talkgroup.alias} from Console {console.id} ---")

        # Check if a call is already active on this talkgroup
        active_call_on_tg = None
        for call in self.active_calls.values():
            if call.talkgroup == talkgroup and call.status == CallStatus.ACTIVE:
                active_call_on_tg = call
                break

        if active_call_on_tg:
            # Preempt the existing call
            print(f"  -> PREEMPTING active Call {active_call_on_tg.id}. New initiator: Console {console.id}.")
            active_call_on_tg.initiating_unit = console
        else:
            # If no call is active, the console initiates a new one.
            # This reuses the existing group voice request logic but with high priority.
            print(f"  -> No active call. Console {console.id} is initiating a new call.")
            request_packet = GroupVoiceServiceRequest(
                unit_id=console.id,
                talkgroup_id=talkgroup.id,
                priority=command.priority
            )
            self.publish_event(request_packet)


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

        # --- THIS IS THE CRITICAL CHECK ---
        if not (unit and talkgroup and unit.state == UnitState.IDLE_AFFILIATED):
            print(f"  -> ZoneController: Call request from Unit {command.unit_id} denied (Unit not idle/affiliated).")
            return

        # The rest of this logic is now handled in handle_group_voice_request,
        # but we still need to create the initial packet.
        call_request_packet = GroupVoiceServiceRequest(
            unit_id=command.unit_id,
            talkgroup_id=command.talkgroup_id,
            priority=talkgroup.priority  # Use the TG's base priority
        )
        self.publish_event(call_request_packet)

    def handle_group_voice_request(self, packet: GroupVoiceServiceRequest):
        """Handles a GRP_V_REQ packet, orchestrating a complex, multi-site call setup."""
        unit = self.radio_system.get_unit(packet.unit_id, self.zone_id)
        talkgroup = self.radio_system.get_talkgroup(packet.talkgroup_id, self.zone_id)
        zone = self.radio_system.get_zone(self.zone_id)

        if not all([unit, talkgroup, zone]):
            print(f"  -> Zone {self.zone_id}: Invalid call request details. Dropping.")
            return

        print(f"\n--- GRP_V_REQ Received from Unit {unit.id} for TG {talkgroup.alias} (Zone {self.zone_id}) ---")

        # 1. Find all sites with affiliated units for this talkgroup
        required_sites = defaultdict(list)
        all_affiliated_units = []
        for site in zone.sites.values():
            if site.status != SiteStatus.ONLINE:
                continue
            for registration in site.registrations:
                if isinstance(registration, Unit) and registration.affiliated_talkgroup == talkgroup:
                    required_sites[site.id].append(registration)
                    if registration not in all_affiliated_units:
                        all_affiliated_units.append(registration)

        if not required_sites:
            print(f"  -> No units affiliated with TG {talkgroup.id} in this zone. Call dropped.")
            # In a real system, we'd send a DENY_RSP.
            return

        # 2. Determine final call mode (downgrade if necessary)
        final_mode = talkgroup.mode
        if final_mode == CallMode.MIXED:
            if any(not u.tdma_capable for u in all_affiliated_units):
                print(f"  -> FDMA-only unit detected. Downgrading call to {CallMode.FDMA.name}.")
                final_mode = CallMode.FDMA
            else:
                final_mode = CallMode.TDMA  # Default mixed to TDMA if all are capable

        # 3. Create the parent RadioCall object
        new_call_id = int(self.current_time * 1000) + unit.id  # Simple unique ID
        call = RadioCall(id=new_call_id, initiating_unit=unit, talkgroup=talkgroup, mode=final_mode)
        self.active_calls[new_call_id] = call
        unit.current_call = call  # Associate the call with the unit
        unit.state = UnitState.CALL_REQUESTED  # Update unit state
        print(
            f"  -> Created Parent Call {call.id} with mode {call.mode.name}. Required sites: {list(required_sites.keys())}")

        # 4. Attempt to allocate channels on all required sites
        successful_sites = {}
        failed_sites = {}
        for site_id in required_sites.keys():
            site = self.radio_system.get_site(site_id, self.zone_id)
            allocated_vc = site.find_and_assign_voice_channel(call, final_mode)
            if allocated_vc:
                successful_sites[site_id] = allocated_vc
            else:
                failed_sites[site_id] = None

        # 5. Handle failures based on the 'all_start' policy
        if failed_sites:
            print(f"  -> Channel allocation failed on sites: {list(failed_sites.keys())}")
            # --- NEW QUEUING LOGIC ---
            print(f"  -> All channels busy. Queuing call {call.id} for TG {talkgroup.alias}.")
            call.status = CallStatus.QUEUED
            # Use a tuple for the priority queue: (priority, time, call_object)
            heapq.heappush(self.call_busy_queue, (packet.priority, self.current_time, call))

            # Send the Queued Response OSP to the initiating unit
            queued_rsp = QueuedResponse(
                unit_id=unit.id,
                talkgroup_id=talkgroup.id
            )
            self.schedule_event(0.05, queued_rsp)
            return  # Stop processing this request for now

        # 6. Grant the call on the successful sites
        if not successful_sites:
            print(f"  -> No sites available for the call. Call failed.")
            call.end()
            del self.active_calls[call.id]
            return

        call.status = CallStatus.ACTIVE
        for site_id, vc in successful_sites.items():
            call.assigned_channels_by_site[site_id] = vc

        # --- REPLACE THE OLD #7 BLOCK WITH THIS ---
        # 7. Broadcast the Group Voice Channel Grant to all involved units
        print(f"  -> Broadcasting call grant on all successful sites...")
        for site_id, vc in successful_sites.items():
            # In a real system, this would be a broadcast OSP.
            # We simulate it by creating a grant for each affiliated unit on that site.
            for unit_on_site in required_sites[site_id]:
                grant_packet = GroupVoiceChannelGrant(
                    unit_id=unit_on_site.id,
                    talkgroup_id=talkgroup.id,
                    call_id=call.id,
                    channel_id=vc.channel_id,
                    tdma_slot=vc.tdma_slot
                )
                self.schedule_event(0.05, grant_packet)

        print(f"  -> Call {call.id} is now ACTIVE on sites: {list(successful_sites.keys())}.")
        print(f"---------------------------------------------------------------------\n")

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
        if not self.call_busy_queue:
            return  # Nothing to do

        print(f"--- Servicing Blocked Call Queue (size: {len(self.call_busy_queue)}) ---")
        # Peek at the highest priority call without removing it
        priority, time, queued_call = self.call_busy_queue[0]

        # Re-run the call setup logic. We create a new request packet from the queued call.
        # A full implementation would check resource availability first, but for this test,
        # we assume the channel is now free.
        print(
            f"  -> Retrying call {queued_call.id} for Unit {queued_call.initiating_unit.id} on TG {queued_call.talkgroup.alias}")
        heapq.heappop(self.call_busy_queue)  # Remove from queue

        # We can re-use the original request logic by creating a new packet.
        retry_packet = GroupVoiceServiceRequest(
            unit_id=queued_call.initiating_unit.id,
            talkgroup_id=queued_call.talkgroup.id,
            priority=priority
        )
        # Publish the event to re-run the allocation logic
        self.publish_event(retry_packet)

    def get_queue_status(self) -> str:
        """Returns a string summarizing the state of the event and busy queues."""
        return "Queue status display logic here."
