# tmga7/trunkterminal/trunkTerminal-17c921e61672f1a12e0888c6d82068578d9f6e2b/models.py
from dataclasses import dataclass, field
from typing import Dict, List, Union, Optional, Tuple, Set
from enum import Enum, auto
import random

from p25.voice_service import GroupVoiceChannelGrant

from p25.packets import EventPriority
from events import ControlChannelEstablishRequest
from p25.control_status import (
    UnitRegistrationRequest,
    UnitRegistrationResponse,
    GroupAffiliationRequest,
    GroupAffiliationResponse,
    RegistrationStatus,
    AffiliationStatus
)

# --- Constants ---
MAX_AFFILIATION_ATTEMPTS = 3


# --- Enums for State Machines ---

class UnitState(Enum):
    """Represents the operational state of a Unit."""
    POWERED_OFF = "Powered Off"
    SEARCHING_FOR_SITE = "Searching for Site"
    REGISTERING = "Registering"
    IDLE_REGISTERED = "Idle (Registered)"
    AFFILIATING = "Affiliating"
    IDLE_AFFILIATED = "Idle (Affiliated)"
    CALL_REQUESTED = "Call Requested"
    IN_CALL = "In Call"
    FAILED = "Failed"


class SiteStatus(Enum):
    """Represents the operational status of a site."""
    OFFLINE = "Offline"
    INITIALIZING = "Initializing"
    ONLINE = "Online"
    FAILED = "Failed"
    TRUNKING = "Site Trunking"


class CallStatus(Enum):
    IDLE = "Idle"
    REQUESTED = "Requested"
    ACTIVE = "Active"
    QUEUED = "Queued"
    PREEMPTED = "Preempted"
    ENDED = "Ended"


class CallMode(Enum):
    FDMA = "FDMA"
    TDMA = "TDMA"
    MIXED = "MIXED"


# --- Geographic Models ---
@dataclass
class Coordinates:
    """Represents a single GPS coordinate."""
    latitude: float
    longitude: float


@dataclass
class OperationalArea:
    """Defines a rectangular geographic area."""
    top_left: Coordinates
    bottom_right: Coordinates


# --- Core Physical Infrastructure Models ---
@dataclass
class Subsite:
    id: int
    alias: str
    location: Coordinates
    operating_radius: float


@dataclass
class Channel:
    id: int
    freq_tx: float
    freq_rx: float
    enabled: bool
    fdma: bool
    tdma: bool
    control: bool = False
    data: bool = False
    bsi: bool = False


@dataclass
class VoiceChannel:
    """Represents an allocated voice channel resource on a site."""
    channel_id: int
    tdma_slot: Optional[int] = None  # None for FDMA, 1 or 2 for TDMA

    def __hash__(self):
        return hash((self.channel_id, self.tdma_slot))


@dataclass
class Site:
    id: int
    alias: str
    assignment_mode: str
    channels: Dict[int, Channel] = field(default_factory=dict)
    subsites: List[Subsite] = field(default_factory=list)
    status: SiteStatus = SiteStatus.OFFLINE
    control_channel: Channel = None
    registrations: List[Union['Unit', 'Console']] = field(default_factory=list)
    assigned_voice_channels: Dict[VoiceChannel, 'RadioCall'] = field(default_factory=dict)

    def __post_init__(self):
        if not self.subsites:
            raise ValueError(f"Site {self.id} ({self.alias}) must be initialized with at least one subsite.")

    def initialize(self, zone_id: int) -> Optional[ControlChannelEstablishRequest]:
        enabled_channels = [c for c in self.channels.values() if c.enabled]
        if not enabled_channels:
            self.status = SiteStatus.FAILED
            print(f"  -> Site {self.id} ({self.alias}): FAILED (No enabled channels).")
            return None
        possible_ccs = sorted([c for c in enabled_channels if c.control], key=lambda c: c.id)
        if not possible_ccs:
            self.status = SiteStatus.FAILED
            print(f"  -> Site {self.id} ({self.alias}): FAILED (No suitable control channel).")
            return None
        voice_channels = [c for c in enabled_channels if not c.control and (c.fdma or c.tdma)]
        if not voice_channels:
            self.status = SiteStatus.FAILED
            print(f"  -> Site {self.id} ({self.alias}): FAILED (No suitable voice channel).")
            return None
        self.control_channel = possible_ccs[0]
        self.status = SiteStatus.ONLINE
        print(f"  -> Site {self.id} ({self.alias}): ONLINE. Control Channel set to {self.control_channel.id}.")
        return ControlChannelEstablishRequest(
            site_id=self.id,
            zone_id=zone_id,
            channel_id=self.control_channel.id
        )

    def has_available_voice_channel(self) -> bool:
        total_voice_channels = len([c for c in self.channels.values() if not c.control and c.enabled])
        return len(self.assigned_voice_channels) < total_voice_channels

    def find_and_assign_voice_channel(self, call: 'RadioCall', required_mode: CallMode) -> Optional[VoiceChannel]:
        """
        Finds and allocates a voice channel based on required mode and site's assignment strategy.
        Implements TDMA slot prioritization and preemption placeholder.
        Returns the allocated VoiceChannel object or None if no channel is available.
        """
        # --- 1. Identify all possible voice channels based on capabilities ---
        possible_channels = []
        for ch in self.channels.values():
            if not ch.enabled or ch.control:
                continue
            if required_mode == CallMode.FDMA and ch.fdma:
                possible_channels.append(ch)
            elif required_mode == CallMode.TDMA and ch.tdma:
                possible_channels.append(ch)
            elif required_mode == CallMode.MIXED and (ch.fdma or ch.tdma):
                possible_channels.append(ch)

        if not possible_channels:
            print(f"  -> Site {self.id}: No channels capable of handling a {required_mode.name} call.")
            return None

        # --- 2. TDMA-Specific Logic: Prioritize finding a free slot on an active channel ---
        if required_mode == CallMode.TDMA:
            for vc, active_call in self.assigned_voice_channels.items():
                # Check if this channel is already in use for a TDMA call
                if active_call.mode == CallMode.TDMA:
                    # Is slot 1 busy? If not, check if slot 2 is free.
                    slot1_vc = VoiceChannel(channel_id=vc.channel_id, tdma_slot=1)
                    slot2_vc = VoiceChannel(channel_id=vc.channel_id, tdma_slot=2)

                    if slot1_vc not in self.assigned_voice_channels:
                        self.assigned_voice_channels[slot1_vc] = call
                        print(f"  -> Site {self.id}: Assigned existing Channel {slot1_vc.channel_id} (TDMA Slot 1).")
                        return slot1_vc
                    if slot2_vc not in self.assigned_voice_channels:
                        self.assigned_voice_channels[slot2_vc] = call
                        print(f"  -> Site {self.id}: Assigned existing Channel {slot2_vc.channel_id} (TDMA Slot 2).")
                        return slot2_vc

        # --- 3. Find a completely idle channel frequency ---
        idle_channels = []
        for ch in possible_channels:
            vc_fdma = VoiceChannel(channel_id=ch.id)
            vc_tdma1 = VoiceChannel(channel_id=ch.id, tdma_slot=1)
            # A channel is idle if it's not in the assigned list at all
            if vc_fdma not in self.assigned_voice_channels and vc_tdma1 not in self.assigned_voice_channels:
                idle_channels.append(ch)

        # --- 4. Apply Assignment Strategy if idle channels are found ---
        if idle_channels:
            selected_channel = None
            # Sort by channel ID to ensure predictable behavior for rotating and balanced modes
            idle_channels.sort(key=lambda c: c.id)

            if self.assignment_mode == "rotating":
                selected_channel = idle_channels[0]
            elif self.assignment_mode == "random":
                selected_channel = random.choice(idle_channels)
            elif self.assignment_mode == "balanced":
                mid_point = len(idle_channels) // 2
                selected_channel = idle_channels[mid_point]
            else:  # Default to rotating
                selected_channel = idle_channels[0]

            # --- 5. Allocate the selected channel ---
            if required_mode == CallMode.TDMA:
                new_vc = VoiceChannel(channel_id=selected_channel.id, tdma_slot=1)
                self.assigned_voice_channels[new_vc] = call
                print(
                    f"  -> Site {self.id}: Assigned new Channel {new_vc.channel_id} (TDMA Slot 1) via '{self.assignment_mode}' strategy.")
                return new_vc
            else:  # FDMA or Mixed (downgraded)
                new_vc = VoiceChannel(channel_id=selected_channel.id)
                self.assigned_voice_channels[new_vc] = call
                print(
                    f"  -> Site {self.id}: Assigned new Channel {new_vc.channel_id} (FDMA) via '{self.assignment_mode}' strategy.")
                return new_vc

        # --- 6. (Placeholder) Preemption Logic ---
        # If we are here, it means no idle channels were found.
        # This is where we would check for a channel with a lower-priority call (e.g., data)
        # and preempt it. For now, we will just fail.
        print(f"  -> Site {self.id}: All capable voice channels are busy. No channel assigned.")
        return None

    def release_voice_channel(self, voice_channel_to_release: VoiceChannel):
        """Releases the specified voice channel, making it available again."""
        if voice_channel_to_release in self.assigned_voice_channels:
            del self.assigned_voice_channels[voice_channel_to_release]
            print(
                f"  -> Site {self.id}: Released Channel {voice_channel_to_release.channel_id} (Slot: {voice_channel_to_release.tdma_slot or 'FDMA'}).")
        else:
            print(f"  -> Site {self.id}: WARNING - Tried to release a channel that was not assigned.")


# --- Logical Resource Models (Units, TGs) ---
@dataclass
class Talkgroup:
    """Represents a talkgroup with its own priority level."""
    id: int
    alias: str
    hangtime: int
    ptt_id: bool
    all_start: bool = False
    mode: CallMode = CallMode.MIXED
    priority: Union[str, EventPriority] = EventPriority.NORMAL
    valid_sites: Optional[List[int]] = None

    def __post_init__(self):
        """Converts priority and mode from strings (from YAML) to their Enum types."""
        if isinstance(self.priority, str):
            try:
                self.priority = EventPriority[self.priority.upper()]
            except KeyError:
                print(f"Warning: Invalid priority '{self.priority}' for TG {self.id}. Defaulting to NORMAL.")
                self.priority = EventPriority.NORMAL

        if isinstance(self.mode, str):
            try:
                self.mode = CallMode[self.mode.upper()]
            except KeyError:
                print(f"Warning: Invalid mode '{self.mode}' for TG {self.id}. Defaulting to MIXED.")
                self.mode = CallMode.MIXED


@dataclass
class Unit:
    """Represents a radio subscriber unit with its own state machine."""
    id: int
    alias: str
    tdma_capable: bool
    state: UnitState = UnitState.POWERED_OFF
    location: Optional[Coordinates] = None
    current_site: Optional[Site] = None
    visible_sites: List[Tuple[Site, int]] = field(default_factory=list)
    selected_talkgroup: Optional[Talkgroup] = None
    affiliated_talkgroup: Optional[Talkgroup] = None
    groups: List['Group'] = field(default_factory=list)
    banned_sites: Set[Tuple[int, int]] = field(default_factory=set)  # CHANGED: Now stores (zone_id, site_id)
    banned_talkgroups: Set[int] = field(default_factory=set)
    affiliation_attempts: Dict[int, int] = field(default_factory=dict)
    current_call: Optional['RadioCall'] = None

    def power_on(self) -> None:
        """Initiates the power-on sequence."""
        if self.state == UnitState.POWERED_OFF:
            self.state = UnitState.SEARCHING_FOR_SITE
            # Reset transient states upon power on
            self.banned_sites.clear()
            self.banned_talkgroups.clear()
            self.affiliation_attempts.clear()
            self.current_site = None
            self.affiliated_talkgroup = None
            print(f"  -> Unit {self.id} ({self.alias}): Powered ON. State: {self.state.value}.")

    def handle_registration_response(self, response: UnitRegistrationResponse) -> Optional[GroupAffiliationRequest]:
        """
        Handles the system's response to a registration request based on P25 logic.
        Returns the next ISP to be sent, if any.
        """
        if response.status == RegistrationStatus.REG_ACCEPT:
            self.state = UnitState.IDLE_REGISTERED
            print(
                f"  -> Unit {self.id} ({self.alias}): REG_ACCEPT. Registration successful on Site {response.site_id} (Zone {response.zone_id}). State: {self.state.value}.")
            if self.selected_talkgroup:
                print(
                    f"  -> Unit {self.id} ({self.alias}): Automatically affiliating to selected TG {self.selected_talkgroup.id}.")
                return self.affiliate_to_talkgroup(self.selected_talkgroup)

        else:  # Any other status is a failure of some kind
            self.state = UnitState.SEARCHING_FOR_SITE
            ban_tuple = (response.zone_id, response.site_id)
            self.banned_sites.add(ban_tuple)

            if response.status == RegistrationStatus.REG_DENY:
                print(
                    f"  -> Unit {self.id} ({self.alias}): REG_DENY on Site {response.site_id} (Zone {response.zone_id}). Banning site and re-scanning.")
            elif response.status == RegistrationStatus.REG_REFUSED:
                self.state = UnitState.FAILED  # This is a terminal failure
                print(f"  -> Unit {self.id} ({self.alias}): REG_REFUSED. Unit not authorized. State: FAILED.")
            else:  # REG_FAIL or FAILED_SYSTEM_FULL
                print(
                    f"  -> Unit {self.id} ({self.alias}): Registration FAILED on Site {response.site_id} (Zone {response.zone_id}) ({response.status.value}). Re-scanning.")

        return None

    def affiliate_to_talkgroup(self, talkgroup: Talkgroup) -> Optional[GroupAffiliationRequest]:
        """Checks bans and attempts, then sends an affiliation request."""
        if talkgroup.id in self.banned_talkgroups:
            print(f"  -> Unit {self.id} ({self.alias}): TG {talkgroup.id} is permanently banned. Cannot affiliate.")
            self.state = UnitState.IDLE_REGISTERED  # Go back to idle
            return None

        if self.affiliation_attempts.get(talkgroup.id, 0) >= MAX_AFFILIATION_ATTEMPTS:
            print(
                f"  -> Unit {self.id} ({self.alias}): Max affiliation attempts reached for TG {talkgroup.id}. Stopping.")
            self.state = UnitState.IDLE_REGISTERED
            return None

        self.state = UnitState.AFFILIATING
        print(
            f"  -> Unit {self.id} ({self.alias}): State: {self.state.value}. Sending GRP_AFF_REQ for TG {talkgroup.id}.")
        return GroupAffiliationRequest(unit_id=self.id, talkgroup_id=talkgroup.id)

    def handle_affiliation_response(self, response: GroupAffiliationResponse):
        """Handles the detailed affiliation response from the system."""
        tg_id = response.talkgroup_id

        if response.status == AffiliationStatus.ACCEPTED:
            self.state = UnitState.IDLE_AFFILIATED
            self.affiliated_talkgroup = self.selected_talkgroup
            self.affiliation_attempts.pop(tg_id, None)  # Clear attempts on success
            print(
                f"  -> Unit {self.id} ({self.alias}): AFF_ACCEPT. Affiliation to TG {tg_id} successful. State: {self.state.value}.")

        elif response.status == AffiliationStatus.DENIED:
            self.state = UnitState.SEARCHING_FOR_SITE  # Per standard, hunt for a new site
            if self.current_site:
                ban_tuple = (response.zone_id, self.current_site.id)
                self.banned_sites.add(ban_tuple)
            print(
                f"  -> Unit {self.id} ({self.alias}): AFF_DENY. Not authorized for TG {tg_id} on this site. Banning site and hunting for new site...")

        elif response.status == AffiliationStatus.FAILED:
            self.affiliation_attempts[tg_id] = self.affiliation_attempts.get(tg_id, 0) + 1
            self.state = UnitState.IDLE_REGISTERED  # Go back to idle before retry
            print(
                f"  -> Unit {self.id} ({self.alias}): AFF_FAIL. Affiliation failed for TG {tg_id}. Attempt {self.affiliation_attempts[tg_id]}/{MAX_AFFILIATION_ATTEMPTS}.")

        elif response.status == AffiliationStatus.REFUSED:
            self.banned_talkgroups.add(tg_id)
            self.state = UnitState.IDLE_REGISTERED
            print(f"  -> Unit {self.id} ({self.alias}): AFF_REFUSED. TG {tg_id} is invalid. Permanently banned.")

    def handle_voice_channel_grant(self, grant: GroupVoiceChannelGrant):
        """Handles receiving the final grant to join a voice call."""
        # --- THIS LOGIC IS NOW EXPANDED ---
        is_initiator = self.state == UnitState.CALL_REQUESTED
        is_listener = self.state == UnitState.IDLE_AFFILIATED

        if is_initiator or is_listener:
            self.state = UnitState.IN_CALL
            self.current_call = self.radio_system.get_zone(self.current_site.zone_id).active_calls.get(
                grant.call_id)  # <-- Needs a way to find the call

            role = "Initiator" if is_initiator else "Listener"
            print(
                f"  -> Unit {self.id} ({self.alias}) [{role}]: Grant received for TG {grant.talkgroup_id}. Moving to Ch {grant.channel_id} (Slot: {grant.tdma_slot or 'N/A'}). State: {self.state.value}.")
        else:
            pass  # Unit is in a state where it can't accept a call (e.g., already in another call)

@dataclass
class Console(Unit):
    affiliated_talkgroups: List[Talkgroup] = field(default_factory=list)
    can_patch_talkgroups: bool = True
    can_inhibit_units: bool = True
    tdma_capable: bool = True

    def __post_init__(self):
        self.tdma_capable = True
        print(f"Console {self.id} ({self.alias}): Initialized with special permissions.")


@dataclass
class Group:
    """A generic group for organizing units, talkgroups, or consoles."""
    id: int
    alias: str
    members: List[Union[Unit, Talkgroup, Console]] = field(default_factory=list)
    priority: EventPriority = EventPriority.DEFAULT
    area: Optional[OperationalArea] = None


@dataclass
class RadioCall:
    id: int
    initiating_unit: Unit
    talkgroup: Talkgroup
    assigned_channels_by_site: Dict[int, VoiceChannel] = field(default_factory=dict)
    status: CallStatus = CallStatus.IDLE
    mode: CallMode = CallMode.TDMA

    def start(self):
        self.status = CallStatus.ACTIVE
        print(f"Call {self.id} on TG {self.talkgroup.alias}: ACTIVE.")

    def end(self):
        self.status = CallStatus.ENDED
        print(f"Call {self.id} on TG {self.talkgroup.alias}: ENDED.")


# --- High-Level Hierarchical Containers ---
@dataclass
class RFSS:
    id: int
    alias: str
    area: OperationalArea
    sites: Dict[int, Site]
    talkgroups: Dict[int, Talkgroup]
    units: Dict[int, Unit]
    consoles: Dict[int, Console]
    groups: Dict[int, 'Group'] = field(default_factory=dict)


@dataclass
class WACN:
    id: int
    zones: Dict[int, RFSS]
    area: Optional[OperationalArea] = None


@dataclass
class SystemConfig:
    wacn: WACN
