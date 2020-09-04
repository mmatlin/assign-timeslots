import csv
import random
import time

# TODO: Remove column names and value constants from functions (e.g. "RUID", "Available", "Yes")

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
INTERVAL_BOUNDS = ("8am", "9am", "10am", "11am", "12pm", "1pm", "2pm", "3pm", "4pm")
TIME_SLOTS = tuple(
    f"{day} {times}"
    for day in DAY_NAMES
    for times in (
        f"{start} - {end}" for start, end in zip(INTERVAL_BOUNDS, INTERVAL_BOUNDS[1:])
    )
)


def create_roster(csv_filename):
    with open(csv_filename, newline="") as csvfile:
        # headers_line_num = 3
        # csvfile.readlines(headers_line_num)
        lines_to_skip = 2
        for _ in range(lines_to_skip):
            next(csvfile)

        group_leader_column_name = (
            "Were you confirmed to be a Discussion Group Facilitator?"
        )
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
    """Example time_slot_buckets dict:

    time_slot_buckets = {
        "time_name_1": {
            "leader_ids": {leader_id_1, leader_id_2, ...},
            "student_ids": {student_id_1, student_id_2, ...},
        },
        "time_name_2": {
            "leader_ids": {leader_id_1, leader_id_3, ...},
            "student_ids": {student_id_6, student_id_8, ...},
        },
    }
    """
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
        if (
            not time_slot_buckets[slot]["leader_ids"]
            or not time_slot_buckets[slot]["student_ids"]
        ):
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

    return (
        time_slot_buckets,
        leader_ids,
        student_ids,
        unavailable_leader_ids,
        unavailable_student_ids,
    )


def create_leader_schedule(time_slot_buckets, leader_ids, student_ids):
    timeout = 5
    min_missing_students = student_ids
    schedules = []

    start = time.time()
    while time.time() - start < timeout:
        possible_slots = dict()
        filled_students = set()

        shuffled_leader_ids = list(leader_ids)
        random.shuffle(shuffled_leader_ids)

        shuffled_time_slots = list(time_slot_buckets.keys())
        random.shuffle(shuffled_time_slots)

        for slot in shuffled_time_slots:
            for leader_id in shuffled_leader_ids:
                if leader_id in time_slot_buckets[slot]["leader_ids"]:
                    possible_slots[slot] = leader_id

                    for student_id in time_slot_buckets[slot]["student_ids"]:
                        filled_students.add(student_id)

                    shuffled_leader_ids.remove(leader_id)
                    break

        missing_students = student_ids - filled_students

        if len(missing_students) < len(min_missing_students):
            min_missing_students = missing_students
            schedules = [possible_slots]
        elif len(missing_students) == len(min_missing_students):
            schedules.append(possible_slots)

        if len(missing_students) == 0:
            break

    return schedules, min_missing_students


def fill_students(time_slot_buckets, student_ids, schedules):
    best_final_schedule = {}
    best_unavailable_student_ids = student_ids

    for schedule in schedules:
        final_schedule = {}
        unavailable_student_ids = set()

        for slot in schedule:
            final_schedule[slot] = {
                "leader_ids": set([schedule[slot]]),
                "student_ids": set(),
            }

        student_ids_with_slots = []
        for student_id in student_ids:
            slots = []
            for slot in schedule:
                if student_id in time_slot_buckets[slot]["student_ids"]:
                    slots.append(slot)
            student_ids_with_slots.append((student_id, slots))
        student_ids_with_slots.sort(key=lambda x: len(x[1]))

        for student_id, slots in student_ids_with_slots:
            if len(slots) == 0:
                unavailable_student_ids.add(student_id)
            elif len(slots) == 1:
                final_schedule[slots[0]]["student_ids"].add(student_id)
            else:
                lowest_slot = min(
                    slots, key=lambda slot: len(final_schedule[slot]["student_ids"])
                )
                final_schedule[lowest_slot]["student_ids"].add(student_id)

        if len(unavailable_student_ids) < len(best_unavailable_student_ids):
            best_final_schedule = final_schedule
            best_unavailable_student_ids = unavailable_student_ids

    return best_final_schedule, best_unavailable_student_ids


def create_groups(time_slot_buckets, leader_ids, student_ids):
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
            break_out = False
            schedule = {
                slot: {"leader_ids": set(), "student_ids": set()}
                for slot in time_slot_buckets.keys()
            }
            for leader_id in leader_ids:
                # destination_slot = random.choice(filter(lambda slot: len(schedule[slot]["leader_ids"]) == 0, schedule.keys()))

                possible_schedule = []
                for slot in schedule.keys():
                    if (
                        leader_id in time_slot_buckets[slot]["leader_ids"]
                        and len(schedule[slot]["leader_ids"]) == 0
                    ):
                        possible_schedule.append(slot)

                destination_slot = random.choice(possible_schedule)
                schedule[destination_slot]["leader_ids"].add(leader_id)

            for student_id in student_ids:
                # destination_slot = random.choice(schedule.keys())
                # destination_slot = random.choice([slot for slot in schedule.keys() if len(schedule[slot]["leader_ids"]) == 1])

                possible_schedule = []
                for slot in schedule.keys():
                    if (
                        student_id in time_slot_buckets[slot]["student_ids"]
                        and len(schedule[slot]["leader_ids"]) == 1
                    ):
                        possible_schedule.append(slot)

                if possible_schedule:
                    destination_slot = random.choice(possible_schedule)
                    schedule[destination_slot]["student_ids"].add(student_id)
                else:
                    break_out = True
                    break

            if break_out:
                break

            print("new schedule")
            if is_valid_schedule(schedule, time_slot_buckets):
                return schedule
        max_members_diff += 1
        print(max_members_diff)


def is_valid_schedule(schedule, availability_buckets):
    people_already_encountered = set()
    for schedule_slot, schedule_slot_data in schedule.items():
        # Check that there are no instances of students being scheduled with a non-1 amount of leaders
        if len(schedule_slot_data["leader_ids"]) != 1 and len(
            schedule_slot_data["student_ids"]
        ):
            return False
        # Check that there are no instances of a leader being scheduled with no students
        elif len(schedule_slot_data["leader_ids"]) == 1 and not len(
            schedule_slot_data["student_ids"]
        ):
            return False
        # Check that no person is scheduled twice
        if any(
            [
                person in people_already_encountered
                for person in (
                    schedule_slot_data["leader_ids"] | schedule_slot_data["student_ids"]
                )
            ]
        ):
            return False
        # Check that no student is scheduled for when they are unavailable
        if any(
            [
                student not in availability_buckets[schedule_slot]["student_ids"]
                for student in schedule_slot_data["student_ids"]
            ]
        ):
            return False
        # Check that no leader is scheduled for when they are unavailable
        if any(
            [
                leader not in availability_buckets[schedule_slot]["leader_ids"]
                for leader in schedule_slot_data["leader_ids"]
            ]
        ):
            return False
        people_already_encountered.update(
            schedule_slot_data["leader_ids"] | schedule_slot_data["student_ids"]
        )
    return True


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
    (
        time_slot_buckets,
        leader_ids,
        student_ids,
        unavailable_leader_ids,
        unavailable_student_ids,
    ) = remove_unavailable_time_slots(time_slot_buckets, leader_ids, student_ids)
    if unavailable_leader_ids:
        print("Leaders who are not available at any time that students are available:")
        for unavailable_leader_id in unavailable_leader_ids:
            print(
                f"{roster[unavailable_leader_id]['first']} {roster[unavailable_leader_id]['last']} (RUID: {unavailable_leader_id})"
            )
    if unavailable_student_ids:
        print("Students who are not available at any time that leaders are available:")
        for unavailable_student_id in unavailable_student_ids:
            print(
                f"{roster[unavailable_student_id]['first']} {roster[unavailable_student_id]['last']} (RUID: {unavailable_student_id})"
            )
    # schedule = create_groups(time_slot_buckets, leader_ids, student_ids)
    # print(schedule)
    schedules, min_missing_students = create_leader_schedule(
        time_slot_buckets, leader_ids, student_ids
    )
    final_schedule, unavailable_student_ids = fill_students(
        time_slot_buckets, student_ids, schedules
    )

    print("Is valid:", is_valid_schedule(final_schedule, time_slot_buckets))

    for slot in final_schedule:
        (leader_id,) = final_schedule[slot]["leader_ids"]
        print("Time:", slot)
        print(
            "Leader:",
            f"{roster[leader_id]['first']} {roster[leader_id]['last']} (RUID: {leader_id})",
        )
        print("Students:", len(final_schedule[slot]["student_ids"]))
        for student_id in final_schedule[slot]["student_ids"]:
            print(
                f"{roster[student_id]['first']} {roster[student_id]['last']} (RUID: {student_id})"
            )
        print()

    if unavailable_student_ids:
        print("Students who have conflicts:")
        for unavailable_student_id in unavailable_student_ids:
            print(
                f"{roster[unavailable_student_id]['first']} {roster[unavailable_student_id]['last']} (RUID: {unavailable_student_id})"
            )


if __name__ == "__main__":
    main()
