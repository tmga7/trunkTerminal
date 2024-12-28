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
        self.active_calls = {}  # Dictionary to store active calls

    def is_call_active(self, tgid):
        for call in self.active_calls.values():
            if call["tgid"] == tgid:
                return True
        return False

    def handle_console_call_start_requested(self, event):
        if self.is_call_active(event.tgid):
            print("Console preempted ongoing call.")
            self.event_bus.publish(ConsoleCallPreempted(event.rid, event.tgid))
        else:
            self.handle_console_call_request(event)

    def handle_call_request(self, event):
        if self.is_call_active(event.tgid):
            print("Subscriber preempted ongoing call.")
            self.event_bus.publish(SubscriberCallPreempted(event.rid, event.tgid))
        else:
            call_id = self.generate_call_id()
            self.pending_allocations[call_id] = {
                "call_length": event.call_length,
                "rid": event.rid,
                "tgid": event.tgid,
                "call_mode": event.ckr,
                "allocated": {},  # Dictionary to track allocated channels per site
                "state": CallState.REQUESTED  # Initialize the state
            }
            print(
                f"Call {call_id}: Request for TGID {event.tgid} from RID {event.rid} - State: {self.pending_allocations[call_id]['state']}")

            for site_id in self.config["sites"]:
                self.event_bus.publish(AllocateChannel(event.rid, event.tgid, site_id, call_id, event.ckr))

    def handle_channel_allocated_on_site(self, event):
        call_id = event.call_id
        if call_id not in self.pending_allocations:
            return

        self.pending_allocations[call_id]["allocated"][event.site_id] = event.channel_id

        if all(self.pending_allocations[call_id]["allocated"].values()):
            call_data = self.pending_allocations[call_id]
            self.active_calls[call_id] = {"rid": call_data["rid"], "tgid": call_data["tgid"],
                                          "state": CallState.ALLOCATING}  # Add to active calls WITH STATE
            print(f"Call {call_id}: Allocated on all sites - State: {self.active_calls[call_id]['state']}")
            call_mode = call_data["call_mode"]
            ptt_id = self.get_talkgroup_ptt_id(call_data["tgid"])
            slots = None
            if call_mode == "TDMA":
                slots = self.allocate_tdma_slots(call_data["allocated"])
                if slots == None:
                    self.pending_allocations[call_id]["state"] = CallState.DENIED
                    print(
                        f"Call {call_id}: Allocation Denied - No TDMA slots available - State: {self.pending_allocations[call_id]['state']}")
                    self.event_bus.publish(CallDenied(call_data["rid"], call_data["tgid"], "No TDMA slots available"))
                    return

            self.event_bus.publish(
                CallAllocated(call_id, call_data["allocated"], call_data["rid"], call_data["tgid"], call_mode, ptt_id,
                              slots))
            self.start_call_timer(call_id, call_data["call_length"], ptt_id, call_mode, call_data["allocated"], slots,
                                  call_data["rid"], call_data["tgid"])
            del self.pending_allocations[call_id]
        else:
            print(
                f"Call {call_id}: Waiting for other sites to allocate channels - State: {CallState.ALLOCATING if call_id in self.pending_allocations else 'N/A'}")  # Added state output and conditional check

    def start_call_timer(self, call_id, call_length, ptt_id, call_mode, allocated_channels, slots, rid, tgid):
        if call_id in self.active_calls:  # Check if call exists before changing state
            self.active_calls[call_id]["state"] = CallState.ACTIVE
            print(f"Call {call_id}: Active, State: {self.active_calls[call_id]['state']}")

        def end_call():
            if call_id in self.active_calls:  # Check if call exists before changing state
                self.active_calls[call_id]["state"] = CallState.ENDING
                print(f"Call {call_id}: Ending, State: {self.active_calls[call_id]['state']}")

                for site_id, channel_id in allocated_channels.items():
                    self.event_bus.publish(
                        CallEnded(call_id, int(site_id), channel_id, call_mode,
                                  slots.get(int(site_id)) if slots else None))

                del self.active_calls[call_id]
                print(f"Call {call_id}: Ended, State: {CallState.ENDED}")

        if ptt_id:
            # PTT-ID mode: use hang time
            hang_time = 0
            for tg_id, tg_config in self.config.get("talkgroups", {}).items():
                if int(tg_id) == tgid:
                    hang_time = tg_config["prop_hangtime"] / 1000
                    break
            print(f"Call {call_id}: Starting timer for {call_length + hang_time} seconds (PTT-ID mode)")
            time.sleep(call_length + hang_time)
            end_call()

        else:
            # Transmission mode: release immediately after call length
            print(f"Call {call_id}: Starting timer for {call_length} seconds (Transmission mode)")
            time.sleep(call_length)
            end_call()

    def determine_involved_sites(self, tgid):
        # Logic to determine involved sites based on talkgroup affiliation
        # For simplicity, returning a fixed list for now.
        return [1, 2]

    def determine_call_mode(self, tgid, sites):
        # check if the talkgroup is mixed mode
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
