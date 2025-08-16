from dataclasses import dataclass
from enum import IntEnum


class EventPriority(IntEnum):
    """Defines the priority of an event. Lower numbers are higher priority."""
    SYSTEM = 0
    EMERGENCY = 1
    PREEMPT = 2  # New priority level for Console preemption
    HIGH = 3
    NORMAL = 5
    DEFAULT = 7  # New default priority for Groups
    LOW = 10


@dataclass
class P25Packet:
    """Base class for all P25 signaling packets. Acts as a marker."""
    pass


@dataclass
class InboundSignalingPacket(P25Packet):
    """
    Base class for all packets sent FROM a Subscriber Unit (SU)
    or Console TO the RF Subsystem (RFSS).
    """
    # Non-default arguments must come first.
    unit_id: int


@dataclass
class OutboundSignalingPacket(P25Packet):
    """
    Base class for all packets sent FROM the RF Subsystem (RFSS)
    TO a Subscriber Unit (SU) or Console.
    """
    pass