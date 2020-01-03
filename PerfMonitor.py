import sys
from sys import exit, argv  # Have to specific import these so packaging/freezing works
import os.path
import argparse
import psutil
import csv
import winstats
import numpy
import matplotlib.pyplot as plt
import time
import datetime as dt
import re


class PerfMonitor:
    """Performance Monitoring for Idemia DocAuth"""
    args = ''
    data = []
    time_measure_seconds = 60  # Number of seconds between consecutive data captures.
    time_max_ticks = 0  # Will be computed from the "hours" argument in the command line.
    monitored_process_name = ""
    monitored_pid = 0
    monitored_pid_counter = 0

    def get_value(self, value):
        return float(value)

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
            parser.add_argument('world', choices=['oldworld', 'newworld'], type=str, help='oldworld or newworld')
            parser.add_argument('action', choices=['record', 'report', 'all'], type=str, help='record | report | all')
            parser.add_argument('esf', choices=['esf', 'noesf'], type=str, help='esf | noesf')
            parser.add_argument('hours', type=int, help='number of hours')
            args = parser.parse_args()
            #print("Commandline def: ", args.esf)

            #self.time_max_ticks = args.hours * 120  # mult by 120 because every 30 seconds a measure is taken. Twice a min.
            self.time_max_ticks = args.hours * 60  # mult by 60 because every 60 seconds a measure is taken. Once a min.

            return args
        except Exception as err:
            print(err)
            # exit(2)

    def string_cleaner(self, temp_string_buffer):
        """ Routine to strip brackets, parens, extra commas, etc from string buffer before writing to csv file """
        # Strip brackets, single quotes, parens from buffer. Matplotlib seems to handover data with commas at the end.
        tempstring = (str(temp_string_buffer).translate(str.maketrans( {'[': '', ']': '', '\'': '', ')': '', '(': ''})))
        tempstring = re.sub( r',,', ',', tempstring )  # Remove double commas
        tempstring = re.sub( r',$', '', tempstring )  # Remove Trailing comma
        return(tempstring)

    def data_collector(self):
        """Collect performance data via winstats library. Then write each line of data to csv file"""

        choicetemp = self.command_line_arguments()

        # Verify that DocAuth IS running.
        if not self.process_checker('IDEMIA.DocAuth.Document.App.exe'):
            print("DocAuth is NOT running. Please startup DocAuth BEFORE running this PerformanceMonitor.")
            exit(2)
        print("\nVerified that DocAuth IS running. Recording data for ", choicetemp.hours, " hours...")
        print("CTRL-C to stop recording earlier.")

        output_filename = r'c:\Temp\DocAuthPerfData.csv'
        f = open(output_filename, 'wt', buffering=1)
        writer = csv.writer(f, delimiter=',', quotechar=' ', lineterminator='\n', quoting=csv.QUOTE_MINIMAL)

        # Run through ticks (time) for x-axis.

        stats_list = [r'\Process(IDEMIA.DocAuth.Document.App)\Private Bytes',
                      r'\Process(IDEMIA.DocAuth.Document.App)\Virtual Bytes',
                      r'\Process(IDEMIA.DocAuth.RegulaService)\Private Bytes',
                      r'\Process(IDEMIA.DocAuth.RegulaService)\Virtual Bytes',
                      r'\Process(IDEMIA.DocAuth.LinecodeService)\Private Bytes',
                      r'\Process(IDEMIA.DocAuth.LinecodeService)\Virtual Bytes']

        stats_list_esf = [r'\Process(IDEMIA.DocAuth.ESFService)\Private Bytes',
                          r'\Process(IDEMIA.DocAuth.ESFService)\Virtual Bytes']

        for ticks in range(self.time_max_ticks):  # 1440 = 12 hours for 30 second tick | 4320 = 36 hours

            # New World processes
            time_track = dt.datetime.fromtimestamp(time.time())  # Get timestamp-style time
            time_track = time_track.strftime("%m/%d/%y %H:%M")   # Keep "m/d/y h/m" drop seconds.milliseconds
            print(time_track, end=" ")

            try:

                # Using a list comprehension instead of a bunch of variables.
                line_of_data = [winstats.get_perf_data(i, fmts='double') for i in stats_list]

                # Capture ESF data only if 'ESF' argument was given on commandline.
                choicetemp = self.command_line_arguments()
                if choicetemp.esf == 'esf':

                    line_of_data_esf = [winstats.get_perf_data(i, fmts='double') for i in stats_list_esf]

                    # Write a row of stats to the csv file including ESF stats.
                    writer.writerow((time_track, self.string_cleaner(line_of_data), self.string_cleaner(line_of_data_esf)))
                else:
                    # @@@@@Write a row of stats to the csv file NOT including ESF stats.
                    # temp_string = self.string_cleaner(line_of_data)
                    # writer.writerow((time_track, line_of_data))
                    writer.writerow((time_track, self.string_cleaner(line_of_data)))

                # Output test status to console.
                print(" tick:", ticks, "of", self.time_max_ticks, " name:", self.monitored_process_name, " pid:",
                      self.monitored_pid, ", was restarted ", self.monitored_pid_counter, " times.")

                # See if the DocAuth service has restarted. IF there is a new pid, then it did restart.
                self.process_checker('IDEMIA.DocAuth.Document.App.exe')

                time.sleep(self.time_measure_seconds)  # Sleep for time slice

            except WindowsError as error:  # If one of the processes is down, winstat errors out, so handle it. Continue the loop.
                print(f"One of the processes was not available for interrogation by winstat.. Regula? :)")
                time.sleep(self.time_measure_seconds)  # Sleep for time slice, otherwise this keeps throwing message.

            except KeyboardInterrupt as error:  # On ctrl-c from keyboard, flush buffer, close file, exit. Break loop.
                print("\n\nExiting...")
                break

        f.close()

        # Print out how many times Regula service was restarted
        print("\nData was collected and stored in file: ", output_filename)
        print(self.monitored_process_name, " was restarted ", self.monitored_pid_counter, " times.")

        return

    def data_collector_oldworld(self):
        """Collect performance data of DocAuth OldWorld via winstats library.
        Then write each line of data to csv file."""

        choicetemp = self.command_line_arguments()

        # Verify that DocAuth IS running.
        if not self.process_checker('DocAuth.Applications.Authenticate.exe'):
            print("DocAuth is NOT running. Please startup DocAuth BEFORE running this PerformanceMonitor.")
            exit(2)
        print("\nVerified that DocAuth IS running. Recording data for ", choicetemp.hours, " hours...")
        print("CTRL-C to stop recording earlier.")

        output_filename = r'c:\Temp\DocAuthPerfData_OldWorld.csv'
        f = open(output_filename, 'wt', buffering=1)
        writer = csv.writer(f, delimiter=',', quotechar='"', lineterminator='\n')

        # Run through ticks (time) for x-axis.
        

        for ticks in range(self.time_max_ticks):  # 1440 = 12 hours for 30 second tick | 4320 = 36 hours
            # New World processes
            time_track = dt.datetime.fromtimestamp(time.time())  # Get timestamp-style time
            time_track = time_track.strftime("%m/%d/%y %H:%M")   # Keep "m/d/y h/m" drop seconds.milliseconds
            print(time_track, end=" ")

            try:
                usage1 = winstats.get_perf_data(r'\Process(BGExaminer)\Private Bytes', fmts='double')
                usage1 = float(usage1[0])
                usage2 = winstats.get_perf_data(r'\Process(BGExaminer)\Virtual Bytes', fmts='double')
                usage2 = float(usage2[0])
                usage3 = winstats.get_perf_data(r'\Process(bgServer)\Private Bytes', fmts='double')
                usage3 = float(usage3[0])
                usage4 = winstats.get_perf_data(r'\Process(bgServer)\Virtual Bytes', fmts='double')
                usage4 = float(usage4[0])
                usage5 = winstats.get_perf_data(r'\Process(DocAuth.Applications.Authenticate)\Private Bytes',
                                                fmts='double')
                usage5 = float(usage5[0])
                usage6 = winstats.get_perf_data(r'\Process(DocAuth.Applications.Authenticate)\Virtual Bytes',
                                                fmts='double')
                usage6 = float(usage6[0])
                usage7 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.RegulaService)\Private Bytes', fmts='double')
                usage7 = float(usage7[0])
                usage8 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.RegulaService)\Virtual Bytes', fmts='double')
                usage8 = float(usage8[0])

                # Write a row of stats to the csv file.
                writer.writerow((time_track, usage1, usage2, usage3, usage4, usage5, usage6, usage7, usage8))
                # Output test status to console.
                print(" tick:", ticks, "of", self.time_max_ticks, " name:", self.monitored_process_name, " pid:",
                      self.monitored_pid, ", was restarted ", self.monitored_pid_counter, " times.")

                # See if the Monitored service has restarted. IF there is a new pid, then it did restart.
                self.process_checker('DocAuth.Applications.Authenticate.exe')  # Inc count if service restarted.

                time.sleep(self.time_measure_seconds)  # Sleep for time slice

            except WindowsError as error:  # If a processes is down, winstat errors out, so handle it.
                print(f"One of the processes was not available for interrogation by winstat.. Regula? :)")
                time.sleep(self.time_measure_seconds)  # Sleep for time slice, otherwise this keeps throwing message.

            except KeyboardInterrupt as error:  # On ctrl-c from keyboard, flush buffer, close file, exit. Break loop.
                print("\n\nExiting...")
                break

        f.close()

        # Print out how many times Monitored service was restarted
        print("\nData was collected and stored in file: ", output_filename)
        print(self.monitored_process_name, " was restarted ", self.monitored_pid_counter, " times.")

        return

    def file_reader(self, input_filename):
        """Read in csv performance file, line by line"""

        #input_filename = r"c:\Temp\DocAuthPerfData.csv"

        if not os.path.isfile(input_filename):  # Check for existing csv file.
            print("File name: ", input_filename, " does not exist. Maybe you need to record data first ?")
            exit(2)
        if os.path.getsize(input_filename) == 0:  # Check for empty csv file.
            print("File name: ", input_filename, " is empty. Maybe your last recording did not work ?")
            exit(2)

        f = open(input_filename, 'rt')
        with f:
            reader = csv.reader(f)
            for x_row in reader:
                PerfMonitor.data.append(x_row)
        f.close()
        return PerfMonitor.data


    def data_plotter_oldworld(self):
        """Plot performance data from csv file using winstats library"""
        a = numpy.array(PerfMonitor.data)
        time_track = a[:, 0]  # Extract Timestamps (as string)

        # Figure out how many hours worth of data came from the csv file
        # total_elapsed_time = (len(a) / 2) / 60   # (/2 for 30 second interval the /60 to get hours)
        total_elapsed_time = (len(a) / 60)   # (/60 to get hours)
        total_elapsed_time = round(total_elapsed_time, 2)

        # Extract data from columns 2 to 7 and (convert to floats).
        bgexaminer_private_bytes = a[:, 1]
        bgexaminer_private_bytes = numpy.asfarray(bgexaminer_private_bytes, float)
        bgexaminer_virtual_bytes = a[:, 2]
        bgexaminer_virtual_bytes = numpy.asfarray(bgexaminer_virtual_bytes, float)
        bgserver_private_bytes = a[:, 3]
        bgserver_private_bytes = numpy.asfarray(bgserver_private_bytes, float)
        bgserver_virtual_bytes = a[:, 4]
        bgserver_virtual_bytes = numpy.asfarray(bgserver_virtual_bytes, float)
        docauthapp_private_bytes = a[:, 5]
        docauthapp_private_bytes = numpy.asfarray(docauthapp_private_bytes, float)
        docauthapp_virtual_bytes = a[:, 6]
        docauthapp_virtual_bytes = numpy.asfarray(docauthapp_virtual_bytes, float)
        docauth_regulaservice_private_bytes = a[:, 7]
        docauth_regulaservice_private_bytes = numpy.asfarray(docauth_regulaservice_private_bytes, float)
        docauth_regulaservice_virtual_bytes = a[:, 8]
        docauth_regulaservice_virtual_bytes = numpy.asfarray(docauth_regulaservice_virtual_bytes, float)

        # Create cartesian plane, draw labels and title
        fig, ax = plt.subplots()  # Returns a figure container and a single xy axis chart

        # Build chart title and include number of hours that the test ran for.
        chart_title = "Bricktest memory utilization ran for " + str(total_elapsed_time) + " hour(s)"
        ax.set_title(chart_title)

        ax.set_xlabel('Date/Time')
        ax.set_ylabel('Memory in Megabytes')
        ax.xaxis.set_major_locator(plt.MaxNLocator(20))  # Display a max of 20 x-axis time ticks

        # Plot the data
        ax.plot(time_track, bgexaminer_private_bytes / 1000000, time_track, bgexaminer_virtual_bytes / 10000000,
                time_track, bgserver_private_bytes / 1000000, time_track, bgserver_virtual_bytes / 1000000,
                time_track, docauthapp_private_bytes / 1000000, time_track, docauthapp_virtual_bytes / 1000000,
                time_track, docauth_regulaservice_private_bytes / 1000000, time_track, docauth_regulaservice_virtual_bytes / 1000000)

        ax.grid(True)
        ax.figure.autofmt_xdate()
        ax.legend(['bgexaminer private', 'bgexaminer virtual', 'bgserver private', 'bgserver virtual',
                   'docauth private', 'docauth virtual', 'regula private', 'regula virtual'])

        # Output the chart.  Really only needed if NOT in "interactive mode".
        # If in non-interactive mode, may need to use "plt.show()" instead.
        #fig.show()
        plt.show()

        return

    def data_plotter(self):
        """Plot performance data from csv file using winstats library"""
        a = numpy.array(PerfMonitor.data)
        time_track = a[:, 0]  # Extract Timestamps (as string)

        # Figure out how many hours worth of data came from the csv file
        # total_elapsed_time = (len(a) / 2) / 60   # (/2 for 30 second interval the /60 to get hours)
        total_elapsed_time = (len(a) / 60)   # (/60 to get hours)
        total_elapsed_time = round(total_elapsed_time, 2)

        # Extract data from columns 2 to 8 and (convert to floats).
        idemia_app_private_bytes = a[:, 1]
        idemia_app_private_bytes = numpy.asfarray(idemia_app_private_bytes, float)
        idemia_app_virtual_bytes = a[:, 2]
        idemia_app_virtual_bytes = numpy.asfarray(idemia_app_virtual_bytes, float)
        idemia_regula_private_bytes = a[:, 3]
        idemia_regula_private_bytes = numpy.asfarray(idemia_regula_private_bytes, float)
        idemia_regula_virtual_bytes = a[:, 4]
        idemia_regula_virtual_bytes = numpy.asfarray(idemia_regula_virtual_bytes, float)
        idemia_linecode_private_bytes = a[:, 5]
        idemia_linecode_private_bytes = numpy.asfarray(idemia_linecode_private_bytes, float)
        idemia_linecode_virtual_bytes = a[:, 6]
        idemia_linecode_virtual_bytes = numpy.asfarray(idemia_linecode_virtual_bytes, float)

        # Output ESF data only if 'ESF' argument was given on commandline.
        choicetemp = self.command_line_arguments()
        if (choicetemp.esf == 'esf'):
            idemia_esf_private_bytes = a[:, 7]
            idemia_esf_private_bytes = numpy.asfarray(idemia_esf_private_bytes, float)
            idemia_esf_virtual_bytes = a[:, 8]
            idemia_esf_virtual_bytes = numpy.asfarray(idemia_esf_virtual_bytes, float)

        # Create cartesian plane, draw labels and title
        fig, ax = plt.subplots()  # Returns a figure container and a single xy axis chart

        # Build chart title and include number of hours that the test ran for.
        chart_title = "Bricktest memory utilization ran for " + str(total_elapsed_time) + " hour(s)"
        ax.set_title(chart_title)

        ax.set_xlabel('Date/Time')
        ax.set_ylabel('Memory in Gigabytes')
        ax.xaxis.set_major_locator(plt.MaxNLocator(20))  # Display a max of 20 x-axis time ticks

        # Plot the data only if 'ESF' argument was given on commandline.
        if (choicetemp.esf == 'esf'):
            ax.plot(time_track, idemia_app_private_bytes / 1000000000, time_track, idemia_app_virtual_bytes / 1000000000,
                time_track, idemia_regula_private_bytes / 1000000000, time_track, idemia_regula_virtual_bytes / 1000000000,
                time_track, idemia_linecode_private_bytes / 1000000000, time_track, idemia_linecode_virtual_bytes / 1000000000,
                time_track, idemia_esf_private_bytes / 1000000000, time_track, idemia_esf_virtual_bytes / 1000000000)
        else:
            ax.plot(time_track, idemia_app_private_bytes / 1000000000, time_track, idemia_app_virtual_bytes / 1000000000,
                time_track, idemia_regula_private_bytes / 1000000000, time_track, idemia_regula_virtual_bytes / 1000000000,
                time_track, idemia_linecode_private_bytes / 1000000000, time_track, idemia_linecode_virtual_bytes / 1000000000)

        # More grid preparations
        ax.grid(True)
        ax.figure.autofmt_xdate()

        if (choicetemp.esf == 'esf'):  # Output proper chart legend with or without ESF.
            ax.legend(['DocAuth private', 'DocAuth virtual', 'Regula private', 'Regula virtual',
                   'Linecode private', 'Linecode virtual', 'ESF private', 'ESF virtual'])
        else:
            ax.legend(['DocAuth private', 'DocAuth virtual', 'Regula private', 'Regula virtual',
                   'Linecode private', 'Linecode virtual'])

        # Output the chart.  Really only needed if NOT in "interactive mode".
        # If in non-interactive mode, may need to use "plt.show()" instead.
        #fig.show()
        plt.show()

        return

# Run this bitch


def main():

    pm = PerfMonitor()

    choice = pm.command_line_arguments()

    if choice.action == "record" and choice.world == "oldworld":
        pm.data_collector_oldworld()
    elif choice.action == "record" and choice.world == "newworld":
        pm.data_collector()
    elif choice.action == "report" and choice.world == "oldworld":
        # pm.file_reader_oldworld()
        pm.file_reader(r"c:\Temp\DocAuthPerfData_OldWorld.csv")
        pm.data_plotter_oldworld()
    elif choice.action == "report" and choice.world == "newworld":
        pm.file_reader(r"c:\Temp\DocAuthPerfData.csv")
        pm.data_plotter()
    elif choice.action == "all" and choice.world == "oldworld":
        pm.data_collector_oldworld()
        # pm.file_reader_oldworld()
        pm.file_reader(r"c:\Temp\DocAuthPerfData_OldWorld.csv")
        pm.data_plotter_oldworld()
    else:  # Assuming 'all' and 'newworld'
        pm.data_collector()
        pm.file_reader(r"c:\Temp\DocAuthPerfData.csv")
        pm.data_plotter()


if __name__ == "__main__":
    main()
