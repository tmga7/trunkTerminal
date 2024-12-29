import core
import cli

if __name__ == "__main__":
    config = core.load_config()
    system = core.System(config)

    # Example usage: Access system information
    print(f"System ID: {system.id}")
    print(f"System Alias: {system.alias}")
    print("-" * 20)

    # Example usage (optional): Access specific elements
    for rfss_id in system.rfss:
        print(f"RFSS ID: {rfss_id}")
        rfss = system.rfss[rfss_id]  # Get specific RFSS object

        # Access sites within the RFSS
        for site_id in rfss.sites:
            print(f"\tSite ID: {site_id}")

    # CLI Start
    processor = cli.CommandProcessor(system)
    while True:
        user_input = input("Enter command: ")
        processor.execute_command(user_input)

# You can further access channels and subscribers using methods within their respective classes (Talkgroup, Subscriber)
