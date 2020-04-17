import copy
import datetime
import os
import textwrap
import time

import argparse

class CanMessage():
    """
    This class stores basic information about a CAN bus message.
    """
    def __init__(self, dlc=0, data=[], timestamp=0., arb_id=0, typ= 'R', dist='uniform', imt=0.05):
        self.dlc = dlc
        self.data = data
        self.timestamp = timestamp
        self.arb_id = arb_id
        self.dist = dist
        self.ttype = typ
        self.imt = imt  #Standard IMT dist.
        
    def __lt__(self, other):
        """
        Less than operator, allows us to easily sort a list of
        can messages based on timestamp.
        """
        return self.timestamp < other.timestamp
    
    def hex_data(self):
        hexstr = ""
        for byte in self.data:
            hexstr = hexstr + hex(byte) + " "
        hexstr = hexstr + "(" + str(len(self.data)) + ")"
        return hexstr
    
    def __str__(self):
        return "ID: {0:d} DLC: {1:d} DATA: {2} TS: {3:f} IMT: {4:f} ({5}) {6}".format(
                self.arb_id, self.dlc, str(self.data), self.timestamp, self.imt, self.dist, self.ttype)

    def bit_string(self):
        """
        Returns message payload as an array of bit values [0, 1, 0, 1, ....] 
        """
        bit_str = []
        for byte in self.data:
            bits = [int(x) for x in '{:08b}'.format(byte)]
            bit_str.extend(bits)
        return bit_str
                            
def parse_canlong_line(line):
    """
    Reads a can message LOG file generated in default candump format,
    which is more human readable.
    
    (1575929897.132300)  vcan1  0000017A   [5]  11 A3 33 13 17
    """
    parts = line.split()
    timestamp = float(parts[0].strip('()'))
    canid = int(parts[2], 16)
    dlc = int(parts[3].strip('[]'))
    data = [int(x, 16) for x in parts[4:]]
    
    return CanMessage(dlc=dlc, data=data, timestamp=timestamp, arb_id=canid)

def parse_canshort_line(line):
    """
    Reads a CAN message LOG file generated in canplayer format, which
    is somewhat less human readable:
    
            (2.135407) can4 00000690#0000000000000000
    """
    parts = line.split()
    timestamp = float(parts[0].strip('()'))
    partsmsg = parts[2].split('#')
    canid = int(partsmsg[0], 16)
    data = [ int(x, 16) for x in textwrap.wrap(partsmsg[1], 2) ]
    
    return CanMessage(dlc=len(data), data=data, timestamp=timestamp, arb_id=canid) 

#def __init__(self, dlc=0, data=[], timestamp=0., arb_id=0, typ= 'R', dist='uniform', imt=0.05):
    
def parse_otids_line(line):
    """
    Reads lines from OTIDS file of format:
    
    05f0    2       00      00      0e      00      00      00      00      00      2.084334
    """
    parts = line.split()
    timestamp = float(parts[-1])
    canid = int(parts[0], 16)
    dlc = int(parts[1])
    data = [ int(x, 16) for x in parts[2:-1] ]
    
    return CanMessage(dlc=dlc, data=data, timestamp=timestamp, arb_id=canid)

def parse_drdc_line(line):
    """
    Reads CAN message from dataset provided by DRDC.  Messages are of the form.
    
    <TS>,<Payload>
    1454074823.645977,t1408000F524600000F210000
    
    Where payload can be sudivided as follows:
    1222344444444444444445555
    t1408000F524600000F210000
    
    Where
    1. is the letter 't'
    2. is the CAN id (in hex)
    3. is the DLC
    4. is the (variable length) payload
    5. is the time stamp (we don't use this).
    """
    parts = line.split(',')
    timestamp = float(parts[0])
    canid = int(parts[1][1:4], 16)
    dlc = int(parts[1][4])
    data = [int(x, 16) for x in textwrap.wrap(parts[1][5:-5], 2) ]
    
    return CanMessage(dlc=dlc, data=data, timestamp=timestamp,arb_id=canid)

def parse_csv_line(line):
    """
    Reads lines from CSV (attack) file of the format:
    
    1478198376.390333,0329,8,40,bb,7f,14,11,20,00,14,R
    , 
    Fields are
    
    Timestamp, CANID, dlc, D[0],D[1],D[2],D[3],D[4],D[5],D[6],D[7], {R}egular|{T}attack
    """
    parts = line.split(',')
    timestamp = float(parts[0])
    canid = int(parts[1], 16)
    dlc = int(parts[2], 16)
    data = [ int(x, 16) for x in parts[3:-1] ]
    typ = parts[-1]
    
    return CanMessage(dlc=dlc, data=data, timestamp=timestamp, arb_id=canid, typ=typ)

def parse_pcaptxt_line(line):
    """
    Reads line from PCAP .txt file generated from Wireshark pcap CAN capture. In Wireshark
    the text file should be generated with the command:
    
    File -> Export Packet Dissections -> As Plain Text
    
    In the Packet Format options group box only the 'Packet Summary Line' option
    should be selected, all others, including the 'Include Column Headings' which is
    a sub-option of Packet Summary Line should NOT be selected.  The output lines will
    look like (some spaces have been dropped for brevity).
    
          1 0.000000       CAN      32     STD: 0x000000d0   7e 00 00 00 ef 07 00 ff
    
    """
    parts = line.split()
    timestamp = float(parts[1])
    canid = int(parts[5], 16)
    data = [ int(x,16) for x in parts[6:] ]
    dlc = len(data)
    
    return CanMessage(dlc=dlc, data=data, timestamp=timestamp, arb_id=canid)
    
    

def to_canplayer2(canmsg, busname):
    """
    Output a CAN message as a string readable by canplayer.
    """
    hex_data = ''.join(["{:02x}".format(x).upper() for x in canmsg.data ])
    hex_data = hex_data[0:canmsg.dlc * 2]
    return "({0:.6f}) {1} {2:0{3}X}#{4}".format(canmsg.timestamp, \
        busname, canmsg.arb_id, 8, hex_data)

def to_canplayer(canmsg, busname):
    """
    Output a CAN message to string with non-extended CAN messages.
    """
    hex_data = ''.join(["{:02x}".format(x).upper() for x in canmsg.data ])
    hex_data = hex_data[0:canmsg.dlc * 2]
    return "({0:.6f}) {1} {2:0{3}X}#{4}".format(canmsg.timestamp, \
        busname, canmsg.arb_id, 3, hex_data)    
        




    
