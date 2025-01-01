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
CALL_REQUEST_GRANT = 0x120  # 0010 0000 -> 32
CALL_REQUEST_DENY = 0x140  # 0100 0000 -> 64
CALL_REQUEST_BUSY = 0x180  # 1000 0000 -> 128

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
RADIO_TYPE_SYSTEM = 0xFFFFFF  # 0000 0100 -> 4

# Call Types (extended)
CALL_TYPE_VOICE = 0x04  # 0000 0100 -> 4
CALL_TYPE_PATCHED = 0x08  # 0000 1000 -> 8
CALL_TYPE_PRIVATE = 0x10  # 0001 0000 -> 16
CALL_TYPE_MULTI_SELECT = 0x20  # 0010 0000 -> 32
CALL_TYPE_OTAR = 0x40  # 0100 0000 -> 64
CALL_TYPE_OTAP = 0x80  # 1000 0000 -> 128
CALL_TYPE_DATA = 0x100  # 0001 0000 0000 -> 256
CALL_TYPE_BSI = 0x120  # 0001 0000 0000 -> 256
CALL_TYPE_SERVICE = 0x140

# Modes
MODE_PTT_ID = 0x01  # 0000 0001 -> 1
MODE_TRANSMISSION = 0x02  # 0000 0010 -> 2

# End Reasons
END_REASON_NORMAL = 0x04  # 0000 0100 -> 4
END_REASON_PREEMPTED = 0x08  # 0000 1000 -> 8
END_REASON_EMERGENCY = 0x10  # 0001 0000 -> 16
END_REASON_FAIL = 0x20  # 0010 0000 -> 32


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


class Talkgroup:
    def __init__(self, tg_id, mode, allow_fdma=True, allow_tdma=True, hang_time=2500):
        self.id = tg_id
        self.mode = mode
        self.affiliated_radios = set()
        self.allow_fdma = allow_fdma
        self.allow_tdma = allow_tdma
        self.hang_time = hang_time
        self.in_emergency = False

    def add_affiliated_radio(self, radio):
        self.affiliated_radios.add(radio)
        radio.affiliation.add(self.id)


class Radio:
    def __init__(self, radio_id, radio_type, is_phase2_capable=False):  # Add phase 2 capability
        self.id = radio_id
        self.type = radio_type
        self.is_phase2_capable = is_phase2_capable  # add the property
        self.in_emergency = False
        self.affiliation = set()


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
        self.end_reason = END_REASON_NORMAL
        self.is_in_hangtime = False

    def end_call(self):
        print("hi")
        # we want to log call
        # if there is a hangtime, change call status and prolong
        # if its in hangtime, then collapse call
        # if it preempted, state that it was - update end reason
        # we wannt to notify site queue of the change


class Controller:

    def __init__(self, system):
        self.talkgroups = {500: Talkgroup(500, MODE_PTT_ID, True, True, True)}


class Site:
    def __init__(self):
        self.channels = []
        self.talkgroups = {}
        self.radios = {}
        self.controller = Controller(self)
        self.site_status = STATUS_SITE_OFFLINE

        # Register system radio (for data calls, etc.)
        self.register_radio(Radio(RADIO_TYPE_SYSTEM, RADIO_TYPE_SYSTEM, True))

    def register_radio(self, radio):
        if radio.id not in self.radios:
            self.radios[radio.id] = radio
            return True
        else:
            return False

    def deregister_radio(self, radio):
        if radio.id in self.radios:
            del self.radios[radio.id]
            return True
        else:
            return False  # Radio not found

    def affiliate_radio(self, radio, talkgroup_ids):

        if radio.id not in self.radios:
            return "Radio not registered"

        radio.affiliation.clear()

        for tg_id in talkgroup_ids:
            if not self.talkgroups[tg_id].allow_fdma and not radio.phase_2_capable:
                return "Radio cannot affiliate to this talkgroup (TDMA only)"
            radio.affiliation.add(tg_id)
            self.talkgroups[tg_id].affiliated_radios.add(radio.id)
            if radio.type == RADIO_TYPE_SUBSCRIBER:
                break

        return "Radio affiliated successfully"

    def deaffiliate_radio(self, radio, talkgroup_ids):

        for tg_id in talkgroup_ids:
            if tg_id in radio.affiliated_talkgroups: radio.affiliation.remove(tg_id)
            self.talkgroups[tg_id].affiliated_radios.remove(radio.id)

        return "Radio left the talkgroup"

    def initialize_system(self):
        if self.control_channel_manager.initialize():
            self.site_status = STATUS_SITE_WIDEAREA
            print("System initialized. System status: WIDEAREA.")

    def add_channel(self, channel):
        self.channels.append(channel)
        return "Channel added successfully"

    def create_talkgroup(self, tg_id, mode, allow_fdma=True, allow_tdma=True, hang_time=2500):
        if tg_id not in self.talkgroups:
            self.talkgroups[tg_id] = Talkgroup(tg_id, mode, allow_fdma, allow_tdma, hang_time)
            print(
                f"Talkgroup {tg_id} created with mode {mode} and allow fdma {allow_fdma} and tdma {allow_tdma} and hang time {hang_time}")
        else:
            print("Talkgroup already exists.")

    def is_tdma(self, call_type, initiating_radio, talkgroup_ids=None, target_radio=None):

        _is_tdma = None
        if call_type in [CALL_TYPE_OTAR, CALL_TYPE_OTAP, CALL_TYPE_DATA, CALL_TYPE_BSI]:
            _is_tdma = False
        elif call_type == CALL_TYPE_PRIVATE:
            if not initiating_radio.is_phase2_capable or not target_radio.is_phase2_capable:
                _is_tdma = False
        elif call_type in [CALL_TYPE_VOICE, CALL_TYPE_PATCHED, CALL_TYPE_MULTI_SELECT]:
            _is_tdma = True
            for tg_id in talkgroup_ids:
                tg = self.talkgroups[tg_id]
                if any(not self.radios[r].is_phase2_capable for r in tg.affiliated_radios):
                    _is_tdma = False
                    break

        return _is_tdma

    def search_talkpath(self, call_type, is_tdma, talkgroup_ids=None, emergency=False):
        preferred_channels = []
        unpreferred_channels = []
        preempt_calls = []

        # Filter channels based on capabilities
        if call_type in [CALL_TYPE_VOICE, CALL_TYPE_PATCHED, CALL_TYPE_PRIVATE, CALL_TYPE_MULTI_SELECT,
                         CALL_TYPE_SERVICE]:
            required_capabilities = CHANNEL_CAP_TDMA if is_tdma else CHANNEL_CAP_FDMA
        elif call_type in [CALL_TYPE_OTAR, CALL_TYPE_OTAP, CALL_TYPE_DATA]:
            required_capabilities = CHANNEL_CAP_DATA
        elif call_type == CALL_TYPE_BSI:
            required_capabilities = CHANNEL_CAP_BSI

        # Filter out channels that cannot handle the call
        channels = [ch for ch in self.channels if
                    (ch.capabilities & required_capabilities) and not ch.is_control_channel]

        for ch in self.channels:
            print(f"Channels found: {ch.is_control_channel}")

        # Identify middle channels for preferred listing
        total_channels = len(channels)
        middle_start = total_channels // 3
        middle_end = 2 * total_channels // 3
        middle_indices = range(middle_start, middle_end)

        for idx, channel in enumerate(channels):
            if idx in middle_indices:
                if is_tdma:
                    if CALL_TDMA_A not in channel.calls or CALL_TDMA_B not in channel.calls:
                        preferred_channels.append(channel)
                else:  # FDMA
                    if not channel.calls:
                        preferred_channels.append(channel)
            else:
                unpreferred_channels.append(channel)

        # Check for re-use of channels with hang time
        if talkgroup_ids:
            for tg_id in talkgroup_ids:
                tg = self.talkgroups[tg_id]
                for channel in self.channels:
                    if tg_id in channel.calls and channel.calls[tg_id].call_duration < tg.hang_time:
                        if is_tdma:
                            if CALL_TDMA_A in channel.calls:
                                return channel, CALL_TDMA_A, preempt_calls
                            if CALL_TDMA_B in channel.calls:
                                return channel, CALL_TDMA_B, preempt_calls
                        else:
                            return channel, CALL_FDMA, preempt_calls

        # Assign channel from preferred list
        for channel in preferred_channels:
            if channel.status == CHANNEL_ENABLED:
                if not is_tdma and not channel.calls:
                    return channel, CALL_FDMA, preempt_calls
                elif is_tdma:
                    if CALL_TDMA_A not in channel.calls:
                        return channel, CALL_TDMA_A, preempt_calls
                    if CALL_TDMA_B not in channel.calls:
                        return channel, CALL_TDMA_B, preempt_calls

        # Assign channel from unpreferred list
        for channel in unpreferred_channels:
            if channel.status == CHANNEL_ENABLED:
                if not is_tdma and not channel.calls:
                    return channel, CALL_FDMA, preempt_calls
                elif is_tdma:
                    if CALL_TDMA_A not in channel.calls:
                        return channel, CALL_TDMA_A, preempt_calls
                    if CALL_TDMA_B not in channel.calls:
                        return channel, CALL_TDMA_B, preempt_calls

        # Preempt calls if no suitable channel is found
        for channel in unpreferred_channels:
            if channel.status == CHANNEL_ENABLED:
                for call in channel.calls.values():
                    if call.call_type in [CALL_TYPE_OTAR, CALL_TYPE_OTAP, CALL_TYPE_DATA, CALL_TYPE_BSI] or (
                            emergency and call.call_type in [CALL_TYPE_VOICE, CALL_TYPE_PATCHED]):
                        preempt_calls.append(call)
                        return channel, (CALL_TDMA_A if is_tdma and CALL_TDMA_A not in channel.calls else
                                         CALL_TDMA_B if is_tdma and CALL_TDMA_B not in channel.calls else
                                         CALL_FDMA), preempt_calls

        # Special assignment for CALL_TYPE_SERVICE
        if call_type == CALL_TYPE_SERVICE:
            for channel in self.channels:
                if channel.service == CHANNEL_SERVICE_MODE:
                    return channel, CALL_FDMA, preempt_calls

        # If no suitable channel is found, raise an exception
        raise Exception("No suitable channel found")

    def collapse_calls(self, preempt_calls):
        for call in preempt_calls:
            call.end_reason = END_REASON_PREEMPTED
            call.channel.remove_call(call.call_id)
            print(f"Call {call.call_id} has been preempted.")

    def process_call(self, call_type, initiating_radio, talkgroup_ids=None, target_radio=None):
        # Attempt to make a new call
        if call_type in [CALL_TYPE_VOICE, CALL_TYPE_PATCHED, CALL_TYPE_MULTI_SELECT, CALL_TYPE_SERVICE]:

            # Define our talkgroups, a console by default, will transmit on all talkgroups
            if not talkgroup_ids:
                if initiating_radio.type == RADIO_TYPE_SUBSCRIBER:
                    talkgroup_ids = [next(iter(initiating_radio.affiliation))]
                elif initiating_radio.type == RADIO_TYPE_CONSOLE and not talkgroup_ids:
                    talkgroup_ids = initiating_radio.affiliation

            # Check capability
            modulation = self.is_tdma(call_type, initiating_radio, talkgroup_ids, target_radio)

            print(f"initiating_radio: {initiating_radio.id} = {talkgroup_ids} == {modulation} ")

        # Search for a talkpath
        channel, slot, preempt_calls = self.search_talkpath(call_type, modulation, talkgroup_ids)

        # Output the channel/slot assigned and any calls that need to be preempted
        print(f"Channel: {channel.number}, Slot: {slot}")
        print("Preempt Calls:", [call.call_id for call in preempt_calls])

        # TODO At this point, we have our channel, but we need to ask ZC whether all sites are ready proceed
        # If not, we busy the call
        zc_proceed = True

        if not zc_proceed:
            channel, slot = None, None
            return CALL_REQUEST_BUSY

        if channel and slot:

            if preempt_calls:
                # We have channels to preempt first
                self.collapse_calls(preempt_calls)

            # Make new call
            return CALL_REQUEST_GRANT
        else:
            return CALL_REQUEST_BUSY


site = Site()

# Create Talkgroups
site.create_talkgroup(101, MODE_PTT_ID)
site.create_talkgroup(102, MODE_TRANSMISSION, True, False)
site.create_talkgroup(103, MODE_TRANSMISSION)
site.create_talkgroup(104, MODE_TRANSMISSION)
site.create_talkgroup(105, MODE_TRANSMISSION)

# Create Radios
radio1 = Radio(1, RADIO_TYPE_SUBSCRIBER, True)
radio2 = Radio(2, RADIO_TYPE_SUBSCRIBER, True)
radio3 = Radio(3, RADIO_TYPE_SUBSCRIBER, True)
radio4 = Radio(4, RADIO_TYPE_SUBSCRIBER, True)
radio5 = Radio(5, RADIO_TYPE_CONSOLE, False)

site.add_channel(Channel(1, CHANNEL_CAP_FDMA | CHANNEL_CAP_CONTROL, 867.5625, 822.5625))
site.add_channel(
    Channel(2, CHANNEL_CAP_CONTROL | CHANNEL_CAP_TDMA | CHANNEL_CAP_DATA | CHANNEL_CAP_FDMA, 867.5625, 822.5625))

print(site.register_radio(radio1))
print(site.register_radio(radio2))
print(site.register_radio(radio3))
print(site.register_radio(radio5))
print(site.affiliate_radio(radio1, [101]))
print(site.affiliate_radio(radio2, [102]))
print(site.affiliate_radio(radio3, [103]))
print(site.affiliate_radio(radio5, [101, 102, 105]))

# print(site.determine_fdma_tdma(CALL_TYPE_PRIVATE, radio1, None, radio2))
# print(site.is_tdma(CALL_TYPE_OTAP, radio1))

site.process_call(CALL_TYPE_VOICE, radio1)
site.process_call(CALL_TYPE_VOICE, radio2)
site.process_call(CALL_TYPE_VOICE, radio5)
site.process_call(CALL_TYPE_VOICE, radio3)

# system.add_channel(Channel(3, CHANNEL_CAP_CONTROL | CHANNEL_CAP_TDMA | CHANNEL_CAP_DATA | CHANNEL_CAP_FDMA, 867.5625, 822.5625))
# system.add_channel(Channel(4, CHANNEL_CAP_DATA | CHANNEL_CAP_DATA | CHANNEL_CAP_FDMA, 867.5625, 822.5625))
# system.add_channel(Channel(5, CHANNEL_CAP_DATA | CHANNEL_CAP_BSI | CHANNEL_CAP_DATA | CHANNEL_CAP_FDMA, 867.5625, 822.5625))

# site.initialize_system()

# system.control_channel_manager.process_call_request(CALL_TYPE_OTAP, radio2, None, None, 15000)
# system.control_channel_manager.process_call_request(CALL_TYPE_VOICE, radio1, [101], None, 15000)
# system.control_channel_manager.process_call_request(CALL_TYPE_VOICE, radio3, [102], None, 15000)
# system.control_channel_manager.process_call_request(CALL_TYPE_VOICE, radio4, [103], None, 15000)
# system.control_channel_manager.process_call_request(CALL_TYPE_PATCHED, radioConsole, [101, 102, 103, 104], None, 15000)
