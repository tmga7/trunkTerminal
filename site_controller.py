from events import *

class SiteController:
    def __init__(self, site_id, event_bus, site_config):
        self.site_id = site_id
        self.event_bus = event_bus
        self.site_config = site_config
        self.channels = {int(chan_id): {"busy": False, "slotA": False, "slotB": False} for chan_id in site_config["channels"]}
        self.last_assigned_channel = None # For rollover
        self.channel_usage_count = {} # For balanced
        for chan_id in self.site_config["channels"]:
            self.channel_usage_count[int(chan_id)] = 0

        self.event_bus.subscribe("AllocateChannel", self.handle_allocate_channel)
        self.event_bus.subscribe("CallEnded", self.handle_call_ended)

    def handle_allocate_channel(self, event):
        if event.site_id != self.site_id:
            return

        channel_id = self.find_free_channel(event.call_mode)
        if channel_id:
            self.channels[channel_id]["busy"] = True
            self.event_bus.publish(ChannelAllocatedOnSite(self.site_id, channel_id, event.call_id, event.tgid, event.call_mode))
        else:
            self.event_bus.publish(ChannelAllocationFailedOnSite(self.site_id, event.call_id, event.tgid, "No channels available"))

    def find_free_channel(self, call_mode):
        assignment_mode = self.site_config.get("prop_assignment_mode", "balanced")
        available_channels = []

        for channel_id, channel_state in self.channels.items():
            channel_config = self.site_config["channels"][str(channel_id)]
            if not channel_state["busy"] and channel_config["enabled"]:
                if call_mode == "FDMA" and channel_config["fdma"]:
                    available_channels.append(int(channel_id))
                elif call_mode == "TDMA" and channel_config["tdma"]:
                    available_channels.append(int(channel_id))

        if not available_channels:
            return None

        if assignment_mode == "balanced":
            return self.assign_balanced(available_channels)
        elif assignment_mode == "rollover":
            return self.assign_rollover(available_channels)
        elif assignment_mode == "random":
            return self.assign_random(available_channels)
        else:
            return self.assign_balanced(available_channels) # Default to balanced

    def assign_balanced(self, available_channels):
        if not available_channels:
            return None

        min_usage = min(self.channel_usage_count[chan] for chan in available_channels)
        best_channels = [chan for chan in available_channels if self.channel_usage_count[chan] == min_usage]
        chosen_channel = min(best_channels)
        self.channel_usage_count[chosen_channel] += 1
        return chosen_channel

    def assign_rollover(self, available_channels):
        if not available_channels:
            return None
        if self.last_assigned_channel is None or self.last_assigned_channel not in available_channels:
            self.last_assigned_channel = min(available_channels)
        else:
            current_index = available_channels.index(self.last_assigned_channel)
            next_index = (current_index + 1) % len(available_channels)
            self.last_assigned_channel = available_channels[next_index]
        return self.last_assigned_channel

    def assign_random(self, available_channels):
        if available_channels:
            return random.choice(available_channels)
        return None

    def handle_call_ended(self, event):
        if event.site_id == self.site_id:
            if event.channel_id:
                self.channels[event.channel_id]["busy"] = False
                if event.slot:
                    if event.slot == "A":
                        self.channels[event.channel_id]["slotA"] = False
                    elif event.slot == "B":
                        self.channels[event.channel_id]["slotB"] = False
