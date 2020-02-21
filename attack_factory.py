import can_message
import subprocess
import can_message
import contextlib
import sys, os
import time
import helper_functions




class BaseAttackModel():
    ATTACK_ON = 1
    ATTACK_ALREADY_ON = 2
    ATTACK_OFF = 3
    
    def __init__(self, attack_type, can_msgs,instances_dict):
        self.min_imt = 0
        self.min_canid = 0
        self.num_msgs = 0
        self.attack_interval = [4.0, 8.0]
        self.attack_state = BaseAttackModel.ATTACK_OFF
        self.attack_messages = None  # Attack messages (in a queue)
        self.preattack_canmsg_dict =instances_dict
        self.prev_imt = 0
        
    def watch( self, can_msgs):
        
        if not(can_msgs.arb_id in self.preattack_canmsg_dict):
            self.prev_imt = can_msgs.timestamp
            self.preattack_canmsg_dict[can_msgs.arb_id]=[]
            self.preattack_canmsg_dict[can_msgs.arb_id][can_msgs.timestamp]= 0
        elif can_msgs.arb_id in self.preattack_canmsg_dict:
            difference=  round(can_msgs.timestamp-self.prev_imt, 4)
            self.preattack_canmsg_dict[can_msgs.arb_id][can_msgs.timestamp]= difference
            self.prev_imt= can_msgs.timestamp

class DoSAttackModel(BaseAttackModel):
    def __init__(self, attack_type, can_msgs,instances_dict):
        super(DoSAttackModel, self).__init__(attack_type, can_msgs,instances_dict)
        
        
        self.watch(can_msgs)



def AttackFactory(can_msg,busname, attack_type,attack_start_time,attack_duration,instances_dict,outstream):
    
    """
    Returns the appropriate attack model based on model
    parameters.
    """
    
    if (float(attack_start_time)== can_msg.timestamp):
    
        print("start-attack")
   
    if attack_type in ['dos_vol', 'dos_prio']:
        
        print(can_message.to_canplayer(can_msg, busname), file=outstream)

        return DoSAttackModel(attack_type, can_msg,instances_dict)

    else:
        return None
        


def parse_infile(parser,file,outfile,busname, attack_name, attack_start_time, attack_duration):
    
    """
    This function is used to parse the infile line by line and print for now 
    """   
    start = time.time()
    instances_dict={}
    with helper_functions.manage_output_stream(outfile) as outstream:

        with open(file, "r") as ifile:
            #lines = [line.rstrip() for line in ifile]
            #print(lines[10])
            for line in ifile:
                cmsg = parser(line)
                AttackFactory(cmsg,busname, attack_name,attack_start_time,attack_duration, instances_dict,outstream)
    
    outstream.close()
    print( " instances dict ", instances_dict)
    
    end = time.time()
