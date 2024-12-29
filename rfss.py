class Channel:
    def __init__(self, number, enabled=False, control=False, voice=False, fdma=False, tdma=False, data=False,
                 freq_tx=136.00000, freq_rx=137.00000):
        self.number = number
        self.enabled = enabled
        self.control = control
        self.voice = voice
        self.fdma = fdma
        self.tdma = tdma
        self.data = data
        self.freq_tx = freq_tx
        self.freq_rx = freq_rx

    def __repr__(self):
        return f"Channel(number={self.number}, enabled={self.enabled}, control={self.control}, voice={self.voice}, fdma={self.fdma}, tdma={self.tdma}, data={self.data}, freq_tx={self.freq_tx}, freq_rx={self.freq_rx})"


class Subsite:
    def __init__(self, alias, location_x, location_y):
        self.alias = alias
        self.location_x = location_x
        self.location_y = location_y

    def __repr__(self):
        return f"Subsite(alias='{self.alias}', location_x={self.location_x}, location_y={self.location_y})"


class Site:
    def __init__(self, alias, enabled, mode, allowed_talkgroups):
        self.alias = alias
        self.enabled = enabled
        self.mode = mode
        self.allowed_talkgroups = allowed_talkgroups
        self.channels = {}
        self.subsites = {}

    def __repr__(self):
        channels_str = ", ".join(repr(c) for c in self.channels.values())
        subsites_str = ", ".join(repr(s) for s in self.subsites.values())
        return f"Site(alias='{self.alias}', enabled={self.enabled}, mode='{self.mode}', allowed_talkgroups={self.allowed_talkgroups}, channels=[{channels_str}], subsites=[{subsites_str}])"


    def add_channel(self, id, channel_data):
        self.channels[id] = Channel(
            id,  # Pass the channel ID here
            channel_data.get('enabled', False),
            channel_data.get('control', False),
            channel_data.get('voice', False),
            channel_data.get('fdma', False),
            channel_data.get('tdma', False),
            channel_data.get('data', False),
            channel_data.get('freq_tx', 136.00000),
            channel_data.get('freq_rx', 136.00000)
        )

    def add_subsite(self, id, data):
        self.subsites[id] = Subsite(data['alias'], data['location_x'], data['location_y'])


class RFSS:
    def __init__(self, id):
        self.id = id
        self.sites = {}

    def __repr__(self):
        sites_str = ", ".join(repr(s) for s in self.sites.values())
        return f"RFSS(id={self.id}, sites=[{sites_str}])\r\n"

    def add_site(self, site_id, site_data):  # Corrected add_site method
        site = Site(
            site_data.get('alias'),
            site_data.get('enabled'),
            site_data.get('mode'),
            site_data.get('allowed_talkgroups', [])
        )
        for channel_id, channel_data in site_data.get('channels', {}).items():
            site.add_channel(channel_id, channel_data)
        for subsite_id, subsite_data in site_data.get('subsites', {}).items():
            site.add_subsite(subsite_id, subsite_data)
        self.sites[site_id] = site  # Use site_id to store the site
