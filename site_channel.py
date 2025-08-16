from site_constants import *


class Channel:

    def __init__(self, number, capabilities, freq_tx, freq_rx):
        self.number = number
        self.capabilities = capabilities
        self.freq_tx = freq_tx
        self.freq_rx = freq_rx
        self.status = CHANNEL_ENABLED
        self.is_control_channel = False
        self.calls = {}

    def has_capability(self, capability):
        return (self.capabilities & capability) != 0
