import random
from site_constants import *
import secrets

class Call:
    def __init__(self, pending_call_id, call_type=None, initiating_radio=None, target_talkgroup=None,
                 target_radio=None, channel=None, tdma_slot=None, call_duration=None):
        self.pending_call_id = pending_call_id  # Reference to the parent call
        self.id = sequence
        self.call_type = call_type
        self.initiating_radio = initiating_radio
        self.target_talkgroup = target_talkgroup  # List of talkgroups
        self.target_radio = target_radio  # List of radios
        self.channel = channel
        self.tdma_slot = tdma_slot
        self.call_duration = call_duration
        self.call_id = random.randint(1000, 9999)
        self.end_reason = END_REASON_NORMAL
        self.is_in_hangtime = False

        print("we made a call")

    def create_site_call(self, pending_call_id, initiating_radio, target_talkgroup, channel, tdma_slot):
        new_call = Call(pending_call_id, initiating_radio=initiating_radio, target_talkgroup=target_talkgroup,
                        channel=channel, tdma_slot=tdma_slot)
        channel.calls[new_call.call_id] = new_call  # Add to channel's calls
        self.calls.append(new_call)  # Add to the site's calls list
        print(f"Call {new_call.call_id} created on site {self.id} (Parent: {pending_call_id})")
        return new_call
    def end_call(self):
        print("hi")
        # we want to log call
        # if there is a hangtime, change call status and prolong
        # if its in hangtime, then collapse call
        # if it preempted, state that it was - update end reason
        # we wannt to notify site queue of the change
