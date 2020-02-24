import can_message
import subprocess
import can_message
import contextlib
import sys, os
import time
import helper_functions
import numpy as np



class CanMessageFactory():
    def __init__(self):
        pass
    
   
    def create_DoS_messages(self, canids, src_imt, dos_speed=1.0):
        """
        These are just guesses for now.
        
        Low speed dos_speed = 0.5
        Med speed dos_speed = 1.0
        High speed dos_speed = 2.0
        """
        attack_msgs = []
        for can_id in canids:
            dlc = gen_rand_dlc()
            data = gen_rand_auto_data()
            imt = gen_rand_imt(maxv=src_imt/dos_speed)
            cmsg = CanMessage(dlc=dlc, data=data, timestamp=0,arb_id=can_id,\
                                dist='uniform', imt=imt)
            attack_msgs.append(cmsg)
        
        return attack_msgs
    


class BaseAttackModel():
    ATTACK_ON = 1
    ATTACK_ALREADY_ON = 2
    ATTACK_OFF = 3
    
    def __init__(self, attack_type,attack_start_time, attack_duration, can_msgs,instances_dict):
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
        now_on = False
        # Eventually we will want to add more intricate attack patterns here.
        if (can_msgs.timestamp >= self.attack_start_time) and( can_msgs.timestamp < (self.attack_start_time + self.attack_duration)):
            now_on = True
            #print("self.attack_start_time :{} timestamp is :{}".format(self.attack_start_time,can_msgs.timestamp))
            return now_on
        else:
            return now_on   
   
    
    
    
    def watch( self, can_msgs):
        
        if not(can_msgs.arb_id in self.preattack_canmsg_dict):
            self.prev_imt = can_msgs.timestamp
            self.preattack_canmsg_dict[can_msgs.arb_id]=[]
            self.preattack_canmsg_dict[can_msgs.arb_id].append(can_msgs.timestamp)
        elif can_msgs.arb_id in self.preattack_canmsg_dict:
            #difference=  round(can_msgs.timestamp-self.preattack_canmsg_dict[can_msgs.arb_id][-1], 4)
            #self.preattack_canmsg_dict[can_msgs.arb_id].append(difference)
            #self.prev_imt= can_msgs.timestamp
            self.preattack_canmsg_dict[can_msgs.arb_id].append(can_msgs.timestamp)

class DoSAttackModel(BaseAttackModel):
    def __init__(self, attack_type,attack_start_time, attack_duration, can_msgs,instances_dict,busname, outstream):
        super(DoSAttackModel, self).__init__(attack_type,attack_start_time, attack_duration, can_msgs,instances_dict)
        
        
        
        if(self.get_attack_state(can_msgs) != True):
            
            self.watch(can_msgs)
            print( "sending normal traffic to outfile")
            print(can_message.to_canplayer(can_msgs, busname), file=outstream)
        
        if( self.get_attack_state(can_msgs) == True):
            #GET CAN ID IN TO ARRAY
            #GET MIN IMT VALUE
            self.canids = sorted(list(instances_dict.keys())) #Get the canid with lowest value from the dictionary 
            
            for canid in self.canids:
                               
                print("{}:before:{}".format(canid,instances_dict[canid]))
                instances_dict[canid]= list(np.diff(instances_dict[canid]))
                print("{}:after:{}".format(canid,instances_dict[canid]))
                
                if( not instances_dict[canid]):  # check if it is having only one message we cannot get IMT so we need to 
                                                # check next messasge min IMT and apply that to min can id value 
                    pass
                elif (instances_dict[canid]):
                    
                    self.min_imt = min(instances_dict[canid])
                    
                    break

            print(self.min_imt)
def AttackFactory(can_msg,busname, attack_type,attack_start_time,attack_duration,instances_dict,outstream):
    
    """
    Returns the appropriate attack model based on model
    parameters.
    """
    
    if (float(attack_start_time)== can_msg.timestamp):
    
        print("start-attack")
    
    if (attack_type in ['dos_vol', 'dos_prio']):
        
        if (can_msg.timestamp <= attack_start_time) or ( can_msg.timestamp > attack_start_time+attack_duration):
           
            return DoSAttackModel(attack_type,attack_start_time, attack_duration, can_msg,instances_dict, busname, outstream)

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
    
    print( " instances dict ", instances_dict)
    
    end = time.time()
