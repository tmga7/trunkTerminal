# events.py
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Event:
    """Base class for all events."""
    pass

# --- Unit Events ---
@dataclass
class UnitPowerOnRequest(Event):
    """Event fired when a user requests to power on a unit."""
    unit_id: int

@dataclass
class UnitRegistrationRequest(Event):
    """
    Event fired by a Unit when it needs to register on a site.
    This is the new equivalent of 'U_REG_REQ'.
    """
    unit_id: int

@dataclass
class UnitRegisteredEvent(Event):
    """Event fired by the ZoneController after a unit has successfully registered."""
    unit_id: int
    site_id: int

# We can add more events like CallRequestEvent, etc., later.