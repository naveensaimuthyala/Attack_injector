import contextlib
import sys, os
import time
import argparse
import can_message
import attack_factory
import json


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
argp.add_argument('-a', '--attacktype', type=str, default = None, help = 'dos[dos_vol, dos_prio]|replay|fuzzy[fuzzy_ins, fuzzy_owrite]|impersonation')
argp.add_argument('-at', '--attackstarttime', type=str, default= None, help = 'Attack Start Time')

argp.add_argument('-ad', '--attackduration', type=str,default= 1 , help= 'Attack Duration')
argp.add_argument('-imt','--imt', type=str, default= None, help='IMT for attack messages')
argp.add_argument('-id', '--canid', type=str,default= -1, help= ' input can-id if required to inject \
                                                                        replay attack with particular can-id')
argp.add_argument('-w', '--replay_seq_length', type=str, default = 1, help= " replay sequence window size" )
argp.add_argument('-rn', '--number_of_times_to_replay', type=str, default = 1, help= " replay sequence window size" )
argp.add_argument('-t', '--test_name', type=str, default= None, help=" testname" )




args = argp.parse_args()

test_name = args.test_name

print( "ou in attackinj",  args.attacktype)

if not os.path.exists(test_name):
    os.makedirs(test_name)
    
infile = args.infile
inp_head, inp_tail = os.path.split(infile)

#test_head , test_tail = os.path.split(test_name)

outfile = test_name+"/"+inp_tail.replace(".log",".").replace(".txt",".")+str(args.attacktype)+".log"

#outfile = test_name+"/"+inp_tail.replace(".log",".").replace(".txt",".")+str(args.attacktype)+"_"+test_tail+".log"


busname = args.bus
infrmt = args.informat
attacktype= args.attacktype
rcanid= int(args.canid)
attk_start_time= float(args.attackstarttime)
attk_duration = float(args.attackduration)
imt_ip=args.imt
replay_seq_window = float(args.replay_seq_length)
no_of_times_times_to_replay = int( args.number_of_times_to_replay)

if infrmt not in parsers:
    print('Input format: {} is not a valid format.'.format(infrmt))
    sys.exit(1)
parser = parsers[infrmt]

inp_args_data= vars(args)
## save the command line arguments given to json file
with open(outfile.replace(".log","")+'_params.json', 'w') as fp:
    json.dump(inp_args_data, fp, sort_keys=True, indent=4)

# in attack factory file we wrote a fucntion to parse input file and convert it to related parameters like corresponding timestamps , payload etc..

attack_factory.inject_attack(parser,infile,outfile, busname, attacktype, attk_start_time,attk_duration, imt_ip, replay_seq_window,rcanid \
                            , no_of_times_times_to_replay)



