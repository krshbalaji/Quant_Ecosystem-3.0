import datetime


class Scheduler:

    def __init__(self):
        self.blocks = [
            ("07:30", "08:30", "HEALTH_CHECK"),
            ("08:30", "09:15", "GLOBAL_INTELLIGENCE"),
            ("09:15", "15:30", "LIVE_MARKET"),
            ("15:30", "23:59", "REPORTING"),
        ]

    def start_day(self):
        now = datetime.datetime.now()
        print("Scheduler active:", now)
        for start, end, phase in self.blocks:
            print(f"{start} -> {end}: {phase}")

    def current_phase(self, now=None):
        now = now or datetime.datetime.now()
        hhmm = now.strftime("%H:%M")

        for start, end, phase in self.blocks:
            if start <= hhmm <= end:
                return phase

        return "OFF_HOURS"
