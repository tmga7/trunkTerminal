class CommandProcessor:
    def __init__(self, system):
        self.system = system

    def execute_command(self, command_line):
        command_parts = command_line.split()
        if len(command_parts) == 0:
            print("No command entered")
            return

        command_name = command_parts[0].upper()
        if command_name == "EXIT":
            exit(0)
        if command_name == "START":
            self.start_command()
        if command_name == "P":
            self.process_print_command(command_parts[1:])
        elif command_name == "RADIO":
            self.process_radio_command(command_parts[1:])
        elif command_name == "SITE":
            self.site_status_command(command_parts[1:])
        else:
            print(f"Unknown command: {command_name}")

    def process_print_command(self, args):
        if len(args) < 1:
            print("No subcommand entered for PRINT")
            return

        command = args[0].upper()
        if command == "ALL":
            print(repr(self.system))  # Print the entire system representation
        elif command == "TALKGROUPS":
            print("Talkgroups:")
            #for tg in self.system.talkgroups.values():
            #    tg.print_()
        elif command == "RFSS":
            print("Talkgroups:")
        elif command == "STATUS":
            if len(args) < 3:
                print("RADIO REGISTER command requires Radio ID and Site ID")
            else:
                radio_id = args[0]
                site_id = args[2]
                print(f"Radio {radio_id} registered to site {site_id}")
        else:
            print(f"Unknown RADIO subcommand: {command}")

    def start_command(self):
        print("System started")

    def process_radio_command(self, args):
        if len(args) < 1:
            print("No subcommand entered for RADIO")
            return

        radio_command = args[0].upper()
        if radio_command == "REGISTER":
            if len(args) < 3:
                print("RADIO REGISTER command requires Radio ID and Site ID")
            else:
                radio_id = args[0]
                site_id = args[2]
                print(f"Radio {radio_id} registered to site {site_id}")
        elif radio_command == "STATUS":
            print("Radio status requested")
        else:
            print(f"Unknown RADIO subcommand: {radio_command}")

    def site_status_command(self, args):
        if len(args) < 2:
            print("SITE STATUS command requires RFSS ID and Site ID")
        else:
            rfss_id = args[0]
            site_id = args[1]
            print(f"Status requested for site {site_id} in RFSS {rfss_id}")
