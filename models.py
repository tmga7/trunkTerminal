# models.py (Revised for Hierarchy)

from dataclasses import dataclass, field
from typing import Dict, List, Union
from enum import Enum


# --- Enums (No Change) ---

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
    """Represents a physical tower. A Site must have at least one."""
    id: int
    alias: str
    location: Coordinates


@dataclass
class Channel:
    id: int
    freq_tx: float
    freq_rx: float
    enabled: bool
    fdma: bool
    tdma: bool
    control: bool = False
    voice: bool = False


@dataclass
class Site:
    """Represents an RF site, which is a collection of subsites and channels."""
    id: int
    alias: str
    assignment_mode: str
    channels: Dict[int, Channel] = field(default_factory=dict)
    subsites: List[Subsite] = field(default_factory=list)

    status: SiteStatus = SiteStatus.OFFLINE
    control_channel: Channel = None
    registrations: List[Union['Unit', 'Console']] = field(default_factory=list)

    def __post_init__(self):
        if not self.subsites:
            raise ValueError(f"Site {self.id} ({self.alias}) must be initialized with at least one subsite.")


# --- Logical Resource Models (Units, TGs) ---
@dataclass
class Talkgroup:
    id: int
    alias: str
    hangtime: int
    ptt_id: bool
    mode: CallMode = CallMode.MIXED


@dataclass
class Unit:
    id: int
    alias: str
    tdma_capable: bool
    powered_on: bool = False
    current_site: Site = None
    affiliated_talkgroup: Talkgroup = None

    def power_on(self):
        """Sets the unit's power status to ON."""
        if not self.powered_on:
            self.powered_on = True
            # The message is generic to work for both Units and Consoles
            print(f"  -> {type(self).__name__} {self.id} ({self.alias}): Powered ON.")




@dataclass
class Console(Unit):
    """A Console is a special type of Unit with extra capabilities."""
    # A list of Talkgroup objects this console is permitted to use.
    affiliated_talkgroups: List[Talkgroup] = field(default_factory=list)
    can_patch_talkgroups: bool = True
    can_inhibit_units: bool = True
    tdma_capable: bool = True


    def __post_init__(self):
        # Consoles are typically not TDMA-dependent in the same way radios are.
        self.tdma_capable = True
        print(f"Console {self.id} ({self.alias}): Initialized with special permissions.")


@dataclass
class Group:
    """A generic group for organizing units, talkgroups, or consoles."""
    id: int
    alias: str
    # A group can contain a mix of different object types.
    members: List[Union[Unit, Talkgroup, Console]] = field(default_factory=list)


@dataclass
class RadioCall:
    """Represents an active radio call on the system. (The new site_call.py)"""
    id: int
    initiating_unit: Unit
    talkgroup: Talkgroup
    involved_sites: List[Site]
    status: CallStatus = CallStatus.IDLE
    mode: CallMode = CallMode.TDMA  # Default, can be changed by CallManager

    def start(self):
        self.status = CallStatus.ACTIVE
        print(f"Call {self.id} on TG {self.talkgroup.alias}: ACTIVE.")

    def end(self):
        self.status = CallStatus.ENDED
        print(f"Call {self.id} on TG {self.talkgroup.alias}: ENDED.")


# --- High-Level Hierarchical Containers ---
@dataclass
class RFSS:  # A Zone Controller
    """Represents a single zone (RFSS) with its own System ID."""
    id: int  # This is the System ID
    alias: str
    area: OperationalArea
    sites: Dict[int, Site]
    talkgroups: Dict[int, Talkgroup]
    units: Dict[int, Unit]
    consoles: Dict[int, Console]


@dataclass
class WACN:
    """Represents the top-level network identifier."""
    id: int  # The WACN ID
    zones: Dict[int, RFSS]  # Contains all zones (RFSS) under this WACN


# The SystemConfig now just points to the top-level WACN object.
@dataclass
class SystemConfig:
    wacn: WACN
