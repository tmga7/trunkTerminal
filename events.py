class Event:
    pass

class SiteStartRequested(Event):
    def __init__(self, site_id):
        self.site_id = site_id

class SiteStarted(Event):
    def __init__(self, site_id, control_channel_id):
        self.site_id = site_id
        self.control_channel_id = control_channel_id

class SiteStartFailed(Event):
    def __init__(self, site_id, reason):
        self.site_id = site_id
        self.reason = reason

class SiteStopRequested(Event):
    def __init__(self, site_id):
        self.site_id = site_id

class SiteStopped(Event):
    def __init__(self, site_id):
        self.site_id = site_id

class SiteFailRequested(Event):
    def __init__(self, site_id, reason):
        self.site_id = site_id
        self.reason = reason

class SiteFailed(Event):
    def __init__(self, site_id, reason):
        self.site_id = site_id
        self.reason = reason

class CallStartRequested(Event):
    def __init__(self, rid, tgid, call_length, ckr):
        self.rid = rid
        self.tgid = tgid
        self.call_length = call_length
        self.ckr = ckr

class CallAllocated(Event):
    def __init__(self, call_id, channel_id, rid, tgid, call_mode, ptt_id, slot=None):
        self.call_id = call_id
        self.channel_id = channel_id
        self.rid = rid
        self.tgid = tgid
        self.call_mode = call_mode
        self.ptt_id = ptt_id
        self.slot = slot

class CallDenied(Event):
    def __init__(self, rid, tgid, reason):
        self.rid = rid
        self.tgid = tgid
        self.reason = reason

class CallEnded(Event):
    def __init__(self, call_id, site_id, channel_id, call_mode, slot=None):
        self.call_id = call_id
        self.site_id = site_id
        self.channel_id = channel_id
        self.call_mode = call_mode
        self.slot = slot

class UnitRegistered(Event):
    def __init__(self, rid, site_id):
        self.rid = rid
        self.site_id = site_id

class UnitAffiliated(Event):
    def __init__(self, rid, tgid):
        self.rid = rid
        self.tgid = tgid

class RadioPowerOn(Event):
    def __init__(self, rid):
        self.rid = rid

class RadioSiteListRequested(Event):
    def __init__(self, rid):
        self.rid = rid

class RadioSiteListReceived(Event):
    def __init__(self, rid, sites):  # sites is a dictionary {site_id: rssi}
        self.rid = rid
        self.sites = sites

class RadioRegisterRequested(Event):
    def __init__(self, rid, site_id):
        self.rid = rid
        self.site_id = site_id

class RadioAffiliateRequested(Event):
    def __init__(self, rid, tgid):
        self.rid = rid
        self.tgid = tgid

class RadioPtt(Event):
    def __init__(self, rid, tgid, call_length, ckr):
        self.rid = rid
        self.tgid = tgid
        self.call_length = call_length
        self.ckr = ckr

class AllocateChannel(Event):
    def __init__(self, rid, tgid, site_id, call_id, call_mode):
        self.rid = rid
        self.tgid = tgid
        self.site_id = site_id
        self.call_id = call_id
        self.call_mode = call_mode

class ChannelAllocatedOnSite(Event):
    def __init__(self, site_id, channel_id, call_id, tgid, call_mode):
        self.site_id = site_id
        self.channel_id = channel_id
        self.call_id = call_id
        self.tgid = tgid
        self.call_mode = call_mode

class ChannelAllocationFailedOnSite(Event):
    def __init__(self, site_id, call_id, tgid, reason):
        self.site_id = site_id
        self.call_id = call_id
        self.tgid = tgid
        self.reason = reason
