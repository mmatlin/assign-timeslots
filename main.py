import csv
import itertools
import time
import random

# TODO: Remove column names and value constants from functions (e.g. "RUID", "Available", "Yes")

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
INTERVAL_BOUNDS = ("8am", "9am", "10am", "11am", "12pm", "1pm", "2pm", "3pm", "4pm")
TIME_SLOTS = tuple(
    f"{day} {times}"
    for day in DAY_NAMES
    for times in (f"{start} - {end}" for start, end in zip(INTERVAL_BOUNDS, INTERVAL_BOUNDS[1:]))
)


def create_roster(csv_filename):
    with open(csv_filename, newline="") as csvfile:
        # headers_line_num = 3
        # csvfile.readlines(headers_line_num)
        lines_to_skip = 2
        for _ in range(lines_to_skip):
            next(csvfile)

        group_leader_column_name = "Were you confirmed to be a Discussion Group Facilitator?"
        roster = dict()
        leader_ids = set()
        student_ids = set()

        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            if not row["RUID"]:
                continue
            availability = {
                column_name: value == "Available"
                for column_name, value in row.items()
                if column_name in TIME_SLOTS
            }
            if row[group_leader_column_name] == "Yes":
                leader_ids.add(row["RUID"])
            else:
                student_ids.add(row["RUID"])

            roster[row["RUID"]] = {
                "first": row["First Name"],
                "last": row["Last Name"],
                "email": row["Preferred Email"],
                "id": row["RUID"],
                "year": row["School Year"],
                "major": row["Major"],
                "leader": row[group_leader_column_name] == "Yes",
                "availability": availability,
            }
    return roster, leader_ids, student_ids


def create_time_slot_buckets(roster, leader_ids, student_ids):
    # Initialize time slots
    time_slot_buckets = dict()
    for slot in TIME_SLOTS:
        time_slot_buckets[slot] = {"leader_ids": set(), "student_ids": set()}

    # Add availability of all leaders first
    for leader_id in leader_ids:
        for slot, available in roster[leader_id]["availability"].items():
            if available:
                time_slot_buckets[slot]["leader_ids"].add(leader_id)

    # Add availability of students
    for student_id in student_ids:
        for slot, available in roster[student_id]["availability"].items():
            if available:
                time_slot_buckets[slot]["student_ids"].add(student_id)

    return time_slot_buckets


def remove_unavailable_time_slots(time_slot_buckets, leader_ids, student_ids):
    # Remove time slots without any leaders or students, keep track of leaders and students in time slots
    available_leader_ids = set()
    available_student_ids = set()
    all_time_slots = [key for key in time_slot_buckets.keys()]
    for slot in all_time_slots:
        if not time_slot_buckets[slot]["leader_ids"] or not time_slot_buckets[slot]["student_ids"]:
            del time_slot_buckets[slot]
        else:
            available_leader_ids.update(time_slot_buckets[slot]["leader_ids"])
            available_student_ids.update(time_slot_buckets[slot]["student_ids"])

    # Identify leaders or students who are unavailable for every time slot with at least one member of opposite group
    # TODO: Figure out how we want to handle these cases
    unavailable_leader_ids = leader_ids - available_leader_ids
    if unavailable_leader_ids:
        # At least one leader exists who does not fit into any time slot
        leader_ids = available_leader_ids

    unavailable_student_ids = student_ids - available_student_ids
    if unavailable_student_ids:
        # At least one student exists who does not fit into any time slot
        student_ids = available_student_ids

    return time_slot_buckets, leader_ids, student_ids, unavailable_leader_ids, unavailable_student_ids


def create_groups(time_slot_buckets, roster, leader_ids, student_ids):
    """
    —All leaders and students must be scheduled for one (1) time slot which they are available for
    —No two leaders can be scheduled for the same time slot
    —Increase maximum membership size difference between groups after n seconds until a solution is found
    """
    attempt_interval = 10
    max_members_diff = 0
    while True:
        starting_time = time.time()
        while time.time() - starting_time < attempt_interval:
            schedule = {slot: {"leader_ids": set(), "student_ids": set()} for slot in time_slot_buckets.keys()}
            
        max_members_diff += 1


def find_group_leader_options(time_slot_buckets, leader_ids):
    for slot in time_slot_buckets:
        time_slot_buckets[slot]["curr_index"] = 0

    schedule = dict()
    filling_leader_ids = set()
    slots = itertools.cycle(time_slot_buckets.keys())

    while True:
        slot = next(slots)
        curr_index = time_slot_buckets[slot]["curr_index"]
        curr_leader_id = time_slot_buckets[slot][leader_ids][curr_index]
        while curr_index < len(time_slot_buckets[slot][leader_ids]):
            if curr_leader_id not in filling_leader_ids:
                filling_leader_ids.append(time_slot_buckets[slot][leader_ids][curr_index])
                schedule[slot] = curr_leader_id
                time_slot_buckets[slot]["curr_index"] += 1
            else:
                time_slot_buckets[slot]["curr_index"] += 1
            if filling_leader_ids == leader_ids:
                yield schedule
                schedule = dict()
                filling_leader_ids = set()

def is_valid_schedule(schedule, availability_buckets):
    people_already_encountered = set()
    for slot, data in schedule.items():
        # Check that there are no instances of students being scheduled with a non-1 amount of leaders
        if len(data["leader_ids"]) != 1 and len(data["student_ids"]):
            return False
        # Check that there are no instances of a leader being scheduled with no students
        elif len(data["leader_ids"]) == 1 and not len(data["student_ids"]):
            return False
        # Check that no person is scheduled twice
        if any([person in people_already_encountered for person in (data["leader_ids"] + data["student_ids"])]):
            return False
        # Check that no student is scheduled for when they are unavailable
        if any([student not in availability_buckets[slot]["student_ids"]]):
            return False
        # Check that no leader is scheduled for when they are unavailable
        if any([leader not in availability_buckets[slot]["leader_ids"]]):
            return False
        

def main():
    csv_filename = "real.csv"
    # roster: Keys are IDs, Values are dicts containing all the information about individuals (both leaders & students)
    # leader_ids: set of IDs of leaders
    # student_ids: set of IDs of students
    roster, leader_ids, student_ids = create_roster(csv_filename)
    # time_slot_buckets:
    #   - Keys are Time Slot names,
    #   - Values are dicts containing available leaders and students for the given time slot
    time_slot_buckets = create_time_slot_buckets(roster, leader_ids, student_ids)
    time_slot_buckets, leader_ids, student_ids, unavailable_leader_ids, unavailable_student_ids = remove_unavailable_time_slots(time_slot_buckets, leader_ids, student_ids)
    if unavailable_leader_ids:
        print("Leaders who are not available at any time that students are available:")
        for unavailable_leader_id in unavailable_leader_ids:
            print(f"{roster[unavailable_leader_id]['first']} {roster[unavailable_leader_id]['last']} (RUID: {unavailable_leader_id})")
    if unavailable_student_ids:
        print("Students who are not available at any time that students are available:")
        for unavailable_student_id in unavailable_student_ids:
            print(f"{roster[unavailable_student_id]['first']} {roster[unavailable_student_id]['last']} (RUID: {unavailable_student_id})")
    pass
    # print(f"Leaders who are not available at any time that students are available:\n{"\n".join([
    #     f'{roster[unavailable_leader_id]["""first"""]} {roster[unavailable_leader_id]["""last"""]} (RUID: {unavailable_leader_id})'
    #     for unavailable_leader_id in unavailable_leader_ids
    #     ])}")


if __name__ == "__main__":
    main()
