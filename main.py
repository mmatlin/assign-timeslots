import csv

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


# Keys are IDs, Values are dicts containing all the information about an individual (both leaders and students)
roster = {}
# Keys are Time Slot names, Values are dicts containing available leaders and students for the given time slot
time_slot_buckets = {}
# IDs of leaders
leader_ids = set()
# IDs of students
student_ids = set()


def process_csv(filename):
    with open(filename, newline="") as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            row["availability"] = {k: v for k, v in row.items() if k in TIME_SLOTS}
            if row["Group leader?"] == "Yes":
                leader_ids.add(row["RUID"])
            else:
                student_ids.add(row["RUID"])
            roster[row["RUID"]] = row


def fill_time_slot_buckets():
    # Initialize time slots
    for slot in TIME_SLOTS:
        time_slot_buckets[slot] = {"leader_ids": set(), "student_ids": set()}

    # Add availability of all leaders first
    for leader_id in leader_ids:
        for slot, available in roster[leader_id]["availability"].items():
            if available != "Available":
                continue
            time_slot_buckets[slot]["leader_ids"].add(leader_id)

    # Add availability of students
    for student_id in student_ids:
        for slot, available in roster[student_id]["availability"].items():
            if available != "Available":
                continue
            time_slot_buckets[slot]["student_ids"].add(student_id)


def remove_unavailable_time_slots():
    # Remove time slots without any leaders or students, keep track of leaders and students in time slots
    available_leader_ids = set()
    available_student_ids = set()
    for slot in time_slot_buckets:
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


if __name__ == "__main__":
    csv_filename = "real.csv"
    process_csv(csv_filename)
    fill_time_slot_buckets()
    remove_unavailable_time_slots()
