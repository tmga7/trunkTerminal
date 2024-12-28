class EventBus:
    def __init__(self):
        self.subscribers = {}  # Dictionary to hold event subscriptions

    def subscribe(self, event_type, callback):
        if not isinstance(event_type, type):
            raise TypeError("event_type must be a class")
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def publish(self, event):
        event_type = type(event)
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                callback(event)
