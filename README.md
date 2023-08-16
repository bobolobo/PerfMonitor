# PerfMonitor

This Python code is a performance monitoring tool that collects performance data from various processes and processes it. It leverages the winstats library for obtaining performance statistics. The script accepts command-line arguments to specify whether to record or report data, and which "world" to monitor or report on. It can capture data over time intervals and store it in CSV files. Additionally, it can read and plot data from these CSV files using the matplotlib library.

The PerfMonitor class contains methods for different stages of the monitoring process, including command-line argument parsing, process monitoring, data collection, file reading, and data plotting. The main method serves as the entry point for running the script

It also monitors certain processes to watch how many times (hopefully none) they restart, and also includes a simple single-pane user interface to present the user with the collected data and allows the user to select which of this data to graph.

To run need to install psutil, numpy, mathplotlib, and winstats python libraries.
                           --Regards, BoboLobo
