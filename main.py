import csv

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
roster = (
    {}
)  # Keys are RUIDs, Values are dicts containing all the information about an individual
leaders = []  # RUIDs
students = []  # RUIDs


def process_csv(filename):
    with open(filename, newline="") as real_csv:
        csvreader = csv.DictReader(real_csv)
        for row in csvreader:
            row["Availability"] = {
                k: v
                for k, v in row
                if any(k.startswith(day_name) for day_name in DAY_NAMES)
            }
            # print(row)
            if row["Group leader?"] == "Yes":
                leaders.append(row["RUID"])
            else:
                students.append(row["RUID"])
            roster[row["RUID"]] = row


if __name__ == "__main__":
    csv_filename = "real.csv"
    process_csv(csv_filename)
    # remove_duplicates()
    # bucket_time_slots()
    # pass
