import heapq
import asyncio
import time
import re
from collections import deque
import datetime
import random
from prototype_core import RadioSystem


class EventQueue:
    def __init__(self, name):
        self.name = name
        self.queue = []

    def push(self, item):
        heapq.heappush(self.queue, item)
        print(f"{self.name} Queue: Added {item}")

    def pop(self):
        if self.queue:
            item = heapq.heappop(self.queue)
            print(f"{self.name} Queue: Removed {item}")
            return item
        return None

    def peek(self):
        if self.queue:
            return self.queue[0]
        return None

    def __len__(self):
        return len(self.queue)

    def __str__(self):
        return f"{self.name} Queue: {self.queue}"

    def get_queue_status(self):
        status = []
        for scheduled_time, submission_time, command, *args in self.queue:
            scheduled_time_readable = datetime.datetime.fromtimestamp(scheduled_time).strftime('%Y-%m-%d %H:%M:%S')
            submission_time_readable = datetime.datetime.fromtimestamp(submission_time).strftime('%Y-%m-%d %H:%M:%S')
            status.append(
                {"scheduled": scheduled_time_readable, "submitted": submission_time_readable, "command": command,
                 "args": args})
        return status


class BlockingQueue:
    def __init__(self, name):
        self.name = name
        self.queue = deque()

    def push(self, item):
        self.queue.append(item)
        print(f"{self.name} Queue: Added {item}")

    def pop(self):
        if self.queue:
            item = self.queue.popleft()
            print(f"{self.name} Queue: Removed {item}")
            return item
        return None

    def peek(self):
        if self.queue:
            return self.queue[0]
        return None

    def __len__(self):
        return len(self.queue)

    def __str__(self):
        return f"{self.name} Queue: {list(self.queue)}"

    def get_queue_status(self):
        status = []
        for unblock_time, priority, submission_time, command, *args in self.queue:
            unblock_time_readable = datetime.datetime.fromtimestamp(unblock_time).strftime('%Y-%m-%d %H:%M:%S')
            status.append({"unblock_time": unblock_time_readable, "priority": priority, "submitted": submission_time,
                           "command": command, "args": args})
        return status


async def simulate_radio_system(radio_system, command, *args):
    """Simulates interaction with the radio system."""
    await asyncio.sleep(0.5)  # Simulate processing time
    if command == "PTT":
        if not radio_system.available_channels:
            print("Radio System: All channels busy.")
            return "busy"  # Indicate busy
        channel = radio_system.available_channels.pop(0)
        radio_system.in_use_channels[channel] = time.time() + 2
        print(f"Radio System: PTT request granted on channel {channel}.")
        return "granted"
    elif command == "OTHER_COMMAND":
        # Handle other commands
        return "granted"  # default granted
    else:
        print(f"Radio System: Unknown command {command}")
        return "denied"


def assign_system_priority(command, args):
    if "EMERGENCY" in args:
        return 0
    elif "PRIORITY" in args:
        return 1
    else:
        return random.randint(1, 3)


async def process_user_queue(user_queue, system_queue):
    while True:
        await asyncio.sleep(0.1)
        if user_queue.peek() and user_queue.peek()[0] <= time.time():
            _, submission_time, command, *args = user_queue.pop()
            system_priority = assign_system_priority(command, args)
            system_queue.push((system_priority, submission_time, command, *args))
            print(f"Moved {command} to system queue with priority {system_priority}")


async def process_system_queue(system_queue, blocking_queue, radio_system):
    while True:
        await asyncio.sleep(0.1)
        await radio_system.check_channels()
        if system_queue.peek():
            priority, submission_time, command, *args = system_queue.pop()
            print(
                f"Processing in system queue: {command} with args {args}, priority {priority}, submitted at {submission_time}")
            response = await simulate_radio_system(radio_system, command, *args)
            if response == "busy":
                blocking_queue.push((time.time() + 2, priority, submission_time, command, *args))
                print(f"Moved {command} to blocking queue")
            elif response == "denied":
                print(f"{command} was denied by the radio system.")
            elif response == "granted":
                print(f"{command} was granted by the radio system.")


async def process_blocking_queue(system_queue, blocking_queue):
    while True:
        await asyncio.sleep(0.1)
        if blocking_queue.peek() and blocking_queue.peek()[0] <= time.time():
            _, original_priority, original_submission_time, command, *args = blocking_queue.pop()
            system_priority = assign_system_priority(command, args)
            system_queue.push((system_priority, original_submission_time, command, *args))
            print(f"Moved {command} back to system queue with re-evaluated priority {system_priority}")


async def handle_non_queue_command(user_queue, system_queue, blocking_queue, command, *args):
    if command.upper() == "HELLO":
        print("Hello to you too!")
    elif command.upper() == "VERSION":
        print("Radio System Simulator v1.0")
    elif command.upper() == "QUEUE":
        if args and args[0].upper() == "STATUS":
            print("User Queue:")
            for item in user_queue.get_queue_status():
                print(item)
            print("\nSystem Queue:")
            for item in system_queue.get_queue_status():
                print(item)
            print("\nBlocking Queue:")
            for item in blocking_queue.get_queue_status():
                print(item)
        else:
            print("Invalid QUEUE command. Use QUEUE STATUS")
    else:
        print(f"Unknown command: {command}")


async def main():
    radio_system = RadioSystem()
    user_queue = EventQueue("User")
    system_queue = EventQueue("System")
    blocking_queue = BlockingQueue("Blocking")

    asyncio.create_task(process_user_queue(user_queue, system_queue))
    asyncio.create_task(process_system_queue(system_queue, blocking_queue, radio_system))
    asyncio.create_task(process_blocking_queue(system_queue, blocking_queue))

    while True:
        command_input = await asyncio.get_running_loop().run_in_executor(None, input, "> ")
        command_parts = command_input.split()
        if not command_parts:
            continue
        command = command_parts[0]
        args = command_parts[1:]

        if re.match(r"(\d+(?:\.\d+)?)\s+(\w+)", command_input):
            match = re.match(r"(\d+(?:\.\d+)?)\s+(\w+)\s*(.*)", command_input)
            if match:
                delay, command, args_str = match.groups()
                try:
                    delay = float(delay)
                    scheduled_time = time.time() if delay == 0 else time.time() + delay
                    args = args_str.split()
                    user_queue.push((scheduled_time, time.time(), command, *args))
                except ValueError:
                    print("Invalid delay value.")
        elif command.upper() == "EXIT":
            break
        else:
            await handle_non_queue_command(user_queue, system_queue, blocking_queue, command, *args)


if __name__ == "__main__":
    asyncio.run(main())
