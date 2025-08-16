from dataclasses import dataclass
from .packets import InboundSignalingPacket, OutboundSignalingPacket, EventPriority

# --- Data Service ISPs (Unit -> System) ---

@dataclass
class SndcpDataChannelRequest(InboundSignalingPacket):
    """P25 SN-DATA_CHN_REQ"""
    pass


@dataclass
class SndcpDataPageResponse(InboundSignalingPacket):
    """P25 SN-DATA_PAGE_RES"""
    pass


@dataclass
class SndcpReconnectRequest(InboundSignalingPacket):
    """P25 SN-REC_REQ"""
    pass


# --- Data Service OSPs (System -> Unit) ---

@dataclass
class SndcpDataChannelGrant(OutboundSignalingPacket):
    """P25 SN-DATA_CHN_GNT"""
    pass


@dataclass
class SndcpDataPageRequest(OutboundSignalingPacket):
    """P25 SN-DATA_PAGE_REQ"""
    pass


@dataclass
class SndcpDataChannelAnnouncementExplicit(OutboundSignalingPacket):
    """P25 SN-DATA_CHN_ANN_EXP"""
    pass