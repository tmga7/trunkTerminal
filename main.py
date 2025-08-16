from simulation import MainProgram
import time

if __name__ == "__main__":
    main_program = MainProgram()

    main_program.create_system_instance("newconfig.yaml")

    time.sleep(50)
    main_program.stop_system_instances()
