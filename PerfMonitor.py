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
import matplotlib.ticker


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
        """Verify that important IDEMIA... processes are running"""

        for p in psutil.process_iter():
            try:
                if process_to_monitor in p.name():
                    if self.monitored_pid == 0:  # If this is the first time through, capture the name and pid.
                        self.monitored_process_name = p.name()
                        self.monitored_pid = p.pid
                    elif self.monitored_pid != p.pid:
                        self.monitored_pid_counter += 1  # Track times that the process has restarted
                        self.monitored_pid = p.pid       # Get new pid value for the process
                    return True
            except WindowsError as error:  # Main Processes down? Can't find it to count. Continue the loop.
                print(f"The main Process was not available for interrogation and counting:", process_to_monitor)
                # time.sleep(self.time_measure_seconds)  # Sleep for time slice, otherwise this keeps throwing message.

        return False

    def command_line_arguments(self):
        """Read and evaluate commandline arguments, returns the single commandline argument"""

        try:
            parser = argparse.ArgumentParser(description='Performance Monitoring for Idemia DocAuth')
            subparsers = parser.add_subparsers(dest='subcommand')

            # Subparser for "Report".
            parser_report = subparsers.add_parser('report')
            # Add a required argument.
            parser_report.add_argument('world', metavar='world', choices=['dotnetworld', 'mobileDLworld', 'biocoreworld', 'ecatworld', 'oldworld', 'oldserviceworld', 'newworld', 'catcworld', 'audiodgworld', 'autocatworld'], type=str, help='[dotnetworld | biocoreworld | ecatworld | oldworld | oldserviceworld | newworld | catcworld | audiodgworld | autocatworld]')

            # Subparser for "Record".
            parser_record = subparsers.add_parser('record')
            # Add required arguments.
            parser_record.add_argument('world', metavar='world', choices=['dotnetworld', 'mobileDLworld', 'biocoreworld', 'ecatworld', 'oldworld', 'oldserviceworld', 'newworld', 'catcworld', 'audiodgworld', 'autocatworld'], type=str, help='[dotnetworld | biocoreworld | ecatworld | oldworld | oldserviceworld | newworld | catcworld | audiodgworld | autocatworld]')
            parser_record.add_argument('esf', choices=['esf', 'noesf'], type=str)
            parser_record.add_argument('hours', type=int, help='number of hours')

            # Parse the arguments
            args = parser.parse_args()

            if hasattr(args, 'hours'):   # Only set this if we are recording data. IF no "hours" arg, then a crash.
                self.time_max_ticks = args.hours * 60  # mult by 60, Once a min.

            # At some point ESF will be a separate process to monitor for all worlds.
            # Right now only newworld has a separate ESF process. So disable esf checking for all other processes.
            if args.world == 'oldworld':  # Oldworld does not have a separate ESF service yet.
                args.esf = 'noesf'
            if args.world == 'oldserviceworld':  # Oldserviceworld does not have a separate ESF service yet.
                args.esf = 'noesf'
            if args.world == 'dotnetworld':  # Biocore testing does not have a separate ESF process to monitor.
                args.esf = 'noesf'
            if args.world == 'mobileDLworld':  # mobileDLworld testing does not have a separate ESF process to monitor.
                args.esf = 'noesf'
            if args.world == 'biocoreworld':  # Biocore testing does not have a separate ESF process to monitor.
                args.esf = 'noesf'
            if args.world == 'ecatworld':  # CAT-C does not have a separate ESF process to monitor since it is oldworld.
                args.esf = 'noesf'
            if args.world == 'catcworld':  # CAT-C does not have a separate ESF process to monitor since it is oldworld.
                args.esf = 'noesf'
            if args.world == 'audiodgworld': # Just monitoring audiodg process since it likes to runaway sometimes.
                args.esf = 'noesf'
            if args.world == 'autocatworld': # AutoCAT testing does not have a separate ESF process to monitor??
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
        elif what_to_do == "badstatname":
            # tempstring = temp_string_buffer[temp_string_buffer.find("(")+1:temp_string_buffer.find(")")]
            tempstring = re.search(r'\((.*?)\)', temp_string_buffer).group(1)

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

        if which_world == 'dotnetworld':
            process_name_to_monitor = 'IDEMIA.DocAuth.DocumentService.exe'
            if not self.process_checker(process_name_to_monitor):
                print("IDEMIA.DocAuth.DocumentService is NOT running. "
                      "Please startup DocAuth BEFORE running this PerformanceMonitor.")
                exit(2)
            output_filename = r'c:\Temp\DocAuthPerfData_DotNetWorld.csv'
            f = open(output_filename, 'wt', buffering=1)
            writer = csv.writer(f, delimiter=',', quotechar=' ', lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        elif which_world == 'mobileDLworld':
            process_name_to_monitor = 'MobileDLReaderSampleApp.exe'
            if not self.process_checker(process_name_to_monitor):
                print("Standalone MobileDLReaderSampleApp is NOT running. Please startup DocAuth BEFORE running this PerformanceMonitor.")
                exit(2)
            output_filename = r'c:\Temp\DocAuthPerfData_MobileDLReaderSampleAppWorld.csv'
            f = open(output_filename, 'wt', buffering=1)
            writer = csv.writer(f, delimiter=',', quotechar=' ', lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        elif which_world == 'biocoreworld':
            process_name_to_monitor = 'IDEMIA.DocAuth.BiometricService.exe'
            if not self.process_checker(process_name_to_monitor):
                print("BioCore is NOT running. Please startup DocAuth BEFORE running this PerformanceMonitor.")
                exit(2)
            output_filename = r'c:\Temp\DocAuthPerfData_BioCoreWorld.csv'
            f = open(output_filename, 'wt', buffering=1)
            writer = csv.writer(f, delimiter=',', quotechar=' ', lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        elif which_world == 'ecatworld':
            process_name_to_monitor = 'ECAT.exe'
            if not self.process_checker(process_name_to_monitor):
                print("ECAT is NOT running. Please startup DocAuth BEFORE running this PerformanceMonitor.")
                exit(2)
            output_filename = r'c:\Temp\DocAuthPerfData_EcatWorld.csv'
            f = open(output_filename, 'wt', buffering=1)
            writer = csv.writer(f, delimiter=',', quotechar=' ', lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        elif which_world == 'newworld':
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
        elif which_world == 'oldserviceworld':
            process_name_to_monitor = 'DocAuth.WindowsService.exe'
            if not self.process_checker(process_name_to_monitor):
                print("DocAuth Services is NOT running. Please startup DocAuth BEFORE running this PerformanceMonitor.")
                exit(2)
            output_filename = r'c:\Temp\DocAuthPerfData_OldServiceWorld.csv'
            f = open(output_filename, 'wt', buffering=1)
            writer = csv.writer(f, delimiter=',', quotechar=' ', lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        elif which_world == 'catcworld':
            process_name_to_monitor = 'CATC.exe'
            if not self.process_checker(process_name_to_monitor):
                print("IPS.exe is NOT running. Please startup CATC BEFORE running this PerformanceMonitor.")
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
        elif which_world == 'autocatworld':
            process_name_to_monitor = 'IDEMIA.DocAuth.CAT.App.exe'
            if not self.process_checker(process_name_to_monitor):
                print("IDEMIA.DocAuth.CAT.App.exe is NOT running. Please startup AutoCAT BEFORE running this PerformanceMonitor.")
                exit(2)
            output_filename = r'c:\Temp\DocAuthPerfData_AutocatWorld.csv'
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

        stats_list_mobileDLworld = [r'\Process(MobileDLReaderSampleApp)\Private Bytes',
                                    r'\Process(MobileDLReaderSampleApp)\Virtual Bytes',
                                    r'\Process(MobileDLReaderSampleApp)\Working Set - Private']

        stats_list_dotnetworld = [r'\Process(IDEMIA.DocAuth.DocumentService)\Private Bytes',
                                  r'\Process(IDEMIA.DocAuth.DocumentService)\Virtual Bytes',
                                  r'\Process(IDEMIA.DocAuth.DocumentService)\Working Set - Private']

        stats_list_biocoreworld = [r'\Process(IDEMIA.DocAuth.DocumentService)\Private Bytes',
                                   r'\Process(IDEMIA.DocAuth.DocumentService)\Virtual Bytes',
                                   r'\Process(IDEMIA.DocAuth.DocumentService)\Working Set - Private',
                                   r'\Process(IDEMIA.DocAuth.IdentityAuthentication.App)\Private Bytes',
                                   r'\Process(IDEMIA.DocAuth.IdentityAuthentication.App)\Virtual Bytes',
                                   r'\Process(IDEMIA.DocAuth.IdentityAuthentication.App)\Working Set - Private',
                                   r'\Process(IDEMIA.DocAuth.BiometricService)\Private Bytes',
                                   r'\Process(IDEMIA.DocAuth.BiometricService)\Virtual Bytes',
                                   r'\Process(IDEMIA.DocAuth.BiometricService)\Working Set - Private',
                                   r'\Process(node)\Private Bytes',
                                   r'\Process(node)\Virtual Bytes',
                                   r'\Process(node)\Working Set - Private',
                                   r'\Process(java)\Private Bytes',
                                   r'\Process(java)\Virtual Bytes',
                                   r'\Process(java)\Working Set - Private',
                                   r'\Process(java#1)\Private Bytes',
                                   r'\Process(java#1)\Virtual Bytes',
                                   r'\Process(java#1)\Working Set - Private',
                                   r'\Process(java#2)\Private Bytes',
                                   r'\Process(java#2)\Virtual Bytes',
                                   r'\Process(java#2)\Working Set - Private',
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
                                   r'\Process(IA#1)\Private Bytes',
                                   r'\Process(IA#1)\Virtual Bytes',
                                   r'\Process(IA#1)\Working Set - Private']

        stats_list_ecatworld = [r'\Process(BGExaminer)\Private Bytes',
                                r'\Process(BGExaminer)\Virtual Bytes',
                                r'\Process(BGExaminer)\Working Set - Private',
                                r'\Process(bgServer)\Private Bytes',
                                r'\Process(bgServer)\Virtual Bytes',
                                r'\Process(bgServer)\Working Set - Private',
                                r'\Process(ECAT)\Private Bytes',
                                r'\Process(ECAT)\Virtual Bytes',
                                r'\Process(ECAT)\Working Set - Private',
                                r'\Process(IDEMIA.DocAuth.RegulaService)\Private Bytes',
                                r'\Process(IDEMIA.DocAuth.RegulaService)\Virtual Bytes',
                                r'\Process(IDEMIA.DocAuth.RegulaService)\Working Set - Private',
                                r'\Process(DataAnalysisApiHost)\Private Bytes',
                                r'\Process(DataAnalysisApiHost)\Virtual Bytes',
                                r'\Process(DataAnalysisApiHost)\Working Set - Private']

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

        stats_list_oldserviceworld = [r'\Process(BGExaminer)\Private Bytes',
                                      r'\Process(BGExaminer)\Virtual Bytes',
                                      r'\Process(BGExaminer)\Working Set - Private',
                                      r'\Process(bgServer)\Private Bytes',
                                      r'\Process(bgServer)\Virtual Bytes',
                                      r'\Process(bgServer)\Working Set - Private',
                                      r'\Process(DocAuth.WindowsService)\Private Bytes',
                                      r'\Process(DocAuth.WindowsService)\Virtual Bytes',
                                      r'\Process(DocAuth.WindowsService)\Working Set - Private']

        stats_list_catcworld = [r'\Process(BGExaminer)\Private Bytes',
                                r'\Process(BGExaminer)\Virtual Bytes',
                                r'\Process(BGExaminer)\Working Set - Private',
                                r'\Process(bgServer)\Private Bytes',
                                r'\Process(bgServer)\Virtual Bytes',
                                r'\Process(bgServer)\Working Set - Private',
                                r'\Process(CATC)\Private Bytes',
                                r'\Process(CATC)\Virtual Bytes',
                                r'\Process(CATC)\Working Set - Private',
                                r'\Process(node)\Private Bytes',
                                r'\Process(node)\Virtual Bytes',
                                r'\Process(node)\Working Set - Private',
                                r'\Process(java)\Private Bytes',
                                r'\Process(java)\Virtual Bytes',
                                r'\Process(java)\Working Set - Private',
                                r'\Process(java#1)\Private Bytes',
                                r'\Process(java#1)\Virtual Bytes',
                                r'\Process(java#1)\Working Set - Private',
                                r'\Process(java#2)\Private Bytes',
                                r'\Process(java#2)\Virtual Bytes',
                                r'\Process(java#2)\Working Set - Private',
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
                                r'\Process(IA#1)\Private Bytes',
                                r'\Process(IA#1)\Virtual Bytes',
                                r'\Process(IA#1)\Working Set - Private']

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

        stats_list_autocatworld = [r'\Process(IDEMIA.DocAuth.CAT.App)\Private Bytes',
                                   r'\Process(IDEMIA.DocAuth.CAT.App)\Virtual Bytes',
                                   r'\Process(IDEMIA.DocAuth.CAT.App)\Working Set - Private',
                                   r'\Process(IDEMIA.DocAuth.BiometricService)\Private Bytes',
                                   r'\Process(IDEMIA.DocAuth.BiometricService)\Virtual Bytes',
                                   r'\Process(IDEMIA.DocAuth.BiometricService)\Working Set - Private',
                                   r'\Process(IDEMIA.DocAuth.DocumentService)\Private Bytes',
                                   r'\Process(IDEMIA.DocAuth.DocumentService)\Virtual Bytes',
                                   r'\Process(IDEMIA.DocAuth.DocumentService)\Working Set - Private',
                                   r'\Process(IDEMIA.DocAuth.CAT.StipClientService)\Private Bytes',
                                   r'\Process(IDEMIA.DocAuth.CAT.StipClientService)\Virtual Bytes',
                                   r'\Process(IDEMIA.DocAuth.CAT.StipClientService)\Working Set - Private',
                                   r'\Process(node)\Private Bytes',
                                   r'\Process(node)\Virtual Bytes',
                                   r'\Process(node)\Working Set - Private',
                                   r'\Process(java)\Private Bytes',
                                   r'\Process(java)\Virtual Bytes',
                                   r'\Process(java)\Working Set - Private',
                                   r'\Process(java#1)\Private Bytes',
                                   r'\Process(java#1)\Virtual Bytes',
                                   r'\Process(java#1)\Working Set - Private',
                                   r'\Process(java#2)\Private Bytes',
                                   r'\Process(java#2)\Virtual Bytes',
                                   r'\Process(java#2)\Working Set - Private',
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
                                   r'\Process(IA#1)\Private Bytes',
                                   r'\Process(IA#1)\Virtual Bytes',
                                   r'\Process(IA#1)\Working Set - Private']

        stats_list_esf = [r'\Process(IDEMIA.DocAuth.ESFService)\Private Bytes',
                          r'\Process(IDEMIA.DocAuth.ESFService)\Virtual Bytes',
                          r'\Process(IDEMIA.DocAuth.ESFService)\Working Set - Private']

        # Load the processes to check based on whether oldworld, newworld, catcworld, etc.
        if which_world == 'newworld':
            stats_list = stats_list_newworld
        elif which_world == 'dotnetworld':
            stats_list = stats_list_dotnetworld
        elif which_world == 'mobileDLworld':
            stats_list = stats_list_mobileDLworld
        elif which_world == 'biocoreworld':
            stats_list = stats_list_biocoreworld
        elif which_world == 'ecatworld':
            stats_list = stats_list_ecatworld
        elif which_world == 'catcworld':
            stats_list = stats_list_catcworld
        elif which_world == 'oldworld':
            stats_list = stats_list_oldworld
        elif which_world == 'oldserviceworld':
            stats_list = stats_list_oldserviceworld
        elif which_world == 'autocatworld':
            stats_list = stats_list_autocatworld
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
                # Used to use a list comprehension to interrogate perf data. But needed to interrogate individual
                # perf data in case one or more of them were down.
                # line_of_data = [winstats.get_perf_data(i, fmts='double') for i in stats_list]

                # This is where we REALLY interrogate the statistics.

                line_of_data = []
                line_of_data_esf = []

                for i in stats_list:
                    line_of_data.append(winstats.get_perf_data(i, fmts='double'))

                # Capture ESF data only if 'ESF' argument was given on commandline.

                if choicetemp.esf == 'esf':
                    for i in stats_list_esf:
                        # line_of_data_esf = [winstats.get_perf_data(i, fmts='double') for i in stats_list_esf]
                        line_of_data_esf.append(winstats.get_perf_data(i, fmts='double'))

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
                # print(f"One of the processes was not available for interrogation:", error)
                print(f"Process was not available for interrogation:", self.string_cleaner("badstatname", i))
                time.sleep(self.time_measure_seconds)  # Sleep for time slice, otherwise this keeps throwing message.

            except KeyboardInterrupt as error:  # On ctrl-c from keyboard, flush buffer, close file, exit. Break loop.
                print("\n\nExiting due to user action...")
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
        _fig, ax = plt.subplots(figsize=(16, 9))  # Returns a figure container and a single xy axis chart. Figure is a dummy var.

        # Some workarounds to minimize crazy scientific offset at top left and bottom right of chart.
        # plt.rcParams['axes.formatter.useoffset'] = False   # This did not work
        plt.gca().get_yaxis().get_major_formatter().set_useOffset(False)

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
        # ax.legend(self.reslist)   # Default matplotlib legend printing inside the graph wherever.
        ax.legend(self.reslist, loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=4)  # Prints legend on top outside.

        # Output the chart.  Really only needed if NOT in "interactive mode".
        # If in non-interactive mode, may need to use "plt.show()" instead.
        # fig.show()
        _fig.tight_layout()
        plt.show()

# Run this bitch


def main():
    """Main to run the Perfmonitor."""

    pm = PerfMonitor()

    choice = pm.command_line_arguments()

    # Debugging
    # pm.command_line_arguments()
    # choice = pm.args  # Using this global which i would like to get as a return from command_line_augments() instead.

    # print("Choice: ", choice)

    if choice.subcommand == "record" and choice.world == "oldworld":
        pm.data_collector("oldworld")
    elif choice.subcommand == "record" and choice.world == "oldserviceworld":
        pm.data_collector("oldserviceworld")
    elif choice.subcommand == "record" and choice.world == "newworld":
        pm.data_collector("newworld")
    elif choice.subcommand == "record" and choice.world == "ecatworld":
        pm.data_collector("ecatworld")
    elif choice.subcommand == "record" and choice.world == "biocoreworld":
        pm.data_collector("biocoreworld")
    elif choice.subcommand == "record" and choice.world == "mobileDLworld":
        pm.data_collector("mobileDLworld")
    elif choice.subcommand == "record" and choice.world == "dotnetworld":
        pm.data_collector("dotnetworld")
    elif choice.subcommand == "record" and choice.world == "catcworld":
        pm.data_collector("catcworld")
    elif choice.subcommand == "record" and choice.world == "audiodgworld":
        pm.data_collector("audiodgworld")
    elif choice.subcommand == "record" and choice.world == "autocatworld":
        pm.data_collector("autocatworld")
    elif choice.subcommand == "report" and choice.world == "oldworld":
        pm.file_reader(r"c:\Temp\DocAuthPerfData_OldWorld.csv")
        pm.data_plotter()
    elif choice.subcommand == "report" and choice.world == "oldserviceworld":
        pm.file_reader(r"c:\Temp\DocAuthPerfData_OldServiceWorld.csv")
        pm.data_plotter()
    elif choice.subcommand == "report" and choice.world == "newworld":
        pm.file_reader(r"c:\Temp\DocAuthPerfData.csv")
        pm.data_plotter()
    elif choice.subcommand == "report" and choice.world == "ecatworld":
        pm.file_reader(r"c:\Temp\DocAuthPerfData_EcatWorld.csv")
        pm.data_plotter()
    elif choice.subcommand == "report" and choice.world == "mobileDLworld":
        pm.file_reader(r"c:\Temp\DocAuthPerfData_MobileDLReaderSampleAppWorld.csv")
        pm.data_plotter()
    elif choice.subcommand == "report" and choice.world == "biocoreworld":
        pm.file_reader(r"c:\Temp\DocAuthPerfData_BioCoreWorld.csv")
        pm.data_plotter()
    elif choice.subcommand == "report" and choice.world == "dotnetworld":
        pm.file_reader(r"c:\Temp\DocAuthPerfData_DotNetWorld.csv")
        pm.data_plotter()
    elif choice.subcommand == "report" and choice.world == "catcworld":
        pm.file_reader(r"c:\Temp\DocAuthPerfData_CatcWorld.csv")
        pm.data_plotter()
    elif choice.subcommand == "report" and choice.world == "audiodgworld":
        pm.file_reader(r"c:\Temp\DocAuthPerfData_Audiodg.csv")
        pm.data_plotter()
    elif choice.subcommand == "report" and choice.world == "autocatworld":
        pm.file_reader(r"c:\Temp\DocAuthPerfData_AutocatWorld.csv")
        pm.data_plotter()


if __name__ == "__main__":
    main()
