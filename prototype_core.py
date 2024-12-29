import asyncio
import time

class RadioSystem:
    def __init__(self, num_channels=3):
        self.num_channels = num_channels
        self.available_channels = list(range(1, num_channels + 1))
        self.in_use_channels = {}

    async def ptt(self, *args):
        await asyncio.sleep(0.5)
        if "BLOCK" in args:
            print("Radio System: PTT request blocked.")
            return False
        if not self.available_channels:
            print("Radio System: All channels busy, PTT request blocked.")
            return False
        channel = self.available_channels.pop(0)
        self.in_use_channels[channel] = time.time() + 10
        print(f"Radio System: PTT request succeeded on channel {channel}.")
        return True

    async def check_channels(self):
        channels_to_release = []
        for channel, release_time in self.in_use_channels.items():
            if time.time() > release_time:
                self.available_channels.append(channel)
                channels_to_release.append(channel)
        for channel in channels_to_release:
            del self.in_use_channels[channel]
            print(f"Channel {channel} has been released")

    async def other_command(self, *args):
        return True