from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any



class EventPriority(IntEnum):
    """Defines the priority of an event. Lower numbers are higher priority."""
    SYSTEM = 0
    EMERGENCY = 1
    HIGH = 3
    NORMAL = 5
    LOW = 10


@dataclass
class Event:
    """Base class for all events."""
    pass


# --- Unit Events ---
@dataclass
class ControlChannelCallRequest(Event):
    """Event to establish the long-running control channel call for a site."""
    site_id: int
    zone_id: int
    channel_id: int
    priority: EventPriority = EventPriority.SYSTEM


@dataclass
class UnitPowerOnRequest(Event):
    """Event fired when a user requests to power on a unit."""
    unit_id: int
    priority: EventPriority = EventPriority.SYSTEM


@dataclass
class UnitRegistrationRequest(Event):
    """
    Event fired by a Unit when it needs to register on a site.
    This is the new equivalent of 'U_REG_REQ'.
    """
    unit_id: int
    priority: EventPriority = EventPriority.NORMAL


@dataclass
class UnitRegisteredEvent(Event):
    """Event fired by the ZoneController after a unit has successfully registered."""
    unit_id: int
    site_id: int
    priority: EventPriority = EventPriority.SYSTEM


# --- Call Events ---
@dataclass
class CallRequestEvent(Event):
    """Event fired when a unit requests to make a call."""
    unit_id: int
    talkgroup_id: int
    priority: EventPriority = EventPriority.NORMAL  # This could be dynamic based on the talkgroup
