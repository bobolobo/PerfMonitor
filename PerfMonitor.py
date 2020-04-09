"""Python-based Performance Monitor which mimics Windows built-in Perfmon, only better :)

It also monitors certain processes to watch how many times (hopefully none) they restart.
We collect all product performance stats but give the User a graphic option to pick the actual stats to report on.

To run need to install psutil, numpy, mathplotlib, and winstats python libraries. --Regards, BoboLobo"""

import sys
from sys import exit, argv  # Have to specific import these so packaging/freezing works
import os.path
import argparse
import csv
import time
import datetime as dt
from tkinter import Tk, N, S, E, W, StringVar, Listbox, MULTIPLE
import tkinter.ttk as ttk
import re
import psutil
import winstats
import numpy
import matplotlib.pyplot as plt


class PerfMonitor:
    """Performance Monitoring for Idemia DocAuth"""

    data = []
    time_measure_seconds = 60  # Number of seconds between consecutive data captures.
    time_max_ticks = 0  # Will be computed from the "hours" argument in the command line.
    monitored_process_name = ""
    monitored_pid = 0
    monitored_pid_counter = 0
    headers = []
    reslist = list()

    def process_checker(self, process_to_monitor):
        """Verify that some IDEMIA... processes are running"""

        for p in psutil.process_iter():
            if process_to_monitor in p.name():
                if self.monitored_pid == 0:  # If this is the first time through, capture the name and pid.
                    self.monitored_process_name = p.name()
                    self.monitored_pid = p.pid
                elif self.monitored_pid != p.pid:
                    self.monitored_pid_counter += 1  # Track times that Regula has restarted
                    self.monitored_pid = p.pid       # Get new pid value for Regula service
                return True
        return False

    def command_line_arguments(self):
        """Read and evaluate commandline arguments, returns the single commandline argument"""

        try:
            parser = argparse.ArgumentParser(description='Performance Monitoring for Idemia DocAuth')
            subparsers = parser.add_subparsers(dest='subcommand')

            # Subparser for "Report".
            parser_report = subparsers.add_parser('report')
            # Add a required argument.
            parser_report.add_argument('world', choices=['oldworld', 'newworld', 'catcworld', 'audiodgworld'],
                                       type=str, help='oldworld, newworld, catcworld, or audiodgworld')

            # Subparser for "Record".
            parser_record = subparsers.add_parser('record')
            # Add required arguments.
            parser_record.add_argument('world', choices=['oldworld', 'newworld', 'catcworld', 'audiodgworld'],
                                       type=str, help='oldworld, newworld, catcworld, audiodgworld')
            parser_record.add_argument('esf', choices=['esf', 'noesf'], type=str, help='esf | noesf')
            parser_record.add_argument('hours', type=int, help='number of hours')

            # Parse the arguments
            args = parser.parse_args()

            if hasattr(args, 'hours'):   # Only set this if we are recording data. IF no "hours" arg, then a crash.
                self.time_max_ticks = args.hours * 60  # mult by 60, Once a min.

            if args.world == 'catcworld':  # CAT-C does not have a separate ESF process to monitor. Reset to no monitor.
                args.esf = 'noesf'
            if args.world == 'audiodgworld':
                args.esf = 'noesf'

            return args

        except Exception as err:
            print(err)

            return args


    def string_cleaner(self, what_to_do, temp_string_buffer):
        """ Routine to strip brackets, parens, extra commas, etc from string buffer before writing to csv file """

        if what_to_do == "header":
            # Capture first row because of headers and strip out some cruft from the header
            tempstring = temp_string_buffer.replace(r"\Process", "")
            tempstring = tempstring.replace(" ", "")  # Replace space with no_space
            tempstring = tempstring.split(",")  # Turn headers string into a list of headers
        elif what_to_do == "data":
            # Strip brackets, single quotes, parens from buffer. Matplotlib seems to send data with commas at the end.
            tempstring = (str(temp_string_buffer).translate(str.maketrans({'[': '', ']': '', '\'': '', ')': '', '(': ''})))
            tempstring = re.sub(r',,', ',', tempstring)  # Remove double commas
            tempstring = re.sub(r',$', '', tempstring)  # Remove Trailing comma

        return tempstring

    def which_perf_columns(self):
        """After querying user for which performance stats to plot, loads that data into data array."""

        root = Tk()
        root.title("Select performance statistics to display")
        # root.geometry("60x20")
        frame = ttk.Frame(root, padding=(6, 6, 12, 12))
        frame.grid(column=0, row=0, sticky=(N, S, E, W))

        perf_values = StringVar()
        perf_values.set(self.headers)

        perf_box = Listbox(frame, listvariable=perf_values, selectmode=MULTIPLE, width=60, height=20)
        perf_box.grid(column=0, row=0, columnspan=1)

        def select():  # Called by Button press
            """Tk-related function for GUI use."""
            selection = perf_box.curselection()
            for i in selection:
                entrada = perf_box.get(i)
                self.reslist.append(entrada)
            for val in self.reslist:
                print(val)
                # perf_box.grid_forget()
            root.destroy()  # Destroy the GUI after selections made.

        btn = ttk.Button(frame, text="Display Chart", command=select)
        btn.grid(column=0, row=1, columnspan=1)

        root.mainloop()

    def process_to_monitor(self, which_world):
        """This picks which process to monitor based on WORLD arg."""

        if which_world == 'newworld':
            process_name_to_monitor = 'IDEMIA.DocAuth.Document.App.exe'
            if not self.process_checker(process_name_to_monitor):
                print("DocAuth is NOT running. Please startup DocAuth BEFORE running this PerformanceMonitor.")
                exit(2)
            output_filename = r'c:\Temp\DocAuthPerfData.csv'
            f = open(output_filename, 'wt', buffering=1)
            writer = csv.writer(f, delimiter=',', quotechar=' ', lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        elif which_world == 'oldworld':
            process_name_to_monitor = 'DocAuth.Applications.Authenticate.exe'
            if not self.process_checker(process_name_to_monitor):
                print("DocAuth is NOT running. Please startup DocAuth BEFORE running this PerformanceMonitor.")
                exit(2)
            output_filename = r'c:\Temp\DocAuthPerfData_OldWorld.csv'
            f = open(output_filename, 'wt', buffering=1)
            writer = csv.writer(f, delimiter=',', quotechar=' ', lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        elif which_world == 'catcworld':
            process_name_to_monitor = 'IS.exe'
            if not self.process_checker(process_name_to_monitor):
                print("IS.exe is NOT running. Please startup CATC BEFORE running this PerformanceMonitor.")
                exit(2)
            output_filename = r'c:\Temp\DocAuthPerfData_CatcWorld.csv'
            f = open(output_filename, 'wt', buffering=1)
            writer = csv.writer(f, delimiter=',', quotechar=' ', lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        elif which_world == 'audiodgworld':
            process_name_to_monitor = 'audiodg.exe'
            if not self.process_checker(process_name_to_monitor):
                print("audiodg is NOT running. Please startup DocAuth BEFORE running this PerformanceMonitor.")
                exit(2)
            output_filename = r'c:\Temp\DocAuthPerfData_Audiodg.csv'
            f = open(output_filename, 'wt', buffering=1)
            writer = csv.writer(f, delimiter=',', quotechar=' ', lineterminator='\n', quoting=csv.QUOTE_MINIMAL)

        return f, writer, output_filename

    def data_collector(self, which_world):
        """Collect performance via winstats library. Then write each line of data to csv file"""

        choicetemp = self.command_line_arguments()

        # Verify that DocAuth IS running, and assign csv filename based on old vs new world

        f, writer, output_filename = self.process_to_monitor(which_world)

        print("\nVerified that DocAuth IS running. Recording data for ", choicetemp.hours, " hours...")
        print("CTRL-C to stop recording earlier.")

        # Run through ticks (time) for x-axis.

        stats_list_audiodgworld = [r'\Process(audiodg)\Private Bytes',
                                   r'\Process(audiodg)\Virtual Bytes',
                                   r'\Process(audiodg)\Working Set - Private']

        stats_list_oldworld = [r'\Process(BGExaminer)\Private Bytes',
                               r'\Process(BGExaminer)\Virtual Bytes',
                               r'\Process(BGExaminer)\Working Set - Private',
                               r'\Process(bgServer)\Private Bytes',
                               r'\Process(bgServer)\Virtual Bytes',
                               r'\Process(bgServer)\Working Set - Private',
                               r'\Process(DocAuth.Applications.Authenticate)\Private Bytes',
                               r'\Process(DocAuth.Applications.Authenticate)\Virtual Bytes',
                               r'\Process(DocAuth.Applications.Authenticate)\Working Set - Private',
                               r'\Process(IDEMIA.DocAuth.RegulaService)\Private Bytes',
                               r'\Process(IDEMIA.DocAuth.RegulaService)\Virtual Bytes',
                               r'\Process(IDEMIA.DocAuth.RegulaService)\Working Set - Private',
                               r'\Process(DataAnalysisApiHost)\Private Bytes',
                               r'\Process(DataAnalysisApiHost)\Virtual Bytes',
                               r'\Process(DataAnalysisApiHost)\Working Set - Private']

        stats_list_catcworld = [r'\Process(BGExaminer)\Private Bytes',
                                r'\Process(BGExaminer)\Virtual Bytes',
                                r'\Process(BGExaminer)\Working Set - Private',
                                r'\Process(bgServer)\Private Bytes',
                                r'\Process(bgServer)\Virtual Bytes',
                                r'\Process(bgServer)\Working Set - Private',
                                r'\Process(ECAT)\Private Bytes',
                                r'\Process(ECAT)\Virtual Bytes',
                                r'\Process(ECAT)\Working Set - Private',
                                r'\Process(node#1)\Private Bytes',
                                r'\Process(node#1)\Virtual Bytes',
                                r'\Process(node#1)\Working Set - Private',
                                r'\Process(node)\Private Bytes',
                                r'\Process(node)\Virtual Bytes',
                                r'\Process(node)\Working Set - Private',
                                r'\Process(java)\Private Bytes',
                                r'\Process(java)\Virtual Bytes',
                                r'\Process(java)\Working Set - Private',
                                r'\Process(java#1)\Private Bytes',
                                r'\Process(java#1)\Virtual Bytes',
                                r'\Process(java#1)\Working Set - Private',
                                r'\Process(FlirTcpClient#1)\Private Bytes',
                                r'\Process(FlirTcpClient#1)\Virtual Bytes',
                                r'\Process(FlirTcpClient#1)\Working Set - Private',
                                r'\Process(FlirTcpClient)\Private Bytes',
                                r'\Process(FlirTcpClient)\Virtual Bytes',
                                r'\Process(FlirTcpClient)\Working Set - Private',
                                r'\Process(IPS)\Private Bytes',
                                r'\Process(IPS)\Virtual Bytes',
                                r'\Process(IPS)\Working Set - Private',
                                r'\Process(IA)\Private Bytes',
                                r'\Process(IA)\Virtual Bytes',
                                r'\Process(IA)\Working Set - Private',
                                ]

        stats_list_newworld = [r'\Process(IDEMIA.DocAuth.Document.App)\Private Bytes',
                               r'\Process(IDEMIA.DocAuth.Document.App)\Virtual Bytes',
                               r'\Process(IDEMIA.DocAuth.Document.App)\Working Set - Private',
                               r'\Process(bgServer)\Private Bytes',
                               r'\Process(bgServer)\Virtual Bytes',
                               r'\Process(bgServer)\Working Set - Private',
                               r'\Process(IDEMIA.DocAuth.RegulaService)\Private Bytes',
                               r'\Process(IDEMIA.DocAuth.RegulaService)\Virtual Bytes',
                               r'\Process(IDEMIA.DocAuth.RegulaService)\Working Set - Private',
                               r'\Process(IDEMIA.DocAuth.LinecodeService)\Private Bytes',
                               r'\Process(IDEMIA.DocAuth.LinecodeService)\Virtual Bytes',
                               r'\Process(IDEMIA.DocAuth.LinecodeService)\Working Set - Private']

        stats_list_esf = [r'\Process(IDEMIA.DocAuth.ESFService)\Private Bytes',
                          r'\Process(IDEMIA.DocAuth.ESFService)\Virtual Bytes',
                          r'\Process(IDEMIA.DocAuth.ESFService)\Working Set - Private']

        # Load the processes to check based on whether oldworld, newworld, catcworld
        if which_world == 'newworld':
            stats_list = stats_list_newworld
        elif which_world == 'catcworld':
            stats_list = stats_list_catcworld
        elif which_world == 'oldworld':
            stats_list = stats_list_oldworld
        else:  # monitoring just audiodg process:
            stats_list = stats_list_audiodgworld

        # Capture ESF data only if 'ESF' argument was given on commandline.

        # Write header file to csv containing name of all perf stats being tracked.
        if choicetemp.esf == 'esf':
            # Write the perf names to the csv file including ESF stats.
            writer.writerow(stats_list + stats_list_esf)
        else:
            # Write perf names to the csv file NOT including ESF stats.
            writer.writerow(stats_list)

        for ticks in range(self.time_max_ticks):  # 1440 = 12 hours for 30 second tick | 4320 = 36 hours

            time_track = dt.datetime.fromtimestamp(time.time())  # Get timestamp-style time
            time_track = time_track.strftime("%m/%d/%y %H:%M")   # Keep "m/d/y h/m" drop seconds.milliseconds
            print(time_track, end=" ")

            # This is where we interrogate the statistics.

            try:
                # Using a list comprehension instead of a bunch of variables. Interrogate perf data.
                line_of_data = [winstats.get_perf_data(i, fmts='double') for i in stats_list]

                # Capture ESF data only if 'ESF' argument was given on commandline.
                # choicetemp = self.command_line_arguments()

                if choicetemp.esf == 'esf':
                    line_of_data_esf = [winstats.get_perf_data(i, fmts='double') for i in stats_list_esf]

                    # Write a row of stats to the csv file including ESF stats.
                    writer.writerow((time_track, self.string_cleaner("data", line_of_data),
                                     self.string_cleaner("data", line_of_data_esf)))
                else:
                    # Write a row of stats to the csv file NOT including ESF stats.
                    writer.writerow((time_track, self.string_cleaner("data", line_of_data)))

                # Output test status to console.
                print(" tick:", ticks, "of", self.time_max_ticks, " name:", self.monitored_process_name, " pid:",
                      self.monitored_pid, ", was restarted ", self.monitored_pid_counter, " times.")

                # See if the DocAuth service has restarted. IF there is a new pid, then it did restart.
                self.process_checker(self.monitored_process_name)

                time.sleep(self.time_measure_seconds)  # Sleep for time slice

            except WindowsError as error:  # Processes down? Winstat errors out, so handle it. Continue the loop.
                print(f"One of the processes was not available for interrogation:", error)
                time.sleep(self.time_measure_seconds)  # Sleep for time slice, otherwise this keeps throwing message.

            except KeyboardInterrupt as error:  # On ctrl-c from keyboard, flush buffer, close file, exit. Break loop.
                print("\n\nExiting...")
                break

        f.close()

        # Print out how many times Regula service was restarted
        print("\nData was collected and stored in file: ", output_filename)
        print(self.monitored_process_name, " was restarted ", self.monitored_pid_counter, " times.")

    def file_reader(self, input_filename):
        """Read in csv performance file, line by line"""

        if not os.path.isfile(input_filename):  # Check for existing csv file.
            print("File name: ", input_filename, " does not exist. Maybe you need to record data first ?")
            exit(2)
        if os.path.getsize(input_filename) == 0:  # Check for empty csv file.
            print("File name: ", input_filename, " is empty. Maybe your last recording did not work ?")
            exit(2)

        # Read file grab header and rest of file
        f = open(input_filename, 'rt')
        with f:
            reader = csv.reader(f)
            # Capture first row because of headers and strip out some cruft from the header
            self.headers = next(f)
            # self.headers = self.headers.replace("\Process", "")
            # self.headers = self.headers.replace(" ", "")  # Replace space with no_space
            # self.headers = self.headers.split(",")  # Turn headers string into a list of headers
            self.headers = self.string_cleaner("header", self.headers)  # Clean header, strip some characters and spaces

            for x_row in reader:  # Read in rest of data
                self.data.append(x_row)
        f.close()
        return self.data

    def data_plotter(self):
        """Plot performance data from csv file using winstats library"""

        a = numpy.array(self.data)
        time_track = a[:, 0]  # Extract Timestamps (as string)

        # Figure out how many hours worth of data came from the csv file
        # total_elapsed_time = (len(a) / 2) / 60   # (/2 for 30 second interval the /60 to get hours)
        total_elapsed_time = (len(a) / 60)   # (/60 to get hours)
        total_elapsed_time = round(total_elapsed_time, 2)

        # Ask user which data to plot
        self.which_perf_columns()

        # Create cartesian plane, draw labels and title
        _fig, ax = plt.subplots()  # Returns a figure container and a single xy axis chart. Figure is a dummy var.

        # Build chart title and include number of hours that the test ran for.
        chart_title = "Bricktest memory utilization ran for " + str(total_elapsed_time) + " hour(s)"
        ax.set_title(chart_title)

        ax.set_xlabel('Date/Time')
        ax.set_ylabel('Memory in Megabytes')
        ax.xaxis.set_major_locator(plt.MaxNLocator(20))  # Display a max of 20 x-axis time ticks

        # Plot the data

        # Iterate through performance counters
        j = 0  # Skip first column which contains times: a[:, 0], then plot all other data columns as user requests.
        for i in self.headers:  # Walk through ALL available stats from csv file.
            j += 1                     # Index for what perf stat to report.
            for k in self.reslist:     # Walk through user's choices, compare to what is available.
                if k == i:             # If match then output the perf stat the user is requesting.
                    temp_stat = a[:, j]
                    temp_stat = numpy.asfarray(temp_stat, float)
                    ax.plot(time_track, temp_stat / 1000000)  # This plots a column of data at a time.

        ax.grid(True)
        ax.figure.autofmt_xdate()

        # Print out legend automatically, cool!
        # ax.legend([i for i in self.reslist])
        ax.legend(self.reslist)

        # Output the chart.  Really only needed if NOT in "interactive mode".
        # If in non-interactive mode, may need to use "plt.show()" instead.
        # fig.show()
        plt.show()

# Run this bitch


def main():
    """Main to run the Perfmonitor."""

    pm = PerfMonitor()

    choice = pm.command_line_arguments()

    # Debugging
    # pm.command_line_arguments()
    # choice = pm.args  # Using this global which i would like to get as a return from command_line_augments() instead.

    print("Choice: ", choice)

    if choice.subcommand == "record" and choice.world == "oldworld":
        pm.data_collector("oldworld")
    elif choice.subcommand == "record" and choice.world == "newworld":
        pm.data_collector("newworld")
    elif choice.subcommand == "record" and choice.world == "catcworld":
        pm.data_collector("catcworld")
    elif choice.subcommand == "record" and choice.world == "audiodgworld":
        pm.data_collector("audiodgworld")
    elif choice.subcommand == "report" and choice.world == "oldworld":
        pm.file_reader(r"c:\Temp\DocAuthPerfData_OldWorld.csv")
        pm.data_plotter()
    elif choice.subcommand == "report" and choice.world == "newworld":
        pm.file_reader(r"c:\Temp\DocAuthPerfData.csv")
        pm.data_plotter()
    elif choice.subcommand == "report" and choice.world == "catcworld":
        pm.file_reader(r"c:\Temp\DocAuthPerfData_CatcWorld.csv")
        pm.data_plotter()
    elif choice.subcommand == "report" and choice.world == "audiodgworld":
        pm.file_reader(r"c:\Temp\DocAuthPerfData_Audiodg.csv")
        pm.data_plotter()


if __name__ == "__main__":
    main()
