from events import *

class ChannelManager:
    def __init__(self, event_bus, config):
        self.event_bus = event_bus
        self.config = config

    def handle_channel_allocated(self, event):
        # This function is no longer needed in the core channel manager
        # because site channel management is handled by the SiteController.
        pass

    def handle_call_ended(self, event):
        # This function is no longer needed in the core channel manager
        # because site channel management is handled by the SiteController.
        pass
