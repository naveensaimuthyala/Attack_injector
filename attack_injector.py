import contextlib
import sys, os
import time
import can_report_helper
import argparse
import can_message
import pandas as pd
import attack_factory



@contextlib.contextmanager
def open_output_stream(filename=None):
    """
    Borrowed from:
    
    https://stackoverflow.com/questions/17602878/how-to-handle-both-with-open-and-sys-stdout-nicely
    """
    if filename and filename != '-':
        fh = open(filename, 'w')
        if fh is not sys.stdout:
            fh.close()

parsers = {
        'otids' : can_message.parse_otids_line,
        'csv' : can_message.parse_csv_line,
        'canshort' : can_message.parse_canshort_line,
        'canlong' : can_message.parse_canlong_line
}


argp = argparse.ArgumentParser(description='This project injects different types of attacks in to log file')
argp.add_argument('-b', '--bus', type=str, default='vcan1', help='CAN bus interface.')
argp.add_argument('-i', '--informat', type=str, default='otids', help='otids|csv|canshort|canlong')
argp.add_argument('-o', '--outfile', type=str, default=None, help='Optional output file')
argp.add_argument('infile', type=str, help='Trace/Template file.')
argp.add_argument('-a', '--attacktype', type=str, default = None, help = 'dos|replay|fuzzy|impersonation')
argp.add_argument('-at', '--attackstarttime', type=str, default= None, help = 'Attack Start Time')
argp.add_argument('-ad', '--attackduration', type=str,default= None , help= 'Attack Duration')
argp.add_argument('-id', '--canid', type=str,default=0, help= 'optional input can-id if required to inject \
                                                                        attack with particular can-id')

args = argp.parse_args()

infile = args.infile
outfile = args.outfile
busname = args.bus
infrmt = args.informat
attacktype= args.attacktype
canid= int(args.canid)
attk_start_time= float(args.attackstarttime)
attk_duration = float(args.attackduration)

if infrmt not in parsers:
    print('Input format: {} is not a valid format.'.format(infrmt))
    sys.exit(1)
parser = parsers[infrmt]

# in attack factory file we wrote a fucntion to parse input file and convert it to related parameters like corresponding timestamps , payload etc..
attack_factory.parse_infile(parser,infile,outfile, busname, attacktype, attk_start_time,attk_duration)

# can_report_helper.report_error_handler(repotype)
# reporter = report_types[repotype]

# start = time.time()

