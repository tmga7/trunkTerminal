import enum


class RadioState(enum.Enum):
    OFF = 0
    IDLE = 1
    REGISTERING = 2
    AFFILIATED = 3
    TRANSMITTING = 4
    RECEIVING = 5
    OUT_OF_RANGE = 6


class CallState(enum.Enum):
    REQUESTED = 0
    ALLOCATING = 1
    ACTIVE = 2
    ENDING = 3
    ENDED = 4
    DENIED = 5


class ChannelState(enum.Enum):
    IDLE = 0
    BUSY = 1


class SiteState(enum.Enum):
    STARTING = 0
    ACTIVE = 1
    STOPPING = 2
    STOPPED = 3
    FAILED = 4


# Event Classes
class Event:
    def __init__(self, event_type, data):
        self.event_type = event_type
        self.data = data


class PTTPressEvent(Event):
    def __init__(self, subscriber_unit):
        super().__init__('PTTPress', {'subscriber_unit': subscriber_unit})


class PTTReleaseEvent(Event):
    def __init__(self, subscriber_unit):
        super().__init__('PTTRelease', {'subscriber_unit': subscriber_unit})


class CallRequestEvent(Event):
    def __init__(self, subscriber_unit):
        super().__init__('CallRequest', {'subscriber_unit': subscriber_unit})


# Event Dispatcher
class EventDispatcher:
    def __init__(self):
        self.listeners = {}

    def register_listener(self, event_type, listener):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(listener)

    def dispatch(self, event):
        if event.event_type in self.listeners:
            for listener in self.listeners[event.event_type]:
                listener(event)
