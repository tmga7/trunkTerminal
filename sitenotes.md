I. System Architecture:

Channels:
Control Channels (Primary & Secondary): Dedicated channels for system information and call setup. Properties: Frequency, Type (Primary Control, Secondary Control).
Voice Channels: Channels used for actual voice and data transmissions. Properties: Frequency, Type (FDMA, TDMA), Current Usage (None, Voice, Data, BSI), Assigned Talk Group, Assigned Radio (if applicable), Time Slot (for TDMA).
Talk Groups: Represent groups of users. Properties: ID, Mode (PTT-ID, Transmission), Current Call Status (Idle, Active).
Radios (Subscribers & Consoles): Represent individual radios. Properties: Type (Subscriber, Console).
System Status: Tracks overall system activity and resource usage.
II. Call Types:

Voice Call: Standard voice communication between radios within a talk group. Arguments: Talk Group ID, Call Duration.
Data Call: Transmission of data between radios. Arguments: Talk Group ID, Data Payload, Data Call Type (e.g., OTAP/OTAR).
BSI (Base Station Identifier): Transmission of the station's identifier. Triggered periodically or on system startup.
Console Preemption: A special call type initiated by a console to interrupt an existing call. Arguments: Target Talk Group ID, Preemption Reason.
III. Call Flow:

Call Request: A radio initiates a call by sending a request to the primary control channel. The request includes the call type and arguments (e.g., talk group ID).
Control Channel Processing: The control channel checks the availability of the requested talk group and resources.
Resource Allocation: The system uses one of the following strategies:
Rollover: Assigns the next available resource in a circular fashion.
Random: Assigns a random available resource.
Balanced: Prioritizes center channels to minimize fragmentation.
Channel Assignment: The control channel sends a channel assignment message to the requesting radio (and any other radios in the talk group).
Call Setup: Radios tune to the assigned voice channel and begin transmission.
Call Termination:
Transmission Mode: The channel is released immediately after the transmission ends.
PTT-ID Mode: A hang timer keeps the channel assigned for a short period.
Console Preemption: If a console initiates a preemption, the control channel sends a preemption message to the affected radios, interrupting the existing call and assigning the console to the talk group.
IV. Error Handling:

Talk Group Busy: If the requested talk group is in use, the control channel sends a "Talk Group Busy" message with a reason code (e.g., "In Use by Other Call," "Preempted by Console").
No Channels Available: If no voice channels are available, the control channel sends a "No Channels Available" message.
V. Features:

Console Preemption: Allows consoles to interrupt existing calls.
PTT-ID Hang Time: Keeps channels assigned for a short period after transmissions in PTT-ID mode.
Resource Allocation Strategies: Implements rollover, random, and balanced allocation.
BSI Transmission: Simulates periodic or on-demand BSI transmissions.
Data Calls (including OTAP/OTAR simulation): Simulates data transfers, including longer OTAP/OTAR requests.
Encryption (Visual Representation): Includes a placeholder for CKR (Common Key Reference) to represent encryption visually, even if the actual encryption process isn't simulated.
CLI Interface: Uses a command-line interface for user interaction.
VI. Data Structures (Python Recommendations):

Channel: Dictionary or class with properties like frequency, type, status, assigned_talkgroup, assigned_radio, time_slot.
Talk Group: Dictionary or class with properties like id, mode, status.
Radio: Dictionary or class with properties like type.
System: A main object or collection of objects that manages channels, talk groups, and radios.
VII. CLI Commands (Examples):

make_call <radio_type> <talkgroup_id> <call_duration>
preempt_call <talkgroup_id> <reason>
send_data <talkgroup_id> <data_payload> <data_call_type>
system_status (displays current system usage)