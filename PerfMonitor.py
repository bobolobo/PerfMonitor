import sys
from sys import exit, argv  # Have to specific import these so packaging/freezing works
import argparse
import psutil
import csv
import winstats
import numpy
import matplotlib.pyplot as plt
import time
import datetime as dt


class PerfMonitor:
    """Performance Monitoring for Idemia DocAuth"""
    args = ''
    data = []
    time_measure_seconds = 30  # Number of seconds between consecutive data captures.
    time_max_ticks = 2880   # Max number of ticks to capture data. 1440 = 12 hours for 30 second ticks | 4320 = 36 hours.
    regula_process_name = ""
    regula_pid = 0
    regula_pid_counter = 0

    def process_checker_oldworld(self):
        """Verify that some IDEMIA... processes are running"""
        for p in psutil.process_iter():
            if 'DocAuth.Applications.Authenticate.exe' in p.name():
                return True
        return False

    def process_checker(self):
        """Verify that some IDEMIA... processes are running"""
        for p in psutil.process_iter():
            if 'IDEMIA.DocAuth.RegulaService.exe' in p.name():
                if self.regula_pid == 0:  # If this is the first time through, capture the name and pid.
                    self.regula_process_name = p.name()
                    self.regula_pid = p.pid
                elif self.regula_pid != p.pid:
                    self.regula_pid_counter += 1  # Track times that Regula has restarted
                    self.regula_pid = p.pid       # Get new pid value for Regula service
                return True
        return False

    def command_line_arguments(self):
        """Read and evaluate commandline arguments, returns the single commandline argument"""

        try:
            parser = argparse.ArgumentParser(description='Performance Monitoring for Idemia DocAuth')
            parser.add_argument('world', choices=['oldworld', 'newworld'], type=str, help='oldworld or newworld')
            parser.add_argument('action', choices=['record', 'report', 'all'], type=str, help='record | report | all')
            args = parser.parse_args()
            #print(args.world, args.action)
            return(args)
        except Exception as err:
            print(err)
            #exit(2)

    def data_collector(self):
        """Collect performance data via winstats library. Then write each line of data to csv file"""

        # Verify that DocAuth IS running.
        if not self.process_checker():
            print("DocAuth is NOT running. Please startup DocAuth BEFORE running this PerformanceMonitor.")
            exit(2)
        print("Verified that DocAuth IS running. \nRecording data...")

        output_filename = r'c:\Temp\DocAuthPerfData.csv'
        f = open(output_filename, 'wt')
        writer = csv.writer(f, delimiter=',', quotechar='"', lineterminator='\n')

        # Run through ticks (time) for x-axis.

        for ticks in range(self.time_max_ticks):  # 1440 = 12 hours for 30 second tick | 4320 = 36 hours
            # New World processes
            time_track = dt.datetime.fromtimestamp(time.time())  # Get timestamp-style time
            time_track = time_track.strftime("%m/%d/%y %H:%M")   # Keep "m/d/y h/m" drop seconds.milliseconds
            print(time_track, end=" ")

            try:
                usage1 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.Document.App)\Private Bytes', fmts='double',
                                                delay=1000)
                usage1 = float(usage1[0])
                usage2 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.Document.App)\Virtual Bytes', fmts='double',
                                                delay=1000)
                usage2 = float(usage2[0])
                usage3 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.Document.App)\Working Set', fmts='double',
                                                delay=1000)
                usage3 = float(usage3[0])
                usage4 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.RegulaService)\Private Bytes', fmts='double',
                                                delay=1000)
                usage4 = float(usage4[0])
                usage5 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.RegulaService)\Virtual Bytes', fmts='double',
                                                delay=1000)
                usage5 = float(usage5[0])
                usage6 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.RegulaService)\Working Set', fmts='double',
                                                delay=1000)
                usage6 = float(usage6[0])

                # Write a row of stats to the csv file.
                writer.writerow((time_track, usage1, usage2, usage3, usage4, usage5, usage6))
                # Output test status to console.
                print(" tick:", ticks,"of", self.time_max_ticks, " name:", self.regula_process_name, " pid:", self.regula_pid, ", was restarted ",
                      self.regula_pid_counter, " times.")

                # See if the Regula service has restarted. IF there is a new pid, then it did restart.
                self.process_checker()  # See if Regula service has been restarted, if yes then increment counter.

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
        print(self.regula_process_name, " was restarted ", self.regula_pid_counter, " times.")

        return

    def data_collector_oldworld(self):
        """Collect performance data of DocAuth OldWorld via winstats library. Then write each line of data to csv file"""

        # Verify that DocAuth IS running.
        if not self.process_checker():
            print("DocAuth is NOT running. Please startup DocAuth BEFORE running this PerformanceMonitor.")
            exit(2)
        print("Verified that DocAuth IS running. \nRecording data...")

        output_filename = r'c:\Temp\DocAuthPerfData.csv'
        f = open(output_filename, 'wt')
        writer = csv.writer(f, delimiter=',', quotechar='"', lineterminator='\n')

        # Run through ticks (time) for x-axis.

        for ticks in range(self.time_max_ticks):  # 1440 = 12 hours for 30 second tick | 4320 = 36 hours
            # New World processes
            time_track = dt.datetime.fromtimestamp(time.time())  # Get timestamp-style time
            time_track = time_track.strftime("%m/%d/%y %H:%M")   # Keep "m/d/y h/m" drop seconds.milliseconds
            print(time_track, end=" ")

            try:
                usage1 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.Document.App)\Private Bytes', fmts='double',
                                                delay=1000)
                usage1 = float(usage1[0])
                usage2 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.Document.App)\Virtual Bytes', fmts='double',
                                                delay=1000)
                usage2 = float(usage2[0])
                usage3 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.Document.App)\Working Set', fmts='double',
                                                delay=1000)
                usage3 = float(usage3[0])
                usage4 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.RegulaService)\Private Bytes', fmts='double',
                                                delay=1000)
                usage4 = float(usage4[0])
                usage5 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.RegulaService)\Virtual Bytes', fmts='double',
                                                delay=1000)
                usage5 = float(usage5[0])
                usage6 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.RegulaService)\Working Set', fmts='double',
                                                delay=1000)
                usage6 = float(usage6[0])

                # Write a row of stats to the csv file.
                writer.writerow((time_track, usage1, usage2, usage3, usage4, usage5, usage6))
                # Output test status to console.
                print(" tick:", ticks,"of", self.time_max_ticks, " name:", self.regula_process_name, " pid:", self.regula_pid, ", was restarted ",
                      self.regula_pid_counter, " times.")

                # See if the Regula service has restarted. IF there is a new pid, then it did restart.
                self.process_checker()  # See if Regula service has been restarted, if yes then increment counter.

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
        print(self.regula_process_name, " was restarted ", self.regula_pid_counter, " times.")

        return

    def file_reader(self):
        """Read in csv performance file, line by line"""

        input_filename = r"c:\Temp\DocAuthPerfData.csv"
        f = open(input_filename, 'rt')
        with f:
            reader = csv.reader(f)
            for x_row in reader:
                PerfMonitor.data.append(x_row)
        f.close()
        return PerfMonitor.data

    def data_plotter(self):
        """Plot performance data from csv file using winstats library"""
        a = numpy.array(PerfMonitor.data)
        time_track = a[:, 0]  # Extract Timestamps (as string)

        # Extract data from columns 2 to 7 and (convert to floats).
        idemia_app_private_bytes = a[:, 1]
        idemia_app_private_bytes = numpy.asfarray(idemia_app_private_bytes, float)
        idemia_app_virtual_bytes = a[:, 2]
        idemia_app_virtual_bytes = numpy.asfarray(idemia_app_virtual_bytes, float)
        idemia_app_working_set = a[:, 3]
        idemia_app_working_set = numpy.asfarray(idemia_app_working_set, float)
        idemia_regula_private_bytes = a[:, 4]
        idemia_regula_private_bytes = numpy.asfarray(idemia_regula_private_bytes, float)
        idemia_regula_virtual_bytes = a[:, 5]
        idemia_regula_virtual_bytes = numpy.asfarray(idemia_regula_virtual_bytes, float)
        idemia_regula_working_set = a[:, 6]
        idemia_regula_working_set = numpy.asfarray(idemia_regula_working_set, float)

        # Create cartesian plane, draw labels and title
        fig = plt.figure()
        ax = fig.add_subplot()

        plt.xlabel('Date/Time')
        plt.ylabel('Memory in Gigbytes')
        plt.title('Bricktest memory utilization')

        ax.xaxis.set_major_locator(plt.MaxNLocator(20))  # Display a max of 20 x-axis time ticks

        # Plot the data
        plt.plot(time_track, idemia_app_private_bytes / 1000000000, time_track, idemia_app_virtual_bytes / 1000000000, time_track,
                 idemia_app_working_set / 1000000000, time_track, idemia_regula_private_bytes / 1000000000, time_track,
                 idemia_regula_virtual_bytes / 1000000000, time_track, idemia_regula_working_set / 1000000000)

        plt.grid(True)
        plt.gcf().autofmt_xdate()
        plt.legend(['IDEMIA private', 'IDEMIA virtual', 'IDEMIA working set', 'Regula private', 'Regula virtual',
                    'Regula working set'])

        plt.show()

        return


# Run this bitch

def main():
    pm = PerfMonitor()

    choice = pm.command_line_arguments()
    #print("Printing args from Main", choice)

    # NEED TO ADD oldworld vs newworld selection
    if choice.action == "record":
        # PHASE 1: Capture performance data to CSV file
        pm.data_collector()
    elif choice.action == "report":  # Tested and PASSED
        # PHASE 2: Plot performance data from CSV capture file
        pm.file_reader()
        pm.data_plotter()
    elif choice.action == "all":
        # PHASE 1: Capture performance data to CSV file
        pm.data_collector()
        # PHASE 2: Plot performance data from CSV capture file
        pm.file_reader()
        pm.data_plotter()


if __name__ == "__main__":
    main()
