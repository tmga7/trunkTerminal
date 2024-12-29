class Subscriber:
    def __init__(self, id, alias, hardware, phase2=False):
        self.id = id
        self.alias = alias
        self.hardware = hardware
        self.phase2 = phase2  # Optional parameter with default False

    def __repr__(self):
        return f"Subscriber(id={self.id}, alias='{self.alias}', hardware='{self.hardware}', phase2={self.phase2})\r\n"

