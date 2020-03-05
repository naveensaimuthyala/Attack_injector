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
    
   
    def create_DoS_messages(self, canids,payload, src_imt,start_time,attack_length,busname,dos_speed=1.0):
        """
        These are just guesses for now.
        
        Low speed dos_speed = 0.5
        Med speed dos_speed = 1.0
        High speed dos_speed = 2.0
        """
        attack_msgs = []
        print("The imt value being introduced in attack is: {}".format(src_imt))
        for attack_msg_timestamp in np.arange(start_time, (start_time+attack_length), src_imt):
            dlc = gen_rand_dlc()
            data = payload  #sending minimum ids payload to every attack message
            imt = gen_rand_imt(maxv=src_imt/dos_speed)
            cmsg = CanMessage(dlc=dlc, data=data, timestamp= attack_msg_timestamp ,arb_id=canids[0],\
                                dist='uniform', imt=imt)
            attack_msgs.append(cmsg)
        return attack_msgs
    
    def create_Fuzzy_messages(self, canids, src_imt,start_time,attack_length,busname):
    
        """
        This method creates Fuzzy attack messages 
        and return list of all Fuzzy attack messages

        """
        attack_msgs = []
        print("The imt value being introduced in attack is: {}".format(src_imt))
        for attack_msg_timestamp in np.arange(start_time, (start_time+attack_length), src_imt):
            dlc = gen_rand_dlc()
            data = gen_rand_auto_data()  #sending Random payload for every message 
            imt = gen_rand_imt(maxv=src_imt)
            cmsg = CanMessage(dlc=dlc, data=data, timestamp= attack_msg_timestamp ,arb_id=canids[0],\
                                dist='uniform', imt=imt)
            attack_msgs.append(cmsg)
        return attack_msgs

    def create_Replay_messages(self, cmsgs, start_time,attack_duration):
    
        """
        This method creates Replay attack messages 
        and return list of all replay attack messages

        """
        x= np.random.uniform(low=start_time, high = (start_time+attack_duration), size= len(cmsgs) )
        x.sort()  # since random function returns randomly with in range we are sorting the list
        for i,message in  enumerate(cmsgs):
               message.timestamp = x[i]    
        attack_msgs = cmsgs
        return attack_msgs
    


class BaseAttackModel():
    ATTACK_ON = 1
    ATTACK_ALREADY_ON = 2
    ATTACK_OFF = 3
    
    def __init__(self, attack_type,attack_start_time, attack_duration,replay_seq_window):
        self.min_imt = 0
        self.min_canid = 0
        self.num_msgs = 0
        self.attack_interval = [4.0, 8.0]
        self.attack_type = attack_type
        self.attack_state = BaseAttackModel.ATTACK_OFF
        self.attack_messages = None  # Attack messages (in a queue)
        self.preattack_canmsg_dict ={}
        self.prev_imt = 0
        self.attack_start_time = attack_start_time
        self.attack_duration= attack_duration
        self.minid_payload =[] 
        self.minid_dos =-1
        
        self.replay_stream=[]
        self.replay_N = 0
        self.replay_stream_length = replay_seq_window #replay_stream_length
        
    def get_attack_state(self, can_msgs):
        """
        Checks and return whether attack time is started or not 
        """
        
        
        if(can_msgs.timestamp < self.attack_start_time):
            
            return ATTACK_NOT_STARTED
        
        elif (can_msgs.timestamp >= self.attack_start_time)  and ( can_msgs.timestamp <= (self.attack_start_time + self.attack_duration)):
           
            self.attack_state = BaseAttackModel.ATTACK_ON
                       
            if(can_msgs.timestamp > self.attack_start_time):
               
               self.attack_state = BaseAttackModel.ATTACK_ALREADY_ON              
            
            return ATTACK_START
            
        elif(can_msgs.timestamp > self.attack_start_time):
            
            return ATTACK_COMPLETED   
   
    
    
    
    def watch( self, can_msgs):
        """
        This stores the previous canids and its time stamps in a dictonary 
        """
        self.random_subset_msgs_from_stream(can_msgs)
        
        #store min can id and its payload alone
        if (self.minid_dos != -1 and can_msgs.arb_id < self.minid_dos):
        
            self.minid_dos = can_msgs.arb_id
            self.minid_payload = can_msgs.data
        
            
        elif( self.minid_dos == -1):
            self.minid_dos = can_msgs.arb_id
            self.minid_payload=can_msgs.data
        
        print( "min can id is :",self.minid_dos)
        
        #store can ids and its time stamps in dictionary
        if not(can_msgs.arb_id in self.preattack_canmsg_dict):
            self.prev_imt = can_msgs.timestamp
            self.preattack_canmsg_dict[can_msgs.arb_id]=[]
            self.preattack_canmsg_dict[can_msgs.arb_id].append(can_msgs.timestamp)
        elif can_msgs.arb_id in self.preattack_canmsg_dict:
            self.preattack_canmsg_dict[can_msgs.arb_id].append(can_msgs.timestamp)
            
        ## For replay msgs 
        # if( self.attack_type == "replay"):
        #     pass
    
    
    def random_subset_msgs_from_stream( self, cmsg ):
        
        self.replay_N += 1
        if len( self.replay_stream ) < self.replay_stream_length:
            self.replay_stream.append( cmsg )
        else:
            s = int(random.random() * self.replay_N)
            if s < self.replay_stream_length:
                self.replay_stream[ s ] = cmsg
        
        

class DoSAttackModel(BaseAttackModel):
    
    """
    This class manages Injection of DOS attack on to datset 
    """
    
    def __init__(self, attack_type,attack_start_time, attack_duration,imt_ip,busname):
        super(DoSAttackModel, self).__init__(attack_type,attack_start_time, attack_duration)
        self.attack_type =attack_type
        # self.attack_start_time=attack_start_time
        # self.attack_duration=attack_duration
        self.imt_ip=imt_ip
        self.busname=busname
    def get_attack_msgs(self): 
        
        #print( "attack state is ", self.attack_state)
        if( self.attack_state == BaseAttackModel.ATTACK_ON):
            """
            GET CAN ID IN TO ARRAY
            GET MIN IMT VALUE
            """

            min_num_canid = [] #used list for future use if attack has to be injected with more than one can id.
            self.canids = sorted(list(self.preattack_canmsg_dict.keys())) #Get the canid with lowest value from the dictionary 
            if self.attack_type == 'dos_prio':
                min_num_canid.append( random.randint(0, min(self.canids))) # selecting non existing minimum can id for dos prority attack
            elif self.attack_type == 'dos_vol':
                min_num_canid.append(min(self.canids)) # selecting existing minimum can id for dos volume attack

            if self.imt_ip is None:  # if imt is not specified we will calculate default imt based on min imt seen for canid
                
                for canid in self.canids:
                                
                    #print("{}:before:{}".format(canid,instances_dict[canid]))
                    self.preattack_canmsg_dict[canid]= list(np.diff(self.preattack_canmsg_dict[canid]))
                    #print("{}:after:{}".format(canid,instances_dict[canid]))
                    
                    if( not self.preattack_canmsg_dict[canid]):  # check if it is having only one message so far  we cannot get IMT so we need to 
                                                    # check next ids can messasge min IMT and apply that to min can id value 
                        pass
                    elif (self.preattack_canmsg_dict[canid]):
                        
                        self.min_imt = min(self.preattack_canmsg_dict[canid])

                        break
            elif self.imt_ip is not None:
                
                self.min_imt= float(self.imt_ip)

                
            
            cmf = CanMessageFactory()
            self.attack_messages = cmf.create_DoS_messages(canids=min_num_canid, payload= self.minid_payload , \
                                                     src_imt=self.min_imt, start_time = self.attack_start_time,attack_length= self.attack_duration,\
                                                         busname= self.busname)
            
            self.preattack_canmsg_dict.clear()
            return self.attack_messages
        
        
        else: 
            return self.attack_messages
        
 
 
 
        
class FuzzyAttackModel(BaseAttackModel):
    
    """
    This class manages Injection of Fuzzy attack on to datset 
    """
    
    def __init__(self, attack_type,attack_start_time, attack_duration,imt_ip,busname):
        super(FuzzyAttackModel, self).__init__(attack_type,attack_start_time, attack_duration)
 
        self.imt_ip=imt_ip
        self.busname=busname
        
    def get_attack_msgs(self): 
        
        #print( "attack state is ", self.attack_state)
        if( self.attack_state == BaseAttackModel.ATTACK_ON):
            """
            GET CAN ID IN TO ARRAY
            GET MIN IMT VALUE
            """
            min_num_canid = [] #used list for future use if attack has to be injected with more than one can id.
            self.canids = sorted(list(self.preattack_canmsg_dict.keys())) #Get the canid with lowest value from the dictionary 
            # if self.attack_type == 'dos_prio':
            #     min_num_canid.append( random.randint(0, min(self.canids))) # selecting non existing minimum can id for dos prority attack
            # elif self.attack_type == 'dos_vol':
            
            min_num_canid.append(min(self.canids)) # selecting existing minimum can id for dos volume attack

            if self.imt_ip is None:  # if imt is not specified we will calculate default imt based on min imt seen for canid
                
                for canid in self.canids:
                                
                    #print("{}:before:{}".format(canid,instances_dict[canid]))
                    self.preattack_canmsg_dict[canid]= list(np.diff(self.preattack_canmsg_dict[canid]))
                    #print("{}:after:{}".format(canid,instances_dict[canid]))
                    
                    if( not self.preattack_canmsg_dict[canid]):  # check if it is having only one message so far  we cannot get IMT so we need to 
                                                    # check next ids can messasge min IMT and apply that to min can id value 
                        pass
                    elif (self.preattack_canmsg_dict[canid]):
                        
                        self.min_imt = min(self.preattack_canmsg_dict[canid])

                        break
            elif self.imt_ip is not None:
                
                self.min_imt= float(self.imt_ip)

                
            
            cmf = CanMessageFactory()
            self.attack_messages = cmf.create_Fuzzy_messages(canids=min_num_canid,src_imt=self.min_imt, start_time = self.attack_start_time, \
                                                            attack_length= self.attack_duration,busname= self.busname)
            
            self.preattack_canmsg_dict.clear()
            return self.attack_messages
        
        
        else: 
            return self.attack_messages
    
    
    def get_owrite_attack_msgs(self, cmsg):
        
        cmsg.data = gen_rand_auto_data() # just replace real can message data payload with random payload and return back
        return cmsg
        


       
class ReplayAttackModel(BaseAttackModel):
    
    """
    This class manages Injection of Replay single and sequence  attack  messages on to datset 
    """
    
    def __init__(self, attack_type,attack_start_time, attack_duration,imt_ip,busname,replay_seq_window):
        super(ReplayAttackModel, self).__init__(attack_type,attack_start_time, attack_duration,replay_seq_window)
        self.attack_type =attack_type
        self.attack_start_time=attack_start_time
        self.attack_duration=attack_duration
        self.imt_ip=imt_ip
        self.busname=busname
        
    def get_attack_msgs(self): 
        
        #print( "attack state is ", self.attack_state)
        if( self.attack_state == BaseAttackModel.ATTACK_ON):
            
            self.replay_stream
            
            cmf = CanMessageFactory()
            self.attack_messages=cmf.create_Replay_messages(cmsgs=self.replay_stream, start_time= self.attack_start_time,\
                                                                attack_duration= self.attack_duration )
 
        return self.attack_messages
        






def AttackFactory(busname, attack_type,attack_start_time,attack_duration,imt_ip,replay_seq_window):
    
    """
    Returns the appropriate attack model based on input attack type
    """
   
    
    if (attack_type in ['dos_vol', 'dos_prio']):
        
        return DoSAttackModel(attack_type = attack_type,attack_start_time = attack_start_time,\
                attack_duration =attack_duration,imt_ip= imt_ip, busname= busname)
    elif ( attack_type in  ['fuzzy_ins', 'fuzzy_owrite']):
        
        return FuzzyAttackModel( attack_type =attack_type, attack_start_time = attack_start_time , \
                                attack_duration =attack_duration,imt_ip= imt_ip, busname= busname)
    elif ( attack_type == 'replay'):
        return ReplayAttackModel( attack_type =attack_type, attack_start_time = attack_start_time , \
                                attack_duration =attack_duration,imt_ip= imt_ip, busname= busname, replay_seq_window=replay_seq_window)    
    else:
        
        return None
    



def write_attackmsgs_to_outfile( amsg, cmsg , current_index ,busname, outstream):
      
    
    while((current_index< len(amsg) )and (amsg[current_index].timestamp <= cmsg.timestamp)):
        print("here",amsg[current_index] , current_index)
        print(can_message.to_canplayer(amsg[current_index], busname), file=outstream)
        current_index+= 1
    return

    

def inject_attack(parser,file,outfile,busname, attack_name, attack_start_time, attack_duration, imt_ip,replay_seq_window):
    
    """
    This function is used to parse the infile line by line and print for now 
    """   
    start = time.time()
    current_index=0
    attack = AttackFactory(busname, attack_name,attack_start_time,attack_duration,imt_ip,replay_seq_window)
    
    with helper_functions.manage_output_stream(outfile) as outstream:

        with open(file, "r") as ifile:
            
   
            for line in ifile:
                cmsg = parser(line)
                
                
                if (attack.get_attack_state(cmsg)== ATTACK_NOT_STARTED):
                    print( " sending normal msg")
                    attack.watch(cmsg)
                    print(can_message.to_canplayer(cmsg, busname), file=outstream)
                    
                
                elif (attack.get_attack_state(cmsg) == ATTACK_START): ## Change the ATTACK_START macro to ATTACK_PHASE
                    
                    
                    
                    if (attack_name  in ['fuzzy_owrite', 'impersonation_owrite']):
                        
                        
                        cmsg = attack.get_owrite_attack_msgs(cmsg)
                        print(can_message.to_canplayer(cmsg, busname), file=outstream)
                   
                    else:
                        
                        amsg = attack.get_attack_msgs()
                        #write_attackmsgs_to_outfile(amsg=amsg, cmsg=cmsg, current_index= current_index, busname= busname,outstream = outstream)
                        while((current_index< len(amsg) )and (amsg[current_index].timestamp <= cmsg.timestamp)):
                            print("here",amsg[current_index] , current_index)
                            print(can_message.to_canplayer(amsg[current_index], busname), file=outstream)
                            current_index+= 1
                        print(can_message.to_canplayer(cmsg, busname), file=outstream)

                elif(attack.get_attack_state(cmsg) == ATTACK_COMPLETED ):
                    print(can_message.to_canplayer(cmsg, busname), file=outstream) # combine this and first condition at end of this version  release 

    
    end = time.time()
    print( " The time took to inject {0} attack messages and process file is {1:.4f} seconds".format(current_index,end-start))
