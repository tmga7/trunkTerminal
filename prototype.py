import heapq
import asyncio
import time
import re
from collections import deque


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


# Blocking Queue now uses deque
class BlockingQueue:
    def __init__(self, name):
        self.name = name
        self.queue = deque()

    def push(self, item):
        self.queue.append(item)
        print(f"{self.name} Queue: Added {item}")

    def pop(self):
        if self.queue:
            item = self.queue.popleft()  # pop from the left
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
        return f"{self.name} Queue: {list(self.queue)}"  # convert to list for printing

def assign_system_priority(command, args):
    """Assigns a system priority based on command and arguments."""
    if "EMERGENCY" in args:
        return 0  # Highest priority
    elif "PRIORITY" in args:
        return 1  # Preemptive priority
    else:
        return 2  # Normal priority

async def process_user_queue(user_queue, system_queue):
    while True:
        await asyncio.sleep(0.1)
        if user_queue.peek() and user_queue.peek()[0] <= time.time():
            _, submission_time, command, *args = user_queue.pop()
            system_priority = assign_system_priority(command, args)
            system_queue.push((system_priority, submission_time, command, *args)) #use submission time for FCFS
            print(f"Moved {command} to system queue with priority {system_priority}")


async def process_system_queue(system_queue, blocking_queue):
    while True:
        await asyncio.sleep(0.1)
        if system_queue.peek():
            priority, submission_time, command, *args = system_queue.pop()
            print(
                f"Processing in system queue: {command} with args {args}, priority {priority}, submitted at {submission_time}")
            if command == "BLOCK":
                blocking_queue.push((time.time() + 2, priority, submission_time, command,
                                     *args))  # store submission time in blocking queue
                print(f"Moved {command} to blocking queue")
            else:
                await asyncio.sleep(1)
                print(f"Finished processing: {command}")


async def process_blocking_queue(system_queue, blocking_queue):
    while True:
        await asyncio.sleep(0.1)
        if blocking_queue.peek() and blocking_queue.peek()[0] <= time.time():
            _, original_priority, original_submission_time, command, *args = blocking_queue.pop()  # get original priority and submission time
            system_priority = assign_system_priority(command, args)  # re-evaluate priority
            system_queue.push((system_priority, original_submission_time, command, *args))  # push back to system queue
            print(f"Moved {command} back to system queue with re-evaluated priority {system_priority}")


async def main():
    user_queue = EventQueue("User")
    system_queue = EventQueue("System")
    blocking_queue = BlockingQueue("Blocking")  # Use the new class

    asyncio.create_task(process_user_queue(user_queue, system_queue))
    asyncio.create_task(process_system_queue(system_queue, blocking_queue))
    asyncio.create_task(process_blocking_queue(system_queue, blocking_queue))

    while True:
        command_input = await asyncio.get_running_loop().run_in_executor(None, input, "> ")
        match = re.match(r"(\d+(?:\.\d+)?)\s+(\w+)\s*(.*)", command_input)

        if match:
            delay, command, args_str = match.groups()
            try:
                delay = float(delay)
                args = args_str.split()
                user_queue.push((time.time() + delay, time.time(), command, *args))
            except ValueError:
                print("Invalid delay value.")
        elif command_input.lower() == 'exit':
            break
        else:
            print("Invalid command format. Use <delay> <command> <arguments>")


if __name__ == "__main__":
    asyncio.run(main())