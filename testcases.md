Test Case 1: Basic Priority and Time Ordering

create
use <simulation_id>

schedule 5 1000 ptt 1 1 10 5      # Priority 5, time 1.0
schedule 3 2000 announce "High Priority 1" # Priority 3, time 2.0
schedule 5 500 ptt 2 2 20 5      # Priority 5, time 0.5
schedule 3 1000 announce "High Priority 2" # Priority 3, time 1.0
schedule 7 3000 ptt 3 3 30 5      # Priority 7, time 3.0

run a

Expected Output:

The events should be processed in this order:

Priority 5, time 0.5
Priority 5, time 1.0
Priority 3, time 1.0
Priority 3, time 2.0
Priority 7, time 3.0


Test Case 2: System Events (Priority 0)

schedule 5 1000 ptt 1 1 10 5      # Priority 5, time 1.0
schedule 0 500 announcement "System Message" # Priority 0, time 0.5
schedule 3 2000 announce "High Priority 1" # Priority 3, time 2.0

Expected Output:

The "System Message" (priority 0) should be processed first, even though it's scheduled for a later time than the first PTT command:

Priority 0, time 0.5
Priority 5, time 1.0
Priority 3, time 2.0

Test Case 3: Multiple Events at the Same Time and Priority

schedule 5 1000 ptt 1 1 10 5      # Priority 5, time 1.0
schedule 5 1000 announce "Same Time 1" # Priority 5, time 1.0
schedule 5 1000 ptt 2 2 20 5      # Priority 5, time 1.0

Expected Output:

The events should be processed in the order they were scheduled:

Priority 5, time 1.0 (ptt 1)
Priority 5, time 1.0 (announce "Same Time 1")
Priority 5, time 1.0 (ptt 2)