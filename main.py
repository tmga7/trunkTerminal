from simulation import MainProgram
import time

if __name__ == "__main__":
    main_program = MainProgram()

    main_program.create_system_instance("newconfig.yaml")

    # Create system instances
    # for i in range(3):
    #    main_program.create_system_instance(i)

    # Add events to the first system instance for testing
    #system_instance = main_program.system_instances[0]
    #system_instance.add_event(5, "U_REG_REQ")  # Event with priority 1 and a delay of 2.55 seconds
    # system_instance.add_event(2, "Event 2", 1.25)  # Event with priority 2 and a delay of 1.25 seconds
    # system_instance.add_event(1, "Emergency Event", 0.75)  # Emergency event with immediate processing and reprocess
    # system_instance.add_event(0, "End Call", 5.0)  # Event to end a call and free the channel after 5 seconds

    # Add a busy command that will be processed when the channel is free
    #system_instance.busy_queue.put((1, time.time(), "Busy Command", {'force_process': True}))

    # Run for a short period and then stop
    #time.sleep(10)
    main_program.stop_system_instances()
