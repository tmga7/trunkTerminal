from events import *
import time
import threading

class CallManager:
    def __init__(self, event_bus, config, site_controllers):
        self.event_bus = event_bus
        self.config = config
        self.site_controller = site_controllers
        self.pending_allocations = {}  # Track pending allocations per call
        self.call_counter = 1

    def handle_call_request(self, event):
        call_id = self.call_counter
        self.call_counter += 1
        sites = self.determine_involved_sites(event.tgid)
        call_mode = self.determine_call_mode(event.tgid, sites)

        if call_mode == "FDMA":
            if not self.check_fdma_channels_available(sites):
                self.event_bus.publish(CallDenied(event.rid, event.tgid, "No FDMA channels available on all sites"))
                return

        self.pending_allocations[call_id] = {
            "sites": sites,
            "allocated": {site: None for site in sites}, # Store allocated channel per site
            "call_mode": call_mode,
            "call_length": event.call_length,
            "ckr": event.ckr,
            "rid": event.rid,
            "tgid": event.tgid
        }

        for site_id in sites:
            self.event_bus.publish(AllocateChannel(event.rid, event.tgid, site_id, call_id, call_mode))

    def handle_allocate_channel(self, event):
        call_id = event.call_id
        if call_id not in self.pending_allocations:
            return

        self.pending_allocations[call_id]["allocated"][event.site_id] = event.channel_id

        if all(self.pending_allocations[call_id]["allocated"].values()):
            call_data = self.pending_allocations[call_id]
            call_mode = call_data["call_mode"]
            ptt_id = self.get_talkgroup_ptt_id(call_data["tgid"])
            slots = None
            if call_mode == "TDMA":
                slots = self.allocate_tdma_slots(call_data["allocated"])
                if slots == None:
                    self.event_bus.publish(CallDenied(call_data["rid"], call_data["tgid"], "No TDMA slots available"))
                    return

            self.event_bus.publish(CallAllocated(call_id, call_data["allocated"], call_data["rid"], call_data["tgid"], call_mode, ptt_id, slots))
            self.start_call_timer(call_id, call_data["call_length"], ptt_id, call_mode, call_data["allocated"], slots, call_data["rid"], call_data["tgid"])
            del self.pending_allocations[call_id]
        else:
            print(f"Waiting for other sites")

    def allocate_tdma_slots(self, allocated_channels):
        slots = {}
        for site_id, channel_id in allocated_channels.items():
            if channel_id:
                if self.site_controller[site_id].channels[channel_id].get("slotA") == False:
                    self.site_controller[site_id].channels[channel_id]["slotA"] = True
                    slots[site_id] = "A"
                elif self.site_controller[site_id].channels[channel_id].get("slotB") == False:
                    self.site_controller[site_id].channels[channel_id]["slotB"] = True
                    slots[site_id] = "B"
                else:
                    return None
            else:
                return None
        return slots

    def start_call_timer(self, call_id, call_length, ptt_id, call_mode, allocated_channels, slots, rid, tgid):
        def end_call():
            for site_id, channel_id in allocated_channels.items():
                self.event_bus.publish(CallEnded(call_id, int(site_id), channel_id, call_mode, slots.get(int(site_id)) if slots else None))

        if ptt_id:
            # PTT-ID mode: use hang time
            hang_time = 0
            for tg_id, tg_config in self.config.get("talkgroups", {}).items():
                if int(tg_id) == tgid:
                    hang_time = tg_config["prop_hangtime"] / 1000
                    break
            time.sleep(call_length + hang_time)
            end_call()

        else:
            # Transmission mode: release immediately after call length
            time.sleep(call_length)
            end_call()

    def determine_involved_sites(self, tgid):
        # Logic to determine involved sites based on talkgroup affiliation
        # For simplicity, returning a fixed list for now.
        return [1, 2]

    def determine_call_mode(self, tgid, sites):
        #check if the talkgroup is mixed mode
        tg_config = None
        for tg_id, tg in self.config.get("talkgroups", {}).items():
            if int(tg_id) == tgid:
                tg_config = tg
                break
        if not tg_config:
            return "TDMA"
        if tg_config["prop_mode"] == "mixed":
            for site in sites:
                for unit_id in self.unit_manager.units:
                    if self.unit_manager.is_unit_tdma_capable(unit_id) == False:
                        return "FDMA"
            return "TDMA"
        elif tg_config["prop_mode"] == "fdma":
            return "FDMA"
        else:
            return "TDMA"

    def check_fdma_channels_available(self, sites):
        for site_id in sites:
            has_fdma_channel = False
            for chan_id, chan_config in self.config["sites"][str(site_id)]["channels"].items():
                if chan_config.get("fdma") and chan_config.get("enabled"):
                    has_fdma_channel = True
                    break
            if not has_fdma_channel:
                return False  # No FDMA channel on this site
        return True  # FDMA channels available on all sites

    def get_talkgroup_ptt_id(self, tgid):
      tg_config = None
      for tg_id, tg in self.config.get("talkgroups", {}).items():
          if int(tg_id) == tgid:
              tg_config = tg
              break
      if tg_config:
          return tg_config["prop_ptt_id"]
      return False
