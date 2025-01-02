from site_constants import *
from core_radio import Radio
from site_channel import Channel
from core_talkgroup import Talkgroup
from site_call import Call
import secrets

class Site:

    def __init__(self, core):
        self.id = None
        self.status = STATUS_SITE_OFFLINE
        self.core = core
        self.channels = []
        self.calls = [] # We keep active calls here
        self.talkgroups = set()
        self.radios = set()


        # Register system radio (for data calls, etc.)
        # self.radios[RADIO_TYPE_SYSTEM] = Radio(self, RADIO_TYPE_SYSTEM, RADIO_TYPE_SYSTEM, True)

    def add_talkgroup_id(self, talkgroup_id):
        self.talkgroup_ids.add(talkgroup_id)

    def remove_talkgroup_id(self, talkgroup_id):
        self.talkgroup_ids.discard(talkgroup_id)

    # Update an existing radio
    def update_radio(self, radio_id, radio_type=None, is_phase2_capable=None, in_emergency=None):
        if radio_id not in self.radios:
            print(f"Radio {radio_id} does not exist.")
            return
        radio = self.radios[radio_id]
        if radio_type is not None:
            radio.type = radio_type
        if is_phase2_capable is not None:
            radio.is_phase2_capable = is_phase2_capable
        if in_emergency is not None:
            radio.in_emergency = in_emergency
        print(f"Radio {radio_id} updated.")

    # Delete an existing radio
    def delete_radio(self, radio_id):
        if radio_id not in self.radios:
            print(f"Radio {radio_id} does not exist.")
            return
        del self.radios[radio_id]
        print(f"Radio {radio_id} deleted.")

    def move_to_site(self, new_site, radio_id):
        if self.site and radio_id in self.site.radios:
            self.site.remove_radio(radio_id)
            self.site = new_site
            self.site.radios[radio_id] = self

    def register_radio(self, radio):

        if radio.id not in self.radios:
            self.radios[radio.id] = radio
            return True
        else:
            return False

    def unit_registration(self, radio):
        # TODO is this radio allowed on this site?
        self.radios.add(radio.id)
        radio.site = self
        print(f"{radio.id} registered successfully REG_ACCEPT")
        return True

    def unit_deregistration(self, radio):
        if radio.id in self.radios:
            del self.radios[radio.id]
            radio.site = None
            print(f"{radio.id} deregistered successfully")

    def group_affiliation_query(self):
        print("Group affiliation query GRP_AFF. _Q")

    def deaffiliate(self, radio, talkgroup_ids):

        print(f"trying to deaffliate -> {talkgroup_ids}")

        for tg_id in talkgroup_ids:
            if tg_id in self.talkgroups:
                radio.affiliation.remove(tg_id)
                self.talkgroups.remove(radio.id)
                print(f"{radio.id} left {tg_id} successfully")

    def group_affiliation_request(self, radio, talkgroup_ids):

        if radio.id not in self.radios:
            return "Radio not registered"

        # TODO we need to our validation on whether unit can affiliate, we assume AFF_ACCEPT
        for tg_id in talkgroup_ids:
            if not self.core.talkgroups[tg_id].allow_fdma and not radio.phase_2_capable:
                return "Radio cannot affiliate to this talkgroup (TDMA only) AFF_DENY"

        # We remove our radio from master talkgroup list, and radio's affiliation
        print(f"Pre-ttalkgroup status: {list(self.core.talkgroups[tg_id].affiliations)}")

        for tg_id in talkgroup_ids:
            self.core.talkgroups[tg_id].affiliations.pop(radio.id, None)
            radio.affiliation.discard(tg_id)

        # Now we add our talkgroups
        for tg_id in talkgroup_ids:
            self.core.talkgroups[tg_id].affiliations[radio.id] = self.id
            radio.affiliation.add(tg_id)

        print(f"AFF_ACCEPT on {tg_id} for {radio.id}")

        return True

    # Create a new channel
    def create_channel(self, channel_number, capabilities, freq_tx=000.00000, freq_rx=000.00000):
        if any(ch.number == channel_number for ch in self.channels):
            print(f"Channel {channel_number} already exists.")
            return
        new_channel = Channel(channel_number, capabilities, freq_tx, freq_rx)
        self.channels.append(new_channel)
        print(f"Channel {channel_number} created.")

    # Update an existing channel
    def update_channel(self, channel_number, capabilities=None, freq_tx=None, freq_rx=None, status=None):
        channel = next((ch for ch in self.channels if ch.number == channel_number), None)
        if capabilities is not None:
            channel.capabilities = capabilities
        if freq_tx is not None:
            channel.freq_tx = freq_tx
        if freq_rx is not None:
            channel.freq_rx = freq_rx
        if status is not None:
            channel.status = status
        print(f"Channel {channel_number} updated.")

    def initialize_system(self):
        control_channels = [ch for ch in self.channels if ch.has_capability(CHANNEL_CAP_CONTROL)]
        print(f"Control channels that we can use: {control_channels}")

        # Ensure there are control channels before proceeding
        if control_channels:
            # Set the control channel to the one with the smallest number
            min(control_channels, key=lambda ch: ch.number).is_control_channel = True
            self.status = STATUS_SITE_WIDEAREA
            print("System initialized. System status: WIDEAREA.")
        else:
            print("No control channels found.")

        # Debug: Print control channel numbers
        print("Control channel numbers:")
        for ch in self.channels:
            print(f"{ch.is_control_channel} = {ch.number})")

    def add_channel(self, channel):
        self.channels.append(channel)
        return "Channel added successfully"

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
            print(f"Channels found: {ch.number}")

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

    def create_call(self, call_type=None, initiating_radio=None, talkgroup_id=None):

        call_sequence = secrets.token_hex(8)

        print(call_sequence)

        self.calls.append(Call(call_sequence))

        print(f"Call {call_sequence} created on {self.id}.")


    def isp_group_voice_service_request(self, initiating_radio, talkgroup_ids=None):

        # Confirm talkgroup
        # A console by default, will transmit on all talkgroups if not specified
        if not talkgroup_ids:
            if initiating_radio.type == RADIO_TYPE_SUBSCRIBER:
                talkgroup_ids = [next(iter(initiating_radio.affiliation))]
            elif initiating_radio.type == RADIO_TYPE_CONSOLE and not talkgroup_ids:
                talkgroup_ids = initiating_radio.affiliation

        # Check capability
        #modulation = self.is_tdma(call_type, initiating_radio, talkgroup_ids, target_radio)


        print("GRP V REQ")

    def isp_unit_to_unit_voice_service_request(self, emergency, initiating_radio, talkgroup_ids=None, target_radio=None):
        print("UU_V_REQ)")

    def isp_unit_to_unit_voice_answer_response(self, emergency, initiating_radio, talkgroup_ids=None, target_radio=None):
        print("UU ANS RSP)")

    def osp_group_voice_channel_grant(self):
        print("GRP V CH GRANT")

    def osp_group_voice_channel_grant_update(self):
        # late entry, updates only, visual interface
        print("G R P V C H GRANT UPDT")

    def osp_unit_to_unit_voice_channel_grant(self):
        print("U U V C H GRANT )")

    def isp_unit_to_unit_voice_answer_request(self):
        #This is the packet to indicate to the target unit that a unit to unit call has been requested involving this target unit.
        print("UU ANS_REQ")

