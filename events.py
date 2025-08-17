from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any
from p25.packets import EventPriority

# The EventPriority enum is still useful for the simulation's internal queue,
# so we can import it from our new p25.packets module.


@dataclass
class Event:
    """Base class for all events and commands in the simulation."""
    pass


# --- Simulation-Level Commands ---
# These events are used by the scenario loader or CLI to command entities
# within the simulation to begin a process. They are not P25 packets themselves.

@dataclass
class UnitUpdateLocationCommand(Event):
    """High-level command to change a unit's physical location."""
    unit_id: int
    new_location: 'Coordinates' # Use forward reference for Coordinates
    priority: EventPriority = EventPriority.NORMAL

@dataclass
class UnitScanForSitesCommand(Event):
    """
    High-level command to instruct a Unit to scan for the best available site
    based on its current location.
    """
    unit_id: int
    priority: EventPriority = EventPriority.NORMAL

@dataclass
class UnitPowerOnCommand(Event):
    """
    High-level command to instruct a Unit to begin its power-on sequence,
    which will involve finding a site and then sending a UnitRegistrationRequest packet.
    """
    unit_id: int
    priority: EventPriority = EventPriority.SYSTEM


@dataclass
class UnitInitiateCallCommand(Event):
    """
    High-level command for a unit to initiate a group call. This will cause
    the unit's internal logic to generate a GroupVoiceServiceRequest packet.
    """
    unit_id: int
    talkgroup_id: int
    priority: EventPriority = EventPriority.HIGH


# --- Internal System Events ---
# These events are used by components within the simulation to communicate
# with each other at a high level.

@dataclass
class ControlChannelEstablishRequest(Event):
    """
    Internal event used by a Site to request the ZoneController to formally
    establish its control channel after a successful initialization.
    """
    site_id: int
    zone_id: int
    channel_id: int
    priority: EventPriority = EventPriority.SYSTEM

@dataclass
class UnitUnbanFromSiteCommand(Event):
    """
    Internal command to remove a site from a unit's temporary ban list
    after a failed registration attempt.
    """
    unit_id: int
    site_id: int
    priority: EventPriority = EventPriority.LOW

@dataclass
class UnitEndTransmissionCommand(Event):
    """
    High-level command for a unit to unkey and end its transmission.
    This will trigger either the hangtime timer or an immediate teardown.
    """
    unit_id: int
    call_id: int
    priority: EventPriority = EventPriority.HIGH

@dataclass
class CallTeardownCommand(Event):
    """
    Internal command to release all radio resources associated with a call
    after the hangtime has expired or if no hangtime is used.
    """
    call_id: int
    priority: EventPriority = EventPriority.NORMAL

@dataclass
class ConsoleInitiateCallCommand(Event):
    """
    High-level command for a console to initiate or preempt a group call.
    """
    console_id: int
    talkgroup_id: int
    priority: EventPriority = EventPriority.PREEMPT # Hardcoded to the highest priority
