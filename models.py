from dataclasses import dataclass, field
from typing import Dict, List, Union, Optional, Tuple
from enum import Enum

# --- Import EventPriority from our p25 packets ---
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


# --- Enums for State Machines ---

class UnitState(Enum):
    """Represents the operational state of a Unit."""
    POWERED_OFF = "Powered Off"
    SEARCHING_FOR_SITE = "Searching for Site"
    REGISTERING = "Registering"
    IDLE_REGISTERED = "Idle (Registered)"
    AFFILIATING = "Affiliating"
    IDLE_AFFILIATED = "Idle (Affiliated)"
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
class Site:
    id: int
    alias: str
    assignment_mode: str
    channels: Dict[int, Channel] = field(default_factory=dict)
    subsites: List[Subsite] = field(default_factory=list)
    status: SiteStatus = SiteStatus.OFFLINE
    control_channel: Channel = None
    registrations: List[Union['Unit', 'Console']] = field(default_factory=list)
    assigned_voice_channels: Dict[int, 'RadioCall'] = field(default_factory=dict)

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


# --- Logical Resource Models (Units, TGs) ---
@dataclass
class Talkgroup:
    """Represents a talkgroup with its own priority level."""
    id: int
    alias: str
    hangtime: int
    ptt_id: bool
    mode: CallMode = CallMode.MIXED
    # --- FIX: Re-add the priority field ---
    priority: Union[str, EventPriority] = EventPriority.NORMAL

    def __post_init__(self):
        """Converts priority from string (from YAML) to the Enum type."""
        if isinstance(self.priority, str):
            try:
                self.priority = EventPriority[self.priority.upper()]
            except KeyError:
                print(f"Warning: Invalid priority '{self.priority}' for TG {self.id}. Defaulting to NORMAL.")
                self.priority = EventPriority.NORMAL


@dataclass
class Unit:
    """Represents a radio subscriber unit with its own state machine."""
    id: int
    alias: str
    tdma_capable: bool
    state: UnitState = UnitState.POWERED_OFF
    location: Optional[Coordinates] = None #
    current_site: Optional[Site] = None
    visible_sites: List[Tuple[Site, int]] = field(default_factory=list)
    selected_talkgroup: Optional[Talkgroup] = None
    affiliated_talkgroup: Optional[Talkgroup] = None
    groups: List['Group'] = field(default_factory=list)

    def power_on(self) -> None:
        """Initiates the power-on sequence.

        This method now only sets the initial state. The subsequent actions
        (finding a site, registering) will be driven by events.
        """
        if self.state == UnitState.POWERED_OFF:
            self.state = UnitState.SEARCHING_FOR_SITE
            print(f"  -> Unit {self.id} ({self.alias}): Powered ON. State: {self.state.value}.")
            # The ZoneController will now be responsible for simulating the
            # site search and then triggering the registration.

    def handle_registration_response(self, response: UnitRegistrationResponse) -> Optional[GroupAffiliationRequest]:
        if response.status == RegistrationStatus.GRANTED:
            self.state = UnitState.IDLE_REGISTERED
            print(f"  -> Unit {self.id} ({self.alias}): Registration successful. State: {self.state.value}.")
            if self.selected_talkgroup:
                return self.affiliate_to_talkgroup(self.selected_talkgroup.id)
        else:
            self.state = UnitState.FAILED
            print(f"  -> Unit {self.id} ({self.alias}): Registration FAILED ({response.status.value}). State: {self.state.value}.")
        return None

    def affiliate_to_talkgroup(self, talkgroup_id: int) -> GroupAffiliationRequest:
        self.state = UnitState.AFFILIATING
        print(f"  -> Unit {self.id} ({self.alias}): State: {self.state.value}. Sending GRP_AFF_REQ for TG {talkgroup_id}.")
        return GroupAffiliationRequest(unit_id=self.id, talkgroup_id=talkgroup_id)

    def handle_affiliation_response(self, response: GroupAffiliationResponse):
        if response.status == AffiliationStatus.GRANTED:
            self.state = UnitState.IDLE_AFFILIATED
            print(f"  -> Unit {self.id} ({self.alias}): Affiliation to TG {response.talkgroup_id} successful. State: {self.state.value}.")
        else:
            self.state = UnitState.IDLE_REGISTERED
            print(f"  -> Unit {self.id} ({self.alias}): Affiliation FAILED ({response.status.value}). State: {self.state.value}.")


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
    involved_sites: List[Site]
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
