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
    time_max_ticks = 120   # Max number of ticks to capture data. 1440 = 12 hours for 30 second ticks | 4320 = 36 hours.
    monitored_process_name = ""
    monitored_pid = 0
    monitored_pid_counter = 0

    def process_checker_oldworld(self):
        """Verify that some IDEMIA... processes are running"""
        for p in psutil.process_iter():
            if 'DocAuth.Applications.Authenticate.exe' in p.name():
                if self.monitored_pid == 0:  # If this is the first time through, capture the name and pid.
                    self.monitored_process_name = p.name()
                    self.monitored_pid = p.pid
                elif self.monitored_pid != p.pid:
                    self.monitored_pid_counter += 1  # Track times that Regula has restarted
                    self.monitored_pid = p.pid       # Get new pid value for Regula service
                return True
        return False

    def process_checker(self):
        """Verify that some IDEMIA... processes are running"""
        for p in psutil.process_iter():
            if 'IDEMIA.DocAuth.RegulaService.exe' in p.name():
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
            args = parser.parse_args()
            # print(args.world, args.action)
            return(args)
        except Exception as err:
            print(err)
            # exit(2)

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
                usage3 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.RegulaService)\Private Bytes', fmts='double',
                                                delay=1000)
                usage3 = float(usage3[0])
                usage4 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.RegulaService)\Virtual Bytes', fmts='double',
                                                delay=1000)
                usage4 = float(usage4[0])
                usage5 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.ESFService)\Private Bytes', fmts='double',
                                                delay=1000)
                usage5 = float(usage5[0])
                usage6 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.ESFService)\Virtual Bytes', fmts='double',
                                                delay=1000)
                usage6 = float(usage6[0])
                usage7 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.LinecodeService)\Private Bytes', fmts='double',
                                                delay=1000)
                usage7 = float(usage7[0])
                usage8 = winstats.get_perf_data(r'\Process(IDEMIA.DocAuth.LinecodeService)\Virtual Bytes', fmts='double',
                                                delay=1000)
                usage8 = float(usage8[0])

                # Write a row of stats to the csv file.
                writer.writerow((time_track, usage1, usage2, usage3, usage4, usage5, usage6, usage7, usage8))
                # Output test status to console.
                print(" tick:", ticks,"of", self.time_max_ticks, " name:", self.monitored_process_name, " pid:", self.monitored_pid, ", was restarted ",
                      self.monitored_pid_counter, " times.")

                # See if the DocAuth service has restarted. IF there is a new pid, then it did restart.
                self.process_checker_oldworld()

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
        """Collect performance data of DocAuth OldWorld via winstats library. Then write each line of data to csv file"""

        # Verify that DocAuth IS running.
        if not self.process_checker_oldworld():
            print("DocAuth is NOT running. Please startup DocAuth BEFORE running this PerformanceMonitor.")
            exit(2)
        print("Verified that DocAuth IS running. \nRecording data...")

        output_filename = r'c:\Temp\DocAuthPerfData_OldWorld.csv'
        f = open(output_filename, 'wt')
        writer = csv.writer(f, delimiter=',', quotechar='"', lineterminator='\n')

        # Run through ticks (time) for x-axis.

        for ticks in range(self.time_max_ticks):  # 1440 = 12 hours for 30 second tick | 4320 = 36 hours
            # New World processes
            time_track = dt.datetime.fromtimestamp(time.time())  # Get timestamp-style time
            time_track = time_track.strftime("%m/%d/%y %H:%M")   # Keep "m/d/y h/m" drop seconds.milliseconds
            print(time_track, end=" ")

            try:
                usage1 = winstats.get_perf_data(r'\Process(BGExaminer)\Private Bytes', fmts='double',
                                                delay=1000)
                usage1 = float(usage1[0])
                usage2 = winstats.get_perf_data(r'\Process(BGExaminer)\Virtual Bytes', fmts='double',
                                                delay=1000)
                usage2 = float(usage2[0])
                usage3 = winstats.get_perf_data(r'\Process(bgServer)\Private Bytes', fmts='double',
                                                delay=1000)
                usage3 = float(usage3[0])
                usage4 = winstats.get_perf_data(r'\Process(bgServer)\Virtual Bytes', fmts='double',
                                                delay=1000)
                usage4 = float(usage4[0])
                usage5 = winstats.get_perf_data(r'\Process(DocAuth.Applications.Authenticate)\Private Bytes', fmts='double',
                                                delay=1000)
                usage5 = float(usage5[0])
                usage6 = winstats.get_perf_data(r'\Process(DocAuth.Applications.Authenticate)\Virtual Bytes', fmts='double',
                                                delay=1000)
                usage6 = float(usage6[0])
                usage7 = winstats.get_perf_data(r'\Process(DataAnalysisApiHost)\Private Bytes', fmts='double',
                                                delay=1000)
                usage7 = float(usage7[0])
                usage8 = winstats.get_perf_data(r'\Process(DataAnalysisApiHost)\Virtual Bytes', fmts='double',
                                                delay=1000)
                usage8 = float(usage8[0])

                # Write a row of stats to the csv file.
                writer.writerow((time_track, usage1, usage2, usage3, usage4, usage5, usage6, usage7, usage8))
                # Output test status to console.
                print(" tick:", ticks,"of", self.time_max_ticks, " name:", self.monitored_process_name, " pid:", self.monitored_pid, ", was restarted ",
                      self.monitored_pid_counter, " times.")

                # See if the Monitored service has restarted. IF there is a new pid, then it did restart.
                self.process_checker_oldworld()  # See if Regula service has been restarted, if yes then increment counter.

                time.sleep(self.time_measure_seconds)  # Sleep for time slice

            except WindowsError as error:  # If one of the processes is down, winstat errors out, so handle it. Continue the loop.
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

    def file_reader_oldworld(self):
        """Read in csv performance file, line by line"""

        input_filename = r"c:\Temp\DocAuthPerfData_OldWorld.csv"
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
        dataanalysisapihost_private_bytes = a[:, 7]
        dataanalysisapihost_private_bytes = numpy.asfarray(dataanalysisapihost_private_bytes, float)
        dataanalysisapihost_virtual_bytes = a[:, 8]
        dataanalysisapihost_virtual_bytes = numpy.asfarray(dataanalysisapihost_virtual_bytes, float)

        # Create cartesian plane, draw labels and title
        fig = plt.figure()
        ax = fig.add_subplot()

        plt.xlabel('Date/Time')
        plt.ylabel('Memory in Megabytes')
        plt.title('Bricktest OldWorld memory utilization')

        ax.xaxis.set_major_locator(plt.MaxNLocator(20))  # Display a max of 20 x-axis time ticks

        # Plot the data
        plt.plot(time_track, bgexaminer_private_bytes / 1000000, time_track, bgexaminer_virtual_bytes / 10000000,
                 time_track, bgserver_private_bytes / 1000000, time_track, bgserver_virtual_bytes / 1000000,
                 time_track, docauthapp_private_bytes / 1000000, time_track, docauthapp_virtual_bytes / 1000000,
                 time_track, dataanalysisapihost_private_bytes / 1000000, time_track, dataanalysisapihost_virtual_bytes / 1000000)

        plt.grid(True)
        plt.gcf().autofmt_xdate()
        plt.legend(['bgexaminer private', 'bgexaminer virtual', 'bgserver private', 'bgserver virtual', 'docauth private',
                    'docauth virtual', 'dataanalapi private', 'dataanalyapi virtual'])
        plt.show()

        return

    def data_plotter(self):
        """Plot performance data from csv file using winstats library"""
        a = numpy.array(PerfMonitor.data)
        time_track = a[:, 0]  # Extract Timestamps (as string)

        # Extract data from columns 2 to 8 and (convert to floats).
        idemia_app_private_bytes = a[:, 1]
        idemia_app_private_bytes = numpy.asfarray(idemia_app_private_bytes, float)
        idemia_app_virtual_bytes = a[:, 2]
        idemia_app_virtual_bytes = numpy.asfarray(idemia_app_virtual_bytes, float)
        idemia_regula_private_bytes = a[:, 3]
        idemia_regula_private_bytes = numpy.asfarray(idemia_regula_private_bytes, float)
        idemia_regula_virtual_bytes = a[:, 4]
        idemia_regula_virtual_bytes = numpy.asfarray(idemia_regula_virtual_bytes, float)
        idemia_esf_private_bytes = a[:, 5]
        idemia_esf_private_bytes = numpy.asfarray(idemia_esf_private_bytes, float)
        idemia_esf_virtual_bytes = a[:, 6]
        idemia_esf_virtual_bytes = numpy.asfarray(idemia_esf_virtual_bytes, float)
        idemia_linecode_private_bytes = a[:, 7]
        idemia_linecode_private_bytes = numpy.asfarray(idemia_linecode_private_bytes, float)
        idemia_linecode_virtual_bytes = a[:, 8]
        idemia_linecode_virtual_bytes = numpy.asfarray(idemia_linecode_virtual_bytes, float)

        # Create cartesian plane, draw labels and title
        fig, ax = plt.subplots()  # Returns a figure container and a single xy axis chart

        ax.set_title('Bricktest memory utilization')
        ax.set_xlabel('Date/Time')
        ax.set_ylabel('Memory in Gigabytes')
        ax.xaxis.set_major_locator(plt.MaxNLocator(20))  # Display a max of 20 x-axis time ticks

        # Plot the data
        ax.plot(time_track, idemia_app_private_bytes / 1000000000, time_track, idemia_app_virtual_bytes / 1000000000,
            time_track, idemia_regula_private_bytes / 1000000000, time_track, idemia_regula_virtual_bytes / 1000000000,
            time_track, idemia_esf_private_bytes / 1000000000, time_track, idemia_esf_virtual_bytes / 1000000000,
            time_track, idemia_linecode_private_bytes / 1000000000, time_track, idemia_linecode_virtual_bytes / 1000000000)

        ax.grid(True)
        ax.figure.autofmt_xdate()
        ax.legend(['DocAuth private', 'DocAuth virtual', 'Regula private', 'Regula virtual',
                   'ESF private', 'ESF virtual', 'Linecode private', 'Linecode virtual'])

        # Output the chart.  Really only needed if NOT in "interactive mode".
        # If in non-interactive mode, may need to use "plt.show()" instead.
        fig.show()

        return

# Run this bitch

def main():
    pm = PerfMonitor()

    choice = pm.command_line_arguments()
    #print("Printing args from Main", choice)

    if choice.action == "record" and choice.world == "oldworld":
        pm.data_collector_oldworld()
    elif choice.action == "record" and choice.world == "newworld":
        pm.data_collector()
    elif choice.action == "report" and choice.world == "oldworld":
        pm.file_reader_oldworld()
        pm.data_plotter_oldworld()
    elif choice.action == "report" and choice.world == "newworld":
        pm.file_reader()
        pm.data_plotter()
    elif choice.action == "all" and choice.world == "oldworld":
        pm.data_collector_oldworld()
        pm.file_reader_oldworld()
        pm.data_plotter_oldworld()
    else:  # Assuming 'all' and 'newworld'
        pm.data_collector()
        pm.file_reader()
        pm.data_plotter()

if __name__ == "__main__":
    main()
