def is_valid_schedule(schedule, availability_table):
    """Checks that the schedule given meets several criteria for validity.
    """
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
                student not in availability_table[schedule_slot]["student_ids"]
                for student in schedule_slot_data["student_ids"]
            ]
        ):
            return False
        # Check that no leader is scheduled for when they are unavailable
        if any(
            [
                leader not in availability_table[schedule_slot]["leader_ids"]
                for leader in schedule_slot_data["leader_ids"]
            ]
        ):
            return False
        people_already_encountered.update(
            schedule_slot_data["leader_ids"] | schedule_slot_data["student_ids"]
        )
    return True
