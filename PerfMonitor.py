import sys
import psutil
import csv
import winstats
import numpy
import matplotlib.pyplot as plt
import time
import datetime as dt


class PerfMonitor:
    """Performance Monitoring for Idemia DocAuth"""
    data = []

    def process_checker(self):
        """Verify that the IDEMIA... processes are running"""
        for process in psutil.process_iter():
            if 'IDEMIA' in process.name():
                print(process.name())
                return True
        return False

    def command_line_arguments(self):
        """Read and evaluate commandline arguments, returns the single commandline argument"""
        command = sys.argv[0]
        arguments = len(sys.argv) - 1

        if arguments == 1:
            # print("parameter %i: %s" % (position, sys.argv[position]))
            choice = sys.argv[1]  # Return the single commandline argument
            return choice
        else:
            print("Usage: " + command + " [record] | [report] | [all]")
            exit(2)

    def data_collector(self):
        """Collect performance data via winstats library. Then write each line of data to csv file"""

        # Verify that DocAuth IS running.
        if not self.process_checker():
            print("DocAuth is NOT running. Please startup DocAuth BEFORE running this PerformanceMonitor.")
            exit(2)
        print("Verified that DocAuth IS running.")

        output_filename = r'c:\Temp\DocAuthPerfData.csv'
        f = open(output_filename, 'wt')
        writer = csv.writer(f, delimiter=',', quotechar='"', lineterminator='\n')

        # Run through ticks (time) for x-axis. (Eventually, replace real time for "ticks" for future.)

        for ticks in range(1440):  # 1440 = 12 hours for 30 second tickssssss
            # New World processes
            time_track = dt.datetime.fromtimestamp(time.time())  # Get timestamp-style time
            time_track = time_track.strftime("%m/%d/%y %H:%M")  # Keep "m/d/y h/m" drop seconds.milliseconds
            print(time_track)

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

            print(ticks)
            time.sleep(30)

        f.close()
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

        plt.xlabel('Time for timer ')
        plt.ylabel('Memory in Kilobytes')
        plt.title('Bricktest memory utilization')

        ax.xaxis.set_major_locator(plt.MaxNLocator(20))  # Display a max of 20 x-axis time ticks

        # Plot the data
        plt.plot(time_track, idemia_app_private_bytes / 10000, time_track, idemia_app_virtual_bytes / 10000, time_track,
                 idemia_app_working_set / 10000,
                 time_track, idemia_regula_private_bytes / 10000, time_track, idemia_regula_virtual_bytes / 10000,
                 time_track, idemia_regula_working_set / 10000)
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
    print(choice)

    if choice == "record":
        # PHASE 1: Capture performance data to CSV file
        pm.data_collector()
    elif choice == "report":  # Tested and PASSED
        # PHASE 2: Plot performance data from CSV capture file
        pm.file_reader()
        pm.data_plotter()
    elif choice == "all":
        # PHASE 1: Capture performance data to CSV file
        pm.data_collector()
        # PHASE 2: Plot performance data from CSV capture file
        pm.file_reader()
        pm.data_plotter()


if __name__ == "__main__":
    main()
