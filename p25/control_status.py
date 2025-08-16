from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from .packets import InboundSignalingPacket, OutboundSignalingPacket, EventPriority



# --- Control & Status ISPs (Unit -> System) ---

@dataclass
class AcknowledgeResponseUnit(InboundSignalingPacket):
    """P25 ACK_RSP_U"""
    pass


@dataclass
class AuthenticationQuery(InboundSignalingPacket):
    """P25 AUTH_Q"""
    pass


@dataclass
class AuthenticationResponse(InboundSignalingPacket):
    """P25 AUTH_RSP"""
    pass


@dataclass
class CallAlertRequest(InboundSignalingPacket):
    """P25 CALL_ALRT_REQ"""
    pass


@dataclass
class CancelServiceRequest(InboundSignalingPacket):
    """P25 CAN_SRV_REQ"""
    pass


@dataclass
class EmergencyAlarmRequest(InboundSignalingPacket):
    """P25 EMRG_ALRM_REQ"""
    pass


@dataclass
class ExtendedFunctionResponse(InboundSignalingPacket):
    """P25 EXT_FNCT_RSP"""
    pass


@dataclass
class GroupAffiliationQueryResponse(InboundSignalingPacket):
    """P25 GRP_AFF_Q_RSP"""
    pass


@dataclass
class GroupAffiliationRequest(InboundSignalingPacket):
    """P25 GRP_AFF_REQ: Sent by a unit to affiliate with a talkgroup."""
    talkgroup_id: int
    priority: EventPriority = EventPriority.NORMAL



@dataclass
class IdentifierUpdateRequest(InboundSignalingPacket):
    """P25 IDEN_UP_REQ"""
    pass


@dataclass
class MessageUpdateRequest(InboundSignalingPacket):
    """P25 MSG_UPDT_REQ"""
    pass


@dataclass
class ProtectionParameterRequest(InboundSignalingPacket):
    """P25 P_PARM_REQ"""
    pass


@dataclass
class StatusQueryRequest(InboundSignalingPacket):
    """P25 STS_Q_REQ"""
    pass


@dataclass
class StatusQueryResponse(InboundSignalingPacket):
    """P25 STS_Q_RSP"""
    pass


@dataclass
class StatusUpdateRequest(InboundSignalingPacket):
    """P25 STS_UPDT_REQ"""
    pass


@dataclass
class UnitRegistrationRequest(InboundSignalingPacket):
    """P25 U_REG_REQ: Sent by a unit to register on a site."""
    priority: EventPriority = EventPriority.NORMAL


@dataclass
class UnitDeregistrationRequest(InboundSignalingPacket):
    """P25 U_DE_REG_REQ"""
    pass


@dataclass
class LocationRegistrationRequest(InboundSignalingPacket):
    """P25 LOC_REG_REQ"""
    pass


@dataclass
class RadioUnitMonitorRequest(InboundSignalingPacket):
    """P25 RAD_MON_REQ"""
    pass


@dataclass
class RoamingAddressRequest(InboundSignalingPacket):
    """P25 ROAM_ADDR_REQ"""
    pass


@dataclass
class RoamingAddressResponse(InboundSignalingPacket):
    """P25 ROAM_ADDR_RSP"""
    pass


# --- Control & Status OSPs (System -> Unit) ---

class RegistrationStatus(Enum):
    """Possible outcomes for a registration request."""
    GRANTED = "Granted"
    FAILED_UNKNOWN_UNIT = "Failed: Unknown Unit"
    FAILED_SYSTEM_FULL = "Failed: System Full"


class AffiliationStatus(Enum):
    """Possible outcomes for an affiliation request."""
    GRANTED = "Granted"
    FAILED_UNKNOWN_GROUP = "Failed: Unknown Group"
    FAILED_NOT_AUTHORIZED = "Failed: Not Authorized"


@dataclass
class AcknowledgeResponseFne(OutboundSignalingPacket):
    """P25 ACK_RSP_FNE"""
    pass


@dataclass
class AdjacentStatusBroadcast(OutboundSignalingPacket):
    """P25 ADJ_STS_BCST"""
    pass


@dataclass
class AuthenticationCommand(OutboundSignalingPacket):
    """P25 AUTH_CMD"""
    pass


@dataclass
class CallAlert(OutboundSignalingPacket):
    """P25 CALL_ALRT"""
    pass


@dataclass
class DenyResponse(OutboundSignalingPacket):
    """P25 DENY_RSP"""
    pass


@dataclass
class ExtendedFunctionCommand(OutboundSignalingPacket):
    """P25 EXT_FNCT_CMD"""
    pass


@dataclass
class GroupAffiliationQuery(OutboundSignalingPacket):
    """P25 GRP_AFF_Q"""
    pass


@dataclass
class GroupAffiliationResponse(OutboundSignalingPacket):
    """P25 GRP_AFF_RSP: Sent by the system in response to an affiliation request."""
    status: AffiliationStatus
    unit_id: int
    talkgroup_id: int


@dataclass
class IdentifierUpdate(OutboundSignalingPacket):
    """P25 IDEN_UP"""
    pass


@dataclass
class MessageUpdate(OutboundSignalingPacket):
    """P25 MSG_UPDT"""
    pass


@dataclass
class NetworkStatusBroadcast(OutboundSignalingPacket):
    """P25 NET_STS_BCST"""
    pass


@dataclass
class ProtectionParameterBroadcast(OutboundSignalingPacket):
    """P25 P_PARM_BCST"""
    pass


@dataclass
class ProtectionParameterUpdate(OutboundSignalingPacket):
    """P25 P_PARM_UPDT"""
    pass


@dataclass
class QueuedResponse(OutboundSignalingPacket):
    """P25 QUE_RSP"""
    pass


@dataclass
class RfssStatusBroadcast(OutboundSignalingPacket):
    """P25 RFSS_STS_BCST"""
    pass


@dataclass
class SecondaryControlChannelBroadcast(OutboundSignalingPacket):
    """P25 SCCB"""
    pass


@dataclass
class StatusQuery(OutboundSignalingPacket):
    """P25 STS_Q"""
    pass


@dataclass
class StatusUpdate(OutboundSignalingPacket):
    """P25 STS_UPDT"""
    pass


@dataclass
class SystemServiceBroadcast(OutboundSignalingPacket):
    """P25 SYS_SRV_BCST"""
    pass


@dataclass
class UnitRegistrationCommand(OutboundSignalingPacket):
    """P25 U_REG_CMD"""
    pass


@dataclass
class UnitRegistrationResponse(OutboundSignalingPacket):
    """P25 U_REG_RSP: Sent by the system in response to a registration request."""
    status: RegistrationStatus
    unit_id: int
    site_id: int


@dataclass
class UnitDeregistrationAcknowledge(OutboundSignalingPacket):
    """P25 U_DE_REG_ACK"""
    pass


@dataclass
class LocationRegistrationResponse(OutboundSignalingPacket):
    """P25 LOC_REG_RSP"""
    pass


@dataclass
class RadioUnitMonitorCommand(OutboundSignalingPacket):
    """P25 RAD_MON_CMD"""
    pass


@dataclass
class RoamingAddressCommand(OutboundSignalingPacket):
    """P25 ROAM_ADDR_CMD"""
    pass


@dataclass
class RoamingAddressUpdate(OutboundSignalingPacket):
    """P25 ROAM_ADDR_UPDT"""
    pass


@dataclass
class TimeAndDateAnnouncement(OutboundSignalingPacket):
    """P25 TIME_DATE_ANN"""
    pass


@dataclass
class SecondaryControlChannelBroadcastExplicit(OutboundSignalingPacket):
    """P25 SCCB_EXP"""
    pass


@dataclass
class IdentifierUpdateVu(OutboundSignalingPacket):
    """P25 IDEN_UP_VU"""
    pass