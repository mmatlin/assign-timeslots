import csv
import random
import time
from util import is_valid_schedule

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
TIMEOUT = 60


def create_roster(csv_filename):
    """Creates a roster from the CSV file and returns the roster, the IDs of students, and the IDs group leaders.
    The student/leader IDs are returned as sets and the roster is returned as a dict in this format:
    {
        ID_1: {
            "first": first_name_1,
            "last": last_name_1,
            "email": email_1,
            "leader": leader_status_1,
            "availability": {
                "Monday 8am - 9am": False,
                "Monday 9am - 10am": True,
                ...
            }
        },
        ID_2: ...,
    }
    """
    with open(csv_filename) as csvfile:
        # Skip needless line at the top
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
        # Create an entry in the roster for each user with their contact details and availability
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
                "leader": row[group_leader_column_name] == "Yes",
                "availability": availability,
            }

    return roster, leader_ids, student_ids


def create_availability_table(roster, leader_ids, student_ids):
    """Returns a dict of which leaders/students are available for each time slot.

    Example availability_table dict:

    availability_table = {
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
    # Initialize availability_table
    availability_table = dict()
    for slot in TIME_SLOTS:
        availability_table[slot] = {"leader_ids": set(), "student_ids": set()}

    # Add availability of all leaders first
    for leader_id in leader_ids:
        for slot, available in roster[leader_id]["availability"].items():
            if available:
                availability_table[slot]["leader_ids"].add(leader_id)

    # Add availability of students
    for student_id in student_ids:
        for slot, available in roster[student_id]["availability"].items():
            if available:
                availability_table[slot]["student_ids"].add(student_id)

    return availability_table


def remove_unavailable_time_slots(availability_table, leader_ids, student_ids):
    """Removes any time slots without any leaders or students from the given availability table.

    Records people who have conflicts (leaders not available for any times that students are available, and vice versa).
    """
    available_leader_ids = set()
    available_student_ids = set()
    all_time_slots = [key for key in availability_table.keys()]

    # Remove any time slots without leaders OR without students
    # Keep track of leaders and students in good time slots
    for slot in all_time_slots:
        if (
            not availability_table[slot]["leader_ids"]
            or not availability_table[slot]["student_ids"]
        ):
            del availability_table[slot]
        else:
            available_leader_ids.update(availability_table[slot]["leader_ids"])
            available_student_ids.update(availability_table[slot]["student_ids"])

    # Identify leaders who are unavailable for every time slot with at least one available student
    unavailable_leader_ids = leader_ids - available_leader_ids
    if unavailable_leader_ids:
        # At least one leader exists who does not fit into any time slot
        # Remove the bad leader(s) from leader_ids
        leader_ids = available_leader_ids

    # Identify students who are unavailable for every time slot with at least one available leader
    unavailable_student_ids = student_ids - available_student_ids
    if unavailable_student_ids:
        # At least one student exists who does not fit into any time slot
        # Remove the bad student(s) from student_ids
        student_ids = available_student_ids

    return (
        availability_table,
        leader_ids,
        student_ids,
        unavailable_leader_ids,
        unavailable_student_ids,
    )


def create_leader_schedules(availability_table, leader_ids, student_ids):
    """Attempts to find the time slot + leaders combination that will cover the most possible students.

    For each randomly generated time slot combo, we check to see how many students were not covered.
    The best possible schedule(s) will have the least amount of students excluded, with the ideal being 0
    (every student was able to be included).

    Since the total number of combinations is insanely high, this loop runs for a fixed amount of time, and
    tries to find the best possible combination(s). Note that this is not necessarily linear; performance
    improvements will decrease exponentially over time.
    """
    # score is the number of students still missing (lower scores are better, indicating that fewer students were not covered)
    # initialized to maximum possible value (number of available students)
    score = len(student_ids)
    # leader_schedules stores possible time slot + leaders combinations that have the best score (same number of excluded students)
    leader_schedules = []

    start = time.time()
    while time.time() - start < TIMEOUT:
        # possible_slots is a dict with keys being slots and values being a leader_id assigned to that slot
        possible_slots = dict()
        # filled_student_ids is a set to store all the students which have already been accounted for with a particular time slot + leaders combination
        filled_student_ids = set()

        remaining_leader_ids = set(leader_ids)

        # Shuffle the order of time slots to generate new combinations
        shuffled_time_slots = list(availability_table.keys())
        random.shuffle(shuffled_time_slots)

        for slot in shuffled_time_slots:
            for leader_id in remaining_leader_ids:
                if leader_id in availability_table[slot]["leader_ids"]:
                    # Found a leader for this time slot
                    possible_slots[slot] = leader_id

                    # Add all students that can attend this time slot to filled_student_ids
                    for student_id in availability_table[slot]["student_ids"]:
                        filled_student_ids.add(student_id)

                    # Remove this leader from the availability pool
                    remaining_leader_ids.remove(leader_id)

                    # Move on to next random time slot
                    break

        missing_students = student_ids - filled_student_ids

        if len(missing_students) < score:
            # Found a score better than the exitsing best score
            score = len(missing_students)
            leader_schedules = [possible_slots]
        elif len(missing_students) == score:

            leader_schedules.append(possible_slots)

        if len(missing_students) == 0:
            # Best case scenario: all students can be accomodated with the existing leader_schedule
            # No need to continue searching for better combinations
            break

    print("Number of conflicting students:", score)
    return leader_schedules


def fill_students(availability_table, student_ids, leader_schedules):  # , roster):
    """Fills each potential schedule with students and returns the schedule with the least student conflicts,
    as well as the list of students with conflicts.

    Example final_schedule / tentative_schedule:

    final_schedule = {
        "time_name_1": {
            "leader_ids": {leader_id_1},
            "student_ids": {student_id_1, student_id_2, ...},
        },
        "time_name_2": {
            "leader_ids": {leader_id_2},
            "student_ids": {student_id_6, student_id_8, ...},
        },
    }
    """
    final_schedule = dict()
    final_conflict_student_ids = set(student_ids)

    for leader_schedule in leader_schedules:
        tentative_schedule = dict()
        tentative_conflict_student_ids = set()

        # Initialize each time slot in schedule to have a set for student IDs and a set for leader IDs
        for slot in leader_schedule:
            tentative_schedule[slot] = {
                "leader_ids": set([leader_schedule[slot]]),
                "student_ids": set(),
            }

        # TODO: Generate student_ids_with_slots from roster (easier for computing)
        # student_ids_with_slots1 = [(ID, [slot for slot, available in info["availability"].items() if available]) for ID, info in roster.items() if ID in student_ids]
        # student_ids_with_slots1.sort(key=lambda x: len(x[1]))

        student_ids_with_slots = []
        for student_id in student_ids:
            slots = []
            for slot in leader_schedule:
                if student_id in availability_table[slot]["student_ids"]:
                    slots.append(slot)
            student_ids_with_slots.append((student_id, slots))
        student_ids_with_slots.sort(key=lambda x: len(x[1]))

        for student_id, slots in student_ids_with_slots:
            if len(slots) == 0:
                tentative_conflict_student_ids.add(student_id)
            elif len(slots) == 1:
                tentative_schedule[slots[0]]["student_ids"].add(student_id)
            else:
                lowest_slot = min(
                    slots, key=lambda slot: len(tentative_schedule[slot]["student_ids"])
                )
                tentative_schedule[lowest_slot]["student_ids"].add(student_id)

        if len(tentative_conflict_student_ids) < len(final_conflict_student_ids):
            final_schedule = tentative_schedule
            final_conflict_student_ids = tentative_conflict_student_ids

    return final_schedule, final_conflict_student_ids


def main():
    print(f"This program may take up to approximately {TIMEOUT} seconds!")
    csv_filename = "real.csv"

    # Create roster
    roster, leader_ids, student_ids = create_roster(csv_filename)

    # Create availability table
    availability_table = create_availability_table(roster, leader_ids, student_ids)

    # Remove unavailable time slots
    (
        availability_table,
        leader_ids,
        student_ids,
        unavailable_leader_ids,
        unavailable_student_ids,
    ) = remove_unavailable_time_slots(availability_table, leader_ids, student_ids)

    # Create leader schedule
    leader_schedules = create_leader_schedules(
        availability_table, leader_ids, student_ids
    )

    # Fill students
    final_schedule, conflict_student_ids = fill_students(
        availability_table, student_ids, leader_schedules  # , roster
    )

    # Sanity check to make sure schedule is valid
    if not is_valid_schedule(final_schedule, availability_table):
        print("Error running script. Invalid schedule generated.")
        return

    # Output final schedule to stdout
    for slot in final_schedule:
        (leader_id,) = final_schedule[slot]["leader_ids"]
        print("Time:", slot)
        print(
            "Leader:",
            f"{roster[leader_id]['first']} {roster[leader_id]['last']} (RUID: {leader_id}, email: {roster[leader_id]['email']})",
        )
        print("Students:", len(final_schedule[slot]["student_ids"]))
        for student_id in final_schedule[slot]["student_ids"]:
            print(
                f"{roster[student_id]['first']} {roster[student_id]['last']} (RUID: {student_id}, email: {roster[student_id]['email']})"
            )
        print()

    # Output unavailable leaders/students to stdout
    if unavailable_leader_ids:
        print("Leaders who are not available at any time that students are available:")
        for unavailable_leader_id in unavailable_leader_ids:
            print(
                f"{roster[unavailable_leader_id]['first']} {roster[unavailable_leader_id]['last']} (RUID: {unavailable_leader_id}, email: {roster[leader_id]['email']})"
            )
        print()
    if unavailable_student_ids:
        print("Students who are not available at any time that leaders are available:")
        for unavailable_student_id in unavailable_student_ids:
            print(
                f"{roster[unavailable_student_id]['first']} {roster[unavailable_student_id]['last']} (RUID: {unavailable_student_id}, email: {roster[student_id]['email']})"
            )
        print()

    # Output conflict students to stdout
    if conflict_student_ids:
        print("Students who have conflicts:")
        for conflict_student_id in conflict_student_ids:
            print(
                f"{roster[conflict_student_id]['first']} {roster[conflict_student_id]['last']} (RUID: {conflict_student_id}, email: {roster[student_id]['email']})"
            )
        print()

    # Output final schedule to csv file
    headers = (
        "Time",
        "Leader",
        "Leader RUID",
        "Leader email",
        "Students",
        "Student RUIDs",
        "Student emails",
    )
    out_csv = ",".join(headers)
    for slot, slot_info in final_schedule.items():
        (leader_id,) = slot_info["leader_ids"]
        out_csv += "\n"
        out_csv += ",".join(
            [
                slot,
                roster[leader_id]["first"] + " " + roster[leader_id]["last"],
                leader_id,
                roster[leader_id]["email"],
                f'"{",".join([roster[student_id]["first"] + " " + roster[student_id]["last"] for student_id in slot_info["student_ids"]])}"',
                ";".join(slot_info["student_ids"]),
                f'"{",".join([roster[student_id]["email"] for student_id in slot_info["student_ids"]])}"',
            ]
        )

    with open("schedule.csv", "w") as f:
        f.write(out_csv)
    print('A .csv file with the generated schedule has been created as "schedule.csv".')


if __name__ == "__main__":
    main()
