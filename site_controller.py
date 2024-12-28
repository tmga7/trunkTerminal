from events import *

class SiteController:
    def __init__(self, site_id, event_bus, site_config):
        self.site_id = site_id
        self.event_bus = event_bus
        self.site_config = site_config
        self.channels = {int(chan_id): {"state": ChannelState.IDLE, "slotA": False, "slotB": False} for chan_id in site_config["channels"]}
        self.site_state = SiteState.STOPPED # Initialize site state
        self.last_assigned_channel = None # For rollover
        self.channel_usage_count = {} # For balanced
        self.site_started = False  # Add this line! Initialize to False
        for chan_id in self.site_config["channels"]:
            self.channel_usage_count[int(chan_id)] = 0



        self.event_bus.subscribe(SiteStartRequested, self.handle_site_start_requested)
        self.event_bus.subscribe(SiteStopRequested, self.handle_site_stop_requested)
        self.event_bus.subscribe(SiteFailRequested, self.handle_site_fail_requested)
        self.event_bus.subscribe(AllocateChannel, self.handle_allocate_channel)
        self.event_bus.subscribe(CallEnded, self.handle_call_ended)

        self.registered_units = set()
        self.event_bus.subscribe(UnitRegistered, self.handle_unit_registered)

    def handle_unit_registered(self, event):
        if event.site_id != self.site_id:
            return

        if self.site_started:  # Check if the site has started
            if self.is_talkgroup_allowed(event.tgid):
                self.registered_units.add(event.rid)
                self.event_bus.publish(UnitRegistrationSuccess(event.rid, self.site_id))  # Publish a success event
                print(f"Site {self.site_id}: Unit {event.rid} Registered")
            else:
                self.event_bus.publish(
                    UnitRegistrationFailed(event.rid, self.site_id, "Talkgroup is not allowed at this site"))
                print(
                    f"Site {self.site_id}: Unit {event.rid} Registration Failed: Talkgroup is not allowed at this site")
        else:
            self.event_bus.publish(UnitRegistrationFailed(event.rid, self.site_id, "Site is not active"))
            print(f"Site {self.site_id}: Unit {event.rid} Registration Failed: Site is not active")

    def is_talkgroup_allowed(self, tgid):
        if "allowed_talkgroups" in self.site_config:
            return tgid in self.site_config["allowed_talkgroups"]
        return True  # Default to true if not specified

    def handle_site_start_requested(self, event):
        if event.site_id != self.site_id:
            return  # Not for this site

        self.site_state = SiteState.STARTING
        print(f"Site {self.site_id}: Starting, State: {self.site_state}")

        control_channels = []
        voice_channels = []

        for channel_id_str, channel_config in self.site_config["channels"].items():
            if channel_config.get("enabled"):
                channel_id = int(channel_id_str) #Convert from string to int
                if channel_config.get("control"):
                    control_channels.append(channel_id)
                if channel_config.get("voice"):
                    voice_channels.append(channel_id)

        if not control_channels:
            self.event_bus.publish(SiteStartFailed(self.site_id, "No control channels available"))
            print(f"Site {self.site_id}: No control channels available")
            return

        if not voice_channels:
            self.event_bus.publish(SiteStartFailed(self.site_id, "No voice channels available"))
            print(f"Site {self.site_id}: No voice channels available")
            return

        # Assign the lowest numbered control channel
        control_channels.sort()
        control_channel_id = control_channels[0]
        self.channels[control_channel_id]["control"] = True #Set the control channel
        self.site_started = True  # Set to True when the site starts!
        self.event_bus.publish(SiteStarted(self.site_id, control_channel_id))
        print(f"Site {self.site_id}: Started with control channel {control_channel_id}")

    def handle_site_stop_requested(self, event):
        if event.site_id != self.site_id:
            return

        # Perform any cleanup or shutdown logic here (e.g., release channels)
        for channel_id in self.channels:
            self.channels[channel_id]["busy"] = False
            self.channels[channel_id]["slotA"] = False
            self.channels[channel_id]["slotB"] = False
        self.site_started = False # Set to False when the site stops
        print(f"Site {self.site_id}: Stopped")
        self.event_bus.publish(SiteStopped(self.site_id))

    def handle_site_fail_requested(self, event):
        if event.site_id != self.site_id:
            return

        reason = event.reason
        # Perform any failure-specific logic (e.g., set status, log error)
        print(f"Site {self.site_id}: Failed due to {reason}")
        self.event_bus.publish(SiteFailed(self.site_id, reason))


    def handle_allocate_channel(self, event):
        if event.site_id != self.site_id:
            return
        channel_id = self.find_free_channel(event.call_mode)
        if channel_id:
            self.channels[channel_id]["state"] = ChannelState.BUSY
            print(f"Site {self.site_id}: Channel {channel_id} is now {self.channels[channel_id]['state']}")
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
        if event.site_id == self.site_id and event.channel_id:
            self.channels[event.channel_id]["state"] = ChannelState.IDLE
            print(f"Site {self.site_id}: Channel {event.channel_id} is now {self.channels[event.channel_id]['state']}")

        if event.site_id == self.site_id:
            if event.channel_id:
                self.channels[event.channel_id]["busy"] = False
                if event.slot:
                    if event.slot == "A":
                        self.channels[event.channel_id]["slotA"] = False
                    elif event.slot == "B":
                        self.channels[event.channel_id]["slotB"] = False