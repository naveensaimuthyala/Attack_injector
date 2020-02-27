import can_message
import subprocess
import can_message
import contextlib
import sys, os
import time
import random
import math

import helper_functions
import numpy as np
from can_message import *

# python3 attack_injector.py -i otids -o tes.log -a dos_vol -at 6.217975 -ad 0.5  ./short.txt 
ATTACK_NOT_STARTED = 0
ATTACK_START = 1
ATTACK_ONGOING = 2
ATTACK_COMPLETED = 3


def gen_rand_dlc():
    low = 1
    high = 8
    return random.randint(low, high)

def gen_rand_imt(minv=0.005, maxv=1.000):
    """
    For now we assume the random inter message time in
    the range minv to maxv.
    
    The power function is applied to skew the results
    slightly to lower numbers.
    """
    rng = maxv - minv
    fact = math.pow(np.random.random_sample(), 1.1)
    return minv + round(rng * fact, 3)

def gen_rand_auto_data():
    """
    Generate a random CAN data segment as a list 
    of eight integral values in the 0..255 range.
    """
    tdata = random.randint(0, np.iinfo(np.int32).max)
    thex_data = '{0:016x}'.format(tdata)
    shex_data = str(thex_data)
    shift = random.randint(0, 16)
    new_hex = shex_data[shift:] + shex_data[:shift]
            
    #I want my data as lists of integers.
    return [ int(new_hex[i:i+2],16) for i in range(0, len(new_hex), 2)]




class CanMessageFactory():
    def __init__(self):
        pass
    
   
    def create_DoS_messages(self, canids, src_imt,start_time,attack_length,busname,dos_speed=1.0):
        """
        These are just guesses for now.
        
        Low speed dos_speed = 0.5
        Med speed dos_speed = 1.0
        High speed dos_speed = 2.0
        """
        attack_msgs = []
        print(src_imt)
        for attack_msg_timestamp in np.arange(start_time, (start_time+attack_length), src_imt):
            dlc = gen_rand_dlc()
            data = gen_rand_auto_data()
            imt = gen_rand_imt(maxv=src_imt/dos_speed)
            cmsg = CanMessage(dlc=dlc, data=data, timestamp= attack_msg_timestamp ,arb_id=canids[0],\
                                dist='uniform', imt=imt)
            #print(can_message.to_canplayer(cmsg, busname), file=outstream)
            attack_msgs.append(cmsg)
            print(cmsg)
        return attack_msgs
    


class BaseAttackModel():
    ATTACK_ON = 1
    ATTACK_ALREADY_ON = 2
    ATTACK_OFF = 3
    
    def __init__(self, attack_type,attack_start_time, attack_duration,instances_dict):
        self.min_imt = 0
        self.min_canid = 0
        self.num_msgs = 0
        self.attack_interval = [4.0, 8.0]
        self.attack_state = BaseAttackModel.ATTACK_OFF
        self.attack_messages = None  # Attack messages (in a queue)
        self.preattack_canmsg_dict =instances_dict
        self.prev_imt = 0
        self.attack_start_time = attack_start_time
        self.attack_duration= attack_duration
        
    def get_attack_state(self, can_msgs):
        """
        Checks and return whether attack time is started or not 
        """
        
        
        if(can_msgs.timestamp < self.attack_start_time):
            
            return ATTACK_NOT_STARTED
        
        elif(can_msgs.timestamp == self.attack_start_time):
            
            self.attack_state = BaseAttackModel.ATTACK_ON
            return ATTACK_START
        
        elif(can_msgs.timestamp > self.attack_start_time) and( can_msgs.timestamp < (self.attack_start_time + self.attack_duration)):
            
            return ATTACK_ONGOING
            
        elif(can_msgs.timestamp > self.attack_start_time):
            
            return ATTACK_COMPLETED   
   
    
    
    
    def watch( self, can_msgs):
        """
        This stores the previous canids and its time stamps in a dictonary 
        """
        if not(can_msgs.arb_id in self.preattack_canmsg_dict):
            self.prev_imt = can_msgs.timestamp
            self.preattack_canmsg_dict[can_msgs.arb_id]=[]
            self.preattack_canmsg_dict[can_msgs.arb_id].append(can_msgs.timestamp)
        elif can_msgs.arb_id in self.preattack_canmsg_dict:
            self.preattack_canmsg_dict[can_msgs.arb_id].append(can_msgs.timestamp)

class DoSAttackModel(BaseAttackModel):
    
    """
    This class manages Injection of DOS attack on to datset 
    """
    
    def __init__(self, attack_type,attack_start_time, attack_duration,imt_ip,instances_dict,busname):
        super(DoSAttackModel, self).__init__(attack_type,attack_start_time, attack_duration,instances_dict)
        self.attack_type =attack_type
        self.attack_start_time=attack_start_time
        self.attack_duration=attack_duration
        self.imt_ip=imt_ip
        self.busname=busname
    def get_attack_msgs(self, instances_dict): 
        
        if( self.attack_state == BaseAttackModel.ATTACK_ON):
            """
            GET CAN ID IN TO ARRAY
            GET MIN IMT VALUE
            """
            min_num_canid = [] #used list for future use if attack has to be injected with more than one can id.
            self.canids = sorted(list(instances_dict.keys())) #Get the canid with lowest value from the dictionary 
            if self.attack_type == 'dos_prio':
                min_num_canid.append( random.randint(0, min(self.canids))) # selecting non existing minimum can id for dos prority attack
            elif self.attack_type == 'dos_vol':
                min_num_canid.append(min(self.canids)) # selecting existing minimum can id for dos volume attack

            if self.imt_ip is None:  # if imt is not specified we will calculate default imt based on min imt seen for canid
                
                for canid in self.canids:
                                
                    #print("{}:before:{}".format(canid,instances_dict[canid]))
                    instances_dict[canid]= list(np.diff(instances_dict[canid]))
                    #print("{}:after:{}".format(canid,instances_dict[canid]))
                    
                    if( not instances_dict[canid]):  # check if it is having only one message so far  we cannot get IMT so we need to 
                                                    # check next ids can messasge min IMT and apply that to min can id value 
                        pass
                    elif (instances_dict[canid]):
                        
                        self.min_imt = min(instances_dict[canid])

                        break
            elif self.imt_ip is not None:
                
                self.min_imt= float(self.imt_ip)

                
            
            cmf = CanMessageFactory()
            self.attack_messages = cmf.create_DoS_messages(canids=min_num_canid,\
                                                     src_imt=self.min_imt, start_time = self.attack_start_time,attack_length= self.attack_duration,\
                                                         busname= self.busname)
            
            instances_dict.clear()
            return self.attack_messages
        
        
        
        
        
def AttackFactory(busname, attack_type,attack_start_time,attack_duration,imt_ip,instances_dict):
    
    """
    Returns the appropriate attack model based on input attack type
    """
   
    
    if (attack_type in ['dos_vol', 'dos_prio']):
        
        return DoSAttackModel(attack_type = attack_type,attack_start_time = attack_start_time,\
                attack_duration =attack_duration,imt_ip= imt_ip,instances_dict= instances_dict, busname= busname)

    else:
        return None
    


def parse_infile(parser,file,outfile,busname, attack_name, attack_start_time, attack_duration, imt_ip):
    
    """
    This function is used to parse the infile line by line and print for now 
    """   
    start = time.time()
    
    instances_dict={}  # This is used to store statistics of previous canmsgs in watch function
    attack = AttackFactory(busname, attack_name,attack_start_time,attack_duration,imt_ip, instances_dict)
    
    with helper_functions.manage_output_stream(outfile) as outstream:

        with open(file, "r") as ifile:

            for line in ifile:
                cmsg = parser(line)
                
                
                if (attack.get_attack_state(cmsg)== ATTACK_NOT_STARTED):
                    print( " sending normal msg")
                    attack.watch(cmsg)
                    print(can_message.to_canplayer(cmsg, busname), file=outstream)
                
                elif (attack.get_attack_state(cmsg) == ATTACK_START):
                    amsg = attack.get_attack_msgs(instances_dict)
                    for message in amsg:
                        print(can_message.to_canplayer(message, busname), file=outstream)
                    
                elif ( attack.get_attack_state(cmsg) == ATTACK_ONGOING ):
                    print(can_message.to_canplayer(cmsg, busname), file=outstream)
                    
                elif(attack.get_attack_state(cmsg) == ATTACK_COMPLETED ):
                    print(can_message.to_canplayer(cmsg, busname), file=outstream)

    
    end = time.time()
    print( " The time took to inject attack and process file is {0:.4f} seconds".format(end-start))
