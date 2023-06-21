#!/bin/python3
import asyncio
import datetime
import json
from pathlib import Path
import random


STAT_DIR = Path(__file__).resolve().parent.parent.joinpath("stat")


class Stat:
    def __init__(self) -> None:
        self.dayly_stat = {}
        self.monthly_stat = {}

    def register_action(self, event):
        self.dayly_stat[event] = 1 + self.dayly_stat.get(event, 0)
        self.monthly_stat[event] = 1 + self.monthly_stat.get(event, 0)


STAT = Stat()


async def dump_statistics():
    day = str(datetime.date.today())
    month = "-".join(day.split("-")[0:2])

    print(month, day)

    day_file = STAT_DIR.joinpath(day + ".json")
    month_file = STAT_DIR.joinpath(month + ".json")

    if day_file.exists():
        with open(day_file, "r") as f:
            STAT.dayly_stat = json.load(f)

    if month_file.exists():
        with open(month_file, "r") as f:
            STAT.monthly_stat = json.load(f)

    while True:
        with open(day_file, "w") as f:
            json.dump(STAT.dayly_stat, f)

        with open(month_file, "w") as f:
            json.dump(STAT.monthly_stat, f)

        new_day = str(datetime.date.today())
        new_month = "-".join(day.split("-")[0:2])

        if day != new_day:
            STAT.dayly_stat = {}

        if month != new_month:
            STAT.dayly_stat = {}

        day_file = STAT_DIR.joinpath(new_day + ".json")
        month_file = STAT_DIR.joinpath(new_month + ".json")

        await asyncio.sleep(300)


async def event_immitator():
    events = ["gsadg", "fjeg", "gjir", "jbgiore"]
    for i in range(300):
        event = random.choice(events)
        STAT.register_action(event)

        await asyncio.sleep(1)

    raise StopIteration()


async def run_tasks():
    await asyncio.gather(dump_statistics(), event_immitator())


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_tasks())
    except (StopIteration, KeyboardInterrupt):
        exit(0)
