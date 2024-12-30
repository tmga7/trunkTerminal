import random

# Channel Capabilities
CHANNEL_CAP_CONTROL = 0x01  # 0000 0001 -> 1
CHANNEL_CAP_FDMA = 0x02  # 0000 0010 -> 2
CHANNEL_CAP_TDMA = 0x04  # 0000 0100 -> 4
CHANNEL_CAP_BSI = 0x08  # 0000 1000 -> 8
CHANNEL_CAP_DATA = 0x10  # 0001 0000 -> 16

# Call Types
CALL_TDMA_A = 0x20  # 0010 0000 -> 32
CALL_TDMA_B = 0x40  # 0100 0000 -> 64
CALL_FDMA = 0x80  # 1000 0000 -> 128

# Channel Status
CHANNEL_ENABLED = 0x01  # 0000 0001 -> 1
CHANNEL_ERROR = 0x02  # 0000 0010 -> 2
CHANNEL_SERVICE_MODE = 0x04  # 0000 0100 -> 4
CHANNEL_DISABLED = 0x08  # 0000 1000 -> 8

# Site Status
STATUS_SITE_OFFLINE = 0x10  # 0001 0000 -> 16
STATUS_SITE_SITE_TRUNKING = 0x20  # 0010 0000 -> 32
STATUS_SITE_FAILSOFT = 0x40  # 0100 0000 -> 64
STATUS_SITE_IMPAIRED = 0x80  # 1000 0000 -> 128
STATUS_SITE_WIDEAREA = 0x100  # 0001 0000 0000 -> 256

# Radio Types
RADIO_TYPE_SUBSCRIBER = 0x01  # 0000 0001 -> 1
RADIO_TYPE_CONSOLE = 0x02  # 0000 0010 -> 2

# Call Types (extended)
CALL_TYPE_VOICE = 0x04  # 0000 0100 -> 4
CALL_TYPE_PATCHED = 0x08  # 0000 1000 -> 8
CALL_TYPE_PRIVATE = 0x10  # 0001 0000 -> 16
CALL_TYPE_MULTI_SELECT = 0x20  # 0010 0000 -> 32
CALL_TYPE_OTAR = 0x40  # 0100 0000 -> 64
CALL_TYPE_OTAP = 0x80  # 1000 0000 -> 128
CALL_TYPE_DATA = 0x100  # 0001 0000 0000 -> 256

# Modes
MODE_PTT_ID = 0x01  # 0000 0001 -> 1
MODE_TRANSMISSION = 0x02  # 0000 0010 -> 2

# End Reasons
END_REASON_NORMAL = 0x04  # 0000 0100 -> 4
END_REASON_PREEMPTED = 0x08  # 0000 1000 -> 8
END_REASON_EMERGENCY = 0x10  # 0001 0000 -> 16
END_REASON_FAIL = 0x20  # 0010 0000 -> 32

# TDMA Slot Status Constants
TDMA_SLOT_FREE = 0x10
TDMA_SLOT_IN_USE = 0x11
TDMA_IN_USE = 0x12

# FDMA Channel Status Constants
FDMA_FREE = 0x20
FDMA_IN_USE = 0x21
FDMA_SLOT = "FDMA"

STATUS_SITE_OFFLINE = 0x01  # not intialized
STATUS_SITE_SITE_TRUNKING = 0x02  # future use: simulated network failure to other radio systems
STATUS_SITE_FAILSOFT = 0x04  # system is not processing any calls
STATUS_SITE_IMPAIRED = 0x08  # future use: subsites within the radio system have failed, but system mostly works
STATUS_SITE_WIDEAREA = 0x10  # system is intialized, ready to operate

CALL_TYPE_VOICE = 0x01
CALL_TYPE_PATCHED = 0x02
CALL_TYPE_PRIVATE = 0x04
CALL_TYPE_MULTI_SELECT = 0x08
CALL_TYPE_OTAR = 0x10
CALL_TYPE_OTAP = 0x20
CALL_TYPE_DATA = 0x40

# Talkgroup Capabilities
MODE_PTT_ID = 0x01
MODE_TRANSMISSION = 0x02

STATUS_IDLE = 0x01
STATUS_HANDSHAKING = 0x02
STATUS_BUSY = 0x04
STATUS_OFFLINE = 0x08

CALL_REASON_NONE = 0x00
CALL_REASON_IN_USE = 0x01
CALL_REASON_BLOCKED = 0x02
CALL_REASON_PREEMPTED = 0x04
CALL_REASON_EMERGENCY = 0x08

# Globals
CHANNEL_IDLE = 0x00
CHANNEL_BUSY = 0x01
CHANNEL_HANDSHAKING = 0x05
CHANNEL_ERROR = 0x06
CHANNEL_SERVICE_MODE = 0x07
CHANNEL_OFFLINE = 0x08

# TDMA Slot Specific States

# Control Channel Specific States
CONTROL_PRIMARY = 0x07
CONTROL_SECONDARY = 0x08
CONTROL_DISABLED = 0x09


class Channel:
    def __init__(self, number, capabilities, freq_tx, freq_rx):
        self.number = number
        self.capabilities = capabilities  # Use bit flags
        self.freq_tx = freq_tx
        self.freq_rx = freq_rx
        self.status = CHANNEL_IDLE
        self.is_control_channel = False
        self.current_calls = {}
        self.slot_a_status = TDMA_SLOT_FREE
        self.slot_b_status = TDMA_SLOT_FREE
        self.status = FDMA_FREE

    def has_capability(self, capability):
        return (self.capabilities & capability) != 0


class Talkgroup:
    def __init__(self, tgid, mode, allow_fdma=True, allow_tdma=True, downgrade=True):
        self.id = tgid
        self.mode = mode
        self.hangtime = 3000  # Important for PTT-ID, we will use a default for now
        self.downgrade = downgrade  # If a FDMA call affiliates, we will downgrade (to do)
        self.affiliated_radios = set()  # Keep track of affiliated radios
        self.allow_fdma = allow_fdma
        self.allow_tdma = allow_tdma

    def add_affiliated_radio(self, radio):
        self.affiliated_radios.add(radio)


class Radio:
    def __init__(self, type, is_phase2_capable):  # Add phase 2 capability
        self.type = type  # "Subscriber", "Console"
        self.is_phase2_capable = is_phase2_capable  # add the property


class Call:
    def __init__(self, call_type, initiating_radio, target_talkgroups, target_radios=None, channel=None, tdma_slot=None,
                 call_duration=None):
        self.call_type = call_type
        self.initiating_radio = initiating_radio
        self.target_talkgroups = target_talkgroups  # List of talkgroups
        self.target_radios = target_radios  # List of radios
        self.channel = channel
        self.tdma_slot = tdma_slot
        self.call_duration = call_duration
        self.call_id = random.randint(1000, 9999)
        self.call_status = STATUS_HANDSHAKING
        self.call_reason = CALL_REASON_NONE


class SiteController:

    def __init__(self, system):
        self.talkgroups = {123: Talkgroup(123, MODE_PTT_ID, True, True, True),
                           456: Talkgroup(456, MODE_PTT_ID, True, True, True)}
    def determine_fdma_tdma(call_type, initiating_radio, talkgroup_ids=None, target_radio=None):
        if call_type in [CALL_TYPE_OTAR, CALL_TYPE_OTAP, CALL_TYPE_DATA]:
            return 'FDMA'

        if call_type == CALL_TYPE_PRIVATE:
            if not initiating_radio.is_phase2_capable or not target_radio.is_phase2_capable:
                return 'FDMA'
            return 'TDMA'

        if call_type in [CALL_TYPE_VOICE, CALL_TYPE_PATCHED, CALL_TYPE_MULTI_SELECT]:
            for tg_id in talkgroup_ids:
                tg = self.talkgroups[tg_id]
                if tg.downgrade and any(not r.is_phase2_capable for r in tg.affiliated_radios):
                    return 'FDMA'
            return 'TDMA'

        return None  # Invalid call type


class ControlChannelManager:
    def __init__(self, system):
        self.system = system
        self.control_channel = None

    def _determine_call_capability(self, call_type, initiating_radio, target_talkgroups, target_radios=None):
        """Determines the appropriate call capability (TDMA or FDMA)."""

        if call_type in (CALL_TYPE_OTAR, CALL_TYPE_OTAP, CALL_TYPE_DATA):
            return CHANNEL_CAP_FDMA

        if call_type == CALL_TYPE_PRIVATE:
            if target_radios and all(
                    radio.is_phase2_capable for radio in target_radios) and initiating_radio.is_phase2_capable:
                return CHANNEL_CAP_TDMA
            else:
                return CHANNEL_CAP_FDMA

        # For VOICE, PATCHED, and MULTI_SELECT
        if initiating_radio.is_phase2_capable:
            if all(tg.allow_tdma for tg in target_talkgroups) and all(
                    all(radio.is_phase2_capable for radio in tg.affiliated_radios) for tg in target_talkgroups):
                return CHANNEL_CAP_TDMA
            elif all(tg.downgrade for tg in target_talkgroups) and all(
                    tg.allow_fdma for tg in target_talkgroups):  # check if all talkgroups allow downgrading and FDMA
                return CHANNEL_CAP_FDMA
            else:
                return None  # Call fails if no allowed capability
        elif all(tg.allow_fdma for tg in target_talkgroups):
            return CHANNEL_CAP_FDMA
        else:
            return None  # Call fails if no allowed capability

    def _get_usable_channels(self, capability):
        """Returns a list of usable channels based on capability."""
        usable_channels = []
        for channel in self.system.channels:
            if channel.has_capability(capability) and not channel.is_control_channel:
                usable_channels.append(channel)
        usable_channels.sort(key=lambda ch: ch.number)
        return usable_channels

    def _find_available_channel_and_slot(self, capability, selection_strategy="balanced"):
        """Finds an available channel and time slot using the specified strategy."""

        usable_channels = self._get_usable_channels(capability)
        if not usable_channels:
            return None, None

        if capability == CHANNEL_CAP_TDMA:
            available_slots = []
            for channel in usable_channels:
                if channel.slot_a_status == TDMA_SLOT_FREE:
                    available_slots.append((channel, "A"))
                if channel.slot_b_status == TDMA_SLOT_FREE:
                    available_slots.append((channel, "B"))

            if not available_slots:
                return None, None

            if selection_strategy == "balanced":
                midpoint = len(available_slots) // 2
                channel, time_slot = available_slots[midpoint]
            elif selection_strategy == "random":
                channel, time_slot = random.choice(available_slots)
            elif selection_strategy == "rollover":
                # Implement rollover logic (e.g., FIFO) here
                # For now, just use FIFO
                channel, time_slot = available_slots[0]
            else:
                return None, None

        else:  # FDMA
            available_fdma_channels = [ch for ch in usable_channels if ch.status == CH]
            print(f"Available FDMA channels: {available_fdma_channels}")
            if not available_fdma_channels:
                return None, None
            if selection_strategy == "balanced":
                midpoint = len(available_fdma_channels) // 2
                channel = available_fdma_channels[midpoint]
                time_slot = None
            elif selection_strategy == "random":
                channel = random.choice(available_fdma_channels)
                time_slot = None
            elif selection_strategy == "rollover":
                channel = available_fdma_channels[0]
                time_slot = None
            else:
                return None, None

        if channel:
            if channel.has_capability(CHANNEL_CAP_TDMA):
                if time_slot == "A":
                    channel.slot_a_status = TDMA_SLOT_IN_USE
                else:
                    channel.slot_b_status = TDMA_SLOT_IN_USE
            elif channel.has_capability(CHANNEL_CAP_FDMA):
                channel.status = FDMA_IN_USE
            return channel, time_slot
        else:
            return None, None

    def _find_available_channel_and_slot_old(self, capability):
        available_channels = [
            ch
            for ch in self.system.channels
            if ch.has_capability(capability)
        ]

        if not available_channels:
            return None, None

        # Sort available channels by their index in the system's channel list
        available_channels.sort(key=lambda ch: self.system.channels.index(ch))

        midpoint = len(available_channels) // 2

        # prefer the midpoint
        if len(available_channels) % 2 == 0:  # even number of channels
            if available_channels[midpoint - 1].has_capability(CHANNEL_CAP_TDMA):
                channel = available_channels[midpoint - 1]
                if channel.slot_a_status == TDMA_SLOT_FREE:
                    time_slot = "A"
                elif channel.slot_b_status == TDMA_SLOT_FREE:
                    time_slot = "B"
                else:
                    channel = None
            elif available_channels[midpoint].has_capability(CHANNEL_CAP_TDMA):
                channel = available_channels[midpoint]
                if channel.slot_a_status == TDMA_SLOT_FREE:
                    time_slot = "A"
                elif channel.slot_b_status == TDMA_SLOT_FREE:
                    time_slot = "B"
                else:
                    channel = None
            elif available_channels[midpoint - 1].status == FDMA_FREE:
                channel = available_channels[midpoint - 1]
                time_slot = None
            elif available_channels[midpoint].status == FDMA_FREE:
                channel = available_channels[midpoint]
                time_slot = None
            else:
                return None, None
        else:
            channel = available_channels[midpoint]
            if channel.has_capability(CHANNEL_CAP_TDMA):
                if channel.slot_a_status == TDMA_SLOT_FREE:
                    time_slot = "A"
                elif channel.slot_b_status == TDMA_SLOT_FREE:
                    time_slot = "B"
                else:
                    channel = None
            elif channel.status == FDMA_FREE:
                time_slot = None
            else:
                channel = None

        if channel:
            if channel.has_capability(CHANNEL_CAP_TDMA):
                if time_slot == "A":
                    channel.slot_a_status = TDMA_SLOT_IN_USE
                else:
                    channel.slot_b_status = TDMA_SLOT_IN_USE
            elif channel.has_capability(CHANNEL_CAP_FDMA):
                channel.status = FDMA_IN_USE
            return channel, time_slot
        else:
            # No free voice channels, check for data, OTAR, OTAP calls to preempt
            preempted_calls = []
            for ch in available_channels:
                for slot, call in ch.current_calls.items():
                    if call.call_type in (CALL_TYPE_DATA, CALL_TYPE_OTAR, CALL_TYPE_OTAP):  # check if its in the tuple
                        print(
                            f"Preempting {call.call_type} call (Call ID: {call.call_id}) on Channel {ch.number} to make way for voice call.")
                        preempted_calls.append((call.target_talkgroups[0].id, slot))
                        break  # only preempt one call per channel
            for talkgroup_id, slot in preempted_calls:
                self.end_call(talkgroup_id, slot)
            available_channels = [
                ch
                for ch in self.system.channels
                if ch.has_capability(capability)
            ]
            if not available_channels:
                return None, None

    def initialize(self):
        control_channels = [ch for ch in self.system.channels if ch.has_capability(CHANNEL_CAP_CONTROL)]
        print(f"Control channels that we can use: {control_channels}")
        if not control_channels:
            self.system.site_status = STATUS_SITE_FAILSOFT
            print("System initialization failed: No control channel found. Entering FAILSOFT.")
            return False

        # Find the control channel with the lowest number
        self.control_channel = min(control_channels, key=lambda ch: ch.number)
        self.control_channel.status = CHANNEL_BUSY  # control channel is always busy
        self.control_channel.is_control_channel = True
        print(f"Control Channel Initialized on Channel: {self.control_channel.number}")
        return True

    def process_call_request(self, call_type, initiating_radio, target_talkgroups, target_radios=None,
                             call_duration=None):
        print(
            f"Call Request: Type: {call_type}, Initiating Radio: {initiating_radio.type}, Target Talkgroups: {target_talkgroups}, Target Radios: {target_radios}")
        # Early validation checks
        if (not target_talkgroups) and (call_type in (CALL_TYPE_PATCHED, CALL_TYPE_VOICE, CALL_TYPE_MULTI_SELECT)):
            print("No target talkgroups specified.")
            return

        talkgroups = None
        if target_talkgroups:
            # Check for existing talkgroups
            for talkgroup_id in target_talkgroups:
                if talkgroup_id not in self.system.talkgroups:
                    print(f"Talkgroup {talkgroup_id} does not exist.")
                    return
            talkgroups = [self.system.talkgroups[tg_id] for tg_id in target_talkgroups]

        # Determine call capability
        capability = self._determine_call_capability(call_type, initiating_radio, talkgroups, target_radios)
        print(f"Capability: {capability}")

        if capability is None:
            print(f"Call cannot be established due to capability mismatch.")
            return

        # Attempt to find a channel
        channel, time_slot = self._find_available_channel_and_slot(capability)

        print(f"Channel: {channel.number}")
        # Last-ditch effort: preempt data/OTAR/OTAP if no channel is available
        if not channel:
            preempted_data_calls = []
            for ch in self.system.channels:
                for slot, call in ch.current_calls.items():
                    if call.call_type in (CALL_TYPE_DATA, CALL_TYPE_OTAR, CALL_TYPE_OTAP):
                        print(
                            f"Last-ditch effort: Preempting {call.call_type} call (Call ID: {call.call_id}) on Channel {ch.number}.")
                        preempted_data_calls.append((call.target_talkgroups[0].id, slot))
                        break  # Only preempt one data call per channel

            for talkgroup_id, slot in preempted_data_calls:
                self.end_call(talkgroup_id, slot)

            # Try finding a channel again after preempting data calls
            channel, time_slot = self._find_available_channel_and_slot(capability)
            if channel:
                print("Last-ditch preemption successful.")
            else:
                print("Last-ditch preemption failed. No channels available.")

        # Preemption logic (if console and voice/patched/multi-select call)
        preempted_calls = []  # create a list of calls to preempt
        if target_talkgroups:
            for talkgroup_id in target_talkgroups:
                for channel in self.system.channels:
                    for slot, call in channel.current_calls.items():
                        if call.target_talkgroups:
                            for talkgroup in call.target_talkgroups:
                                if talkgroup.id == talkgroup_id:
                                    if call.call_status == STATUS_BUSY:
                                        if initiating_radio.type == "Console" and call_type in (
                                        CALL_TYPE_PATCHED, CALL_TYPE_MULTI_SELECT):
                                            print(
                                                f"Console marks Talkgroup {talkgroup_id} (Call ID: {call.call_id}) for preemption.")
                                            preempted_calls.append((talkgroup_id, slot))  # add to the list
                                        else:  # Subscriber cannot preempt
                                            print(
                                                f"Talkgroup {talkgroup_id} is busy (Call ID: {call.call_id}). Subscriber cannot preempt.")
                                            return

            # now preempt the calls
            print(preempted_calls)
            for talkgroup_id, slot in preempted_calls:
                self.end_call(talkgroup_id, slot)

        if channel:
            print(f"we are here - we have resources")

            if capability == CHANNEL_CAP_FDMA:
                channel.status = FDMA_IN_USE
                time_slot = FDMA_SLOT
            else:
                channel.status = TDMA_IN_USE
                if time_slot == "A":
                    channel.slot_a_status = TDMA_SLOT_IN_USE
                else:
                    channel.slot_b_status = TDMA_SLOT_IN_USE

            call = Call(call_type, initiating_radio, talkgroups, target_radios, channel, time_slot, call_duration)
            channel.current_calls[time_slot] = call

            if initiating_radio.type == "Console":
                call.call_reason = CALL_REASON_PREEMPTED

            print(
                f"Channel Assigned: Channel {channel.number} ({'TDMA' if channel.has_capability(CHANNEL_CAP_TDMA) else 'FDMA'}), Talkgroup {target_talkgroups}, Call ID: {call.call_id}, Time Slot: {time_slot}")
            print(
                f"Call Started on Channel {channel.number} ({'TDMA' if channel.has_capability(CHANNEL_CAP_TDMA) else 'FDMA'}), Talkgroup {target_talkgroups}, Call ID: {call.call_id}, Time Slot: {time_slot}")
        else:
            talkgroups = [self.system.talkgroups[tg_id] for tg_id in target_talkgroups]  # get talkgroups
            call = Call(call_type, initiating_radio, talkgroups, target_radios, None)
            call.call_reason = CALL_REASON_BLOCKED
            print(f"No available channels for talkgroup {target_talkgroups}. Reason: {call.call_reason}")

    def end_call(self, talkgroup_id, time_slot=None):
        for channel in self.system.channels:
            if channel.current_calls and not channel.is_control_channel:
                ended_calls = []
                for slot, call in channel.current_calls.items():
                    if call.target_talkgroups:
                        for talkgroup in call.target_talkgroups:
                            if talkgroup.id == talkgroup_id:
                                print(
                                    f"Call Ended on Channel {channel.number} ({'TDMA' if channel.has_capability(CHANNEL_CAP_TDMA) else 'FDMA'}), Talkgroup {talkgroup_id}, Call ID: {call.call_id}, Time Slot: {slot}")
                                call.call_status = STATUS_IDLE
                                call.call_reason = CALL_REASON_NONE
                                ended_calls.append(slot)
                                if channel.has_capability(CHANNEL_CAP_TDMA):
                                    if slot == "A":
                                        channel.slot_a_status = TDMA_SLOT_FREE
                                    else:
                                        channel.slot_b_status = TDMA_SLOT_FREE
                                elif channel.has_capability(CHANNEL_CAP_FDMA):
                                    channel.status = FDMA_FREE
                                break
                for ended_call in ended_calls:
                    channel.current_calls.pop(ended_call)
        print(f"No active call found for talkgroup {talkgroup_id}")

    # Add other control channel functions here as needed (e.g., system status broadcasts, radio registration)


class System:
    def __init__(self):
        self.channels = []
        self.talkgroups = {}
        self.radios = []
        self.control_channel_manager = ControlChannelManager(self)  # Now directly manage calls
        self.site_status = STATUS_SITE_OFFLINE

    def initialize_system(self):
        if self.control_channel_manager.initialize():
            self.site_status = STATUS_SITE_WIDEAREA
            print("System initialized. System status: WIDEAREA.")

    def add_channel(self, channel):
        self.channels.append(channel)

    def create_talkgroup(self, talkgroup_id, mode):
        if talkgroup_id not in self.talkgroups:
            self.talkgroups[talkgroup_id] = Talkgroup(talkgroup_id, mode)
            print(f"Talkgroup {talkgroup_id} created.")
        else:
            print("Talkgroup already exists.")


system = System()

# Create Talkgroups
system.create_talkgroup(101, MODE_PTT_ID)
system.create_talkgroup(102, MODE_TRANSMISSION)
system.create_talkgroup(103, MODE_TRANSMISSION)
system.create_talkgroup(104, MODE_TRANSMISSION)
system.create_talkgroup(105, MODE_TRANSMISSION)

system.add_channel(Channel(1, CHANNEL_CAP_FDMA | CHANNEL_CAP_CONTROL, 867.5625, 822.5625))
system.add_channel(
    Channel(2, CHANNEL_CAP_CONTROL | CHANNEL_CAP_TDMA | CHANNEL_CAP_DATA | CHANNEL_CAP_FDMA, 867.5625, 822.5625))
# system.add_channel(Channel(3, CHANNEL_CAP_CONTROL | CHANNEL_CAP_TDMA | CHANNEL_CAP_DATA | CHANNEL_CAP_FDMA, 867.5625, 822.5625))
# system.add_channel(Channel(4, CHANNEL_CAP_DATA | CHANNEL_CAP_DATA | CHANNEL_CAP_FDMA, 867.5625, 822.5625))
# system.add_channel(Channel(5, CHANNEL_CAP_DATA | CHANNEL_CAP_BSI | CHANNEL_CAP_DATA | CHANNEL_CAP_FDMA, 867.5625, 822.5625))

system.initialize_system()

# Create Radios
radio1 = Radio("Subscriber", True)
radio2 = Radio("Subscriber", True)
radio3 = Radio("Subscriber", True)
radio4 = Radio("Subscriber", True)
radio5 = Radio("Subscriber", True)
radioConsole = Radio("Console", True)

system.control_channel_manager.process_call_request(CALL_TYPE_OTAP, radio2, None, None, 15000)
system.control_channel_manager.process_call_request(CALL_TYPE_VOICE, radio1, [101], None, 15000)
# system.control_channel_manager.process_call_request(CALL_TYPE_VOICE, radio3, [102], None, 15000)
# system.control_channel_manager.process_call_request(CALL_TYPE_VOICE, radio4, [103], None, 15000)
# system.control_channel_manager.process_call_request(CALL_TYPE_PATCHED, radioConsole, [101, 102, 103, 104], None, 15000)
