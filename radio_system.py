from event_bus import EventBus

class RadioSystem:
    def __init__(self, config):
        self.config = config
        self.event_bus = EventBus()

    def start(self):
        # Start any background processes or services
        pass

    def stop(self):
        # Stop any background processes or services
        pass
