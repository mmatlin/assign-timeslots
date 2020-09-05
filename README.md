# assign-timeslots
Instructions for use:
1. Install Python (version at least 3.8).
1. If you have Git installed, clone this repo into the desired folder of your choice:  
`git clone https://github.com/mmatlin/assign-timeslots.git`. Alternatively, you can simply download `main.py` and `util.py` and place them into a folder.
1. Save the REAL availability form results as a .csv file named `real.csv` (whether by exporting from Excel or otherwise) and place the file into the repo folder.
1. Open a terminal window and run `python main.py`.
1. The schedule will be output as text in the terminal and a .csv file with the schedule will be generated as `schedule.csv` in the repo folder. **Note that students who cannot be placed into the schedule will not be recorded in schedule.csv but in the program output.**
