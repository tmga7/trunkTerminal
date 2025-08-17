from dataclasses import dataclass
from .packets import InboundSignalingPacket, OutboundSignalingPacket, EventPriority
from typing import Optional


# --- Voice Service ISPs (Unit -> System) ---

@dataclass
class GroupVoiceServiceRequest(InboundSignalingPacket):
    """P25 GRP_V_REQ"""
    talkgroup_id: int
    # Setting a higher default priority for voice requests
    priority: EventPriority = EventPriority.HIGH



@dataclass
class UnitToUnitVoiceServiceRequest(InboundSignalingPacket):
    """P25 UU_V_REQ"""
    target_unit_id: int
    priority: EventPriority = EventPriority.HIGH


@dataclass
class UnitToUnitVoiceServiceAnswerResponse(InboundSignalingPacket):
    """P25 UU_ANS_RSP"""
    pass


@dataclass
class TelephoneInterconnectRequestExplicit(InboundSignalingPacket):
    """P25 TELE_INT_DIAL_REQ"""
    phone_number: str
    priority: EventPriority = EventPriority.NORMAL


@dataclass
class TelephoneInterconnectRequestImplicit(InboundSignalingPacket):
    """P25 TELE_INT_PSTN_REQ"""
    priority: EventPriority = EventPriority.NORMAL


@dataclass
class TelephoneInterconnectAnswerResponse(InboundSignalingPacket):
    """P25 TELE_INT_ANS_RSP"""
    pass


# --- Voice Service OSPs (System -> Unit) ---

@dataclass
class GroupVoiceChannelGrant(OutboundSignalingPacket):
    """P25 GRP_V_CH_GRANT"""
    unit_id: int
    talkgroup_id: int
    call_id: int
    channel_id: int             # <-- ADD THIS
    tdma_slot: Optional[int]    # <-- ADD THIS
    priority: EventPriority = EventPriority.HIGH


@dataclass
class GroupVoiceChannelGrantUpdate(OutboundSignalingPacket):
    """P25 GRP_V_CH_GRANT_UPDT"""
    pass


@dataclass
class GroupVoiceChannelUpdateExplicit(OutboundSignalingPacket):
    """P25 GRP_V_CH_GRANT_UPDT_EXP"""
    pass


@dataclass
class UnitToUnitAnswerRequest(OutboundSignalingPacket):
    """P25 UU_ANS_REQ"""
    pass


@dataclass
class UnitToUnitVoiceServiceChannelGrant(OutboundSignalingPacket):
    """P25 UU_V_CH_GRANT"""
    pass


@dataclass
class TelephoneInterconnectVoiceChannelGrant(OutboundSignalingPacket):
    """P25 TELE_INT_CH_GRANT"""
    pass


@dataclass
class TelephoneInterconnectAnswerRequest(OutboundSignalingPacket):
    """P25 TELE_INT_ANS_REQ"""
    pass


@dataclass
class UnitToUnitVoiceChannelGrantUpdate(OutboundSignalingPacket):
    """P25 UU_V_CH_GRANT_UPDT"""
    pass


@dataclass
class TelephoneInterconnectChannelGrantUpdate(OutboundSignalingPacket):
    """P25 TELE_INT_CH_GRANT_UPDT"""
    pass