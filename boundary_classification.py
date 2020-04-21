import contextlib
import sys, os
import time
import argparse
import can_message
import numpy as np
np.set_printoptions(threshold=sys.maxsize)
np.set_printoptions(formatter={'float': '{: 0.3f}'.format})
import json
from collections import OrderedDict
import ast

def get_sliced_matrix(binary_canmsgwindow_array, left_bit, field_length):
    """
    get_unique_count_matrix defined by a starting bit 'left_bit' and length
    'field_length'. Return a column of integers containing that
    field's values from the given 64-bit 'bit_array'.
    """
    assert field_length > 0, "Field length must be positive"

    

    sub_matrix = binary_canmsgwindow_array[:, left_bit:left_bit + field_length] #slicing all rows with columns leftbit to left_bit+field_length
    
    #print("len", len(sub_matrix))
    int_arr = np.packbits(sub_matrix, axis=1) #convert each message to integer array
    
    
    num_of_messages = len(int_arr)
    
   
    
    a_pad = np.hstack((np.zeros((num_of_messages, (64 - field_length) // 8), #converting all messages int values to single column
                                dtype='u1'), int_arr)).view(np.uint64)
    return a_pad

        

def extract_unique_valcount_from_matrix(data_matrix, fileds_to_skip):
    """
    Count how many unique values are in each possible field defined by a
    'left_bit' and 'field_length'. Put these counts in uniquecnt_matrix which
    at location [left_bit, field_length-1] contains the number of unique
    values seen in data_matrix at that location. The matrix is all-zero on the
    lower right triangle.
    """

    print("Fields to skip are ", fileds_to_skip)
    canmsgs_window_arr = data_matrix.astype('u1')
    print("window arr", len(canmsgs_window_arr))
    time_start = time.time()
    
    uniquecnt_matrix = np.zeros((64, 64))
    
    matrix_size =64
    skipindex_matrix = np.rot90(np.triu(np.ones((matrix_size, matrix_size), dtype=str)))
    skipindex_matrix[skipindex_matrix==''] = ' '
    finalskip_index=[]
    #print(skipindex_matrix)
    for user_classified_idx in fileds_to_skip:
       
        start_bit_index = user_classified_idx[0]+1  # determines zero based indexing or 1 based indexing for testing only
        end_bit_index = user_classified_idx[1]
        
        
        # #print(" Before \n", uniquecnt_matrix[:,start_bit_index:end_bit_index])

        # #print("change values from field {} to length {}".format(user_classified_idx[1], user_classified_idx[0]+1))
        # uniquecnt_matrix[:,start_bit_index:end_bit_index] = -5
        # #print(" After \n", uniquecnt_matrix[:,start_bit_index:end_bit_index])
    
                
        for i in range(start_bit_index):
            c = (end_bit_index + i)
            skipindex_matrix[: -c, c] = '*'

        #print(skipindex_matrix)
        
        for i in range(end_bit_index):
            skipindex_matrix[end_bit_index-i:matrix_size-i, i] = '*'
    
        res = np.where(skipindex_matrix=='*')
        res= list(zip(res[0], res[1]))
        finalskip_index.extend(res)
    
    finalskip_index = list(set(finalskip_index))
    finalskip_index.sort()
    print("Matrix", len(finalskip_index))
    print ("Processing rows")
    sys.stdout.flush()
    
    
    for msg_length in range(64):
        
        
        for remaining_field_length  in range(64-msg_length):
            
            if (msg_length,remaining_field_length) in finalskip_index:
                
                #print( "skipping Tuple is", (msg_length, remaining_field_length))
                continue
            a_packed = get_sliced_matrix(canmsgs_window_arr, msg_length,
                                                 remaining_field_length + 1)
            unique_val= np.unique(a_packed)

            #print("index being filled : ({},{})".format(msg_length, remaining_field_length))
            uniquecnt_matrix[msg_length, remaining_field_length] = len(unique_val)
        
    time_end = time.time() - time_start

    print("\nTime elapsed = {}s".format(time_end))

    #print( uniquecnt_matrix)
    #sys.exit()
    return uniquecnt_matrix, finalskip_index




def get_field_type_score(f,skip_index_arr):
    """
    Calculate a score and corresponding type for every candidate field
    as represented by the unique val counts in unique val matrix given as input.
    Return f_score and field_typen, where field_classified has possible values:
      -1 for invalid address (bottom lower-right triangle of f)
      2 for constant
      1 for multi-value
      0 for sensor/counter.
    """
    field_type = np.zeros((64, 64), dtype='str')
    classified_field = np.zeros((64, 64), dtype=np.int32)
    field_score = np.zeros((64, 64))
    T_mv = 12.0
    T_minlength = 2
    for left_bit in range(64):
        for field_length in range(64):
            
            if (left_bit, field_length) in skip_index_arr:
                continue
            
            unique_val_count = f[left_bit, field_length]
            T_maxval = min(np.sqrt(2.**(field_length+1)), T_mv)
            
            
            if unique_val_count == 0:
                field_type[left_bit, field_length] = 'NA'
                classified_field[left_bit, field_length] = -1
                field_score[left_bit, field_length] = 0
            elif unique_val_count == 1:
                field_type[left_bit, field_length] = 'c'
                classified_field[left_bit, field_length] = 2
                field_score[left_bit, field_length] = field_length+1
            elif ((field_length+1) >= T_minlength) and (unique_val_count <= T_maxval):
                field_type[left_bit, field_length] = 'm'
                classified_field[left_bit, field_length] = 1
                field_score[left_bit, field_length] = field_length+1
            else:
                field_type[left_bit, field_length] = 's'
                classified_field[left_bit, field_length] = 0
                field_score[left_bit, field_length] = np.float32(unique_val_count**2)/(2.**(field_length+1)) 
    return field_score, classified_field




def compare_fields(field1, field2):
    """
    Compare fields f1 and f2. They are both tuples containing (score, typen),
    where typen is a number with 2 for const, 1 for multi, 0 for counter/sensor.

    If f1 > f2, return True.
    """
    if field1[1] == field2[1]:
        return field1[0] > field2[0]
    else:
        return field1[1] > field2[1]


def get_field_with_max_score(f_dict):
    p_max = None
    for key, value in f_dict.items():
        if p_max is None:
            p_max = key
        else:
            if compare_fields(value, f_dict[p_max]):
                p_max = key
    return p_max


def check_field_overlap(best_field, key):
    
    
    num_overlap = len(set.intersection(
        set(range(best_field[0], best_field[0]+best_field[1]+1)),
        set(range(key[0], key[0]+key[1]+1))))
    if num_overlap:
        return True
    else:
        return False


def choose_fileds(f_score, f_typen ,skip_index_arr):

    field_dict = {}
    
    for row in range(64):
        for col in range(64-row):
            
            if(row,col) in skip_index_arr:
                
                continue
            else:
                
                field_dict[(row, col)] = (f_score[row, col], f_typen[row, col])
            
    
    chosen_fields = {}
    
    while field_dict:
        number_of_fields_in_field_dict = len(field_dict)
        
        best_field = get_field_with_max_score(field_dict)

        chosen_fields[best_field] = field_dict.pop(best_field)
        
        for key in list(field_dict.keys()):
            if check_field_overlap(best_field, key):
                field_dict.pop(key, None)
        if len(field_dict) >= number_of_fields_in_field_dict:
            print( " Error nothing is deleted from field dictionary")
            break
    
    bounday_dict = {k:tuple(change_to_str(list(v))) for k,v in chosen_fields.items()}
    return bounday_dict

def change_to_str(value):
    if value[1]== 2:
        value[1] ='CONSTANT'
    elif value[1] == 1:
        value[1] = 'MULTIVAL'
    elif value[1] == 0:
        value[1] = 'SEN/CTR'
    elif value[1] == -1:
        value[1] = 'BUG'
    return value


           
def convert_intarr_to_matrix(inpdata, output_columns=64, output_type=np.float32):
    """
    Converts sequence of data 64*64 bit matrix - Input inpdata is list of canmessages
    data field in uint8 format.
    param1: inputdata to be converted to matrix.
    param2: number of columns to be present in output matrix.
    param3: Elements datatype in ouput matrix.
    :return:
    """

    
    return np.unpackbits(inpdata.view(np.uint8)).reshape(
                (-1, output_columns)).astype(output_type)  #gives output of 64 columns 
        
def classify_can_payload_fields(cmsg_list, user_skip_list):
    
    
       
    npcmsg= np.asarray(cmsg_list,dtype = np.uint8)
   
    bit_seq =convert_intarr_to_matrix(npcmsg, output_type=np.uint32)
    
    #print("Bit seq", len(bit_seq[0]))
    f, skip_index_arr = extract_unique_valcount_from_matrix(bit_seq, user_skip_list)
       
     
    
    field_score, field_category = get_field_type_score(f,skip_index_arr)

    final_fields =choose_fileds(field_score, field_category, skip_index_arr)
    
    return final_fields




def extract_can_payload_fields(infile, canid,cmsg_list, user_specified_indexes, user_classified_fields):
        
    f_d =classify_can_payload_fields( cmsg_list, user_specified_indexes)
    f_d.update( user_classified_fields)
    #print("here", user_classified_fields)
    #sys.exit()
    
    f_list=sorted(f_d.items())
    

    field_dict=OrderedDict()
    
    field_dict["source"] = infile
    field_dict["processing"] = "CONST/SENSOR/COUNTER/MULTIVALUE"
    field_dict["can_messages"]=[]
    
    classified_indexes_info={}
    classified_indexes_info["canid"]= canid
    classified_indexes_info["fields"]= []
    
    
    field_dict["index-type"]={}
    for index,element in enumerate(f_list):
        classified_indices ={}
        classified_indices["s_no"]= index+1
        classified_indices["left_bit"]= element[0][0]
        classified_indices["length"] = element[0][1]
        classified_indices["score"] = element[1][0]
        classified_indices["type"] = element[1][1]
        classified_indexes_info["fields"].append(classified_indices)

        field_dict["index-type"][str(index+1)+"-"+str(element[0])] = str(element[1])   
    
    field_dict["can_messages"].append(classified_indexes_info)
    
    print("field dict", field_dict)         
    end = time.time()

    json_object=json.dumps(field_dict,indent = 2)
    
    # Writing to jsonfile 
    with open(infile+"_"+str(canid)+"_classified_fields.json", "w") as outfile: 
        outfile.write(json_object) 
    print( " classified  {0:} lines in {1:.4f} seconds.".format(num_lines, end-start))



if __name__ == "__main__":
    
    
    parsers = {
            'otids' : can_message.parse_otids_line,
            'csv' : can_message.parse_csv_line,
            'canshort' : can_message.parse_canshort_line,
            'canlong' : can_message.parse_canlong_line,
            'pcap' : can_message.parse_pcaptxt_line,
            'drdc' : can_message.parse_drdc_line
    }

    argp = argparse.ArgumentParser(description='Convert traces to canplayer log file.')
    argp.add_argument('-b', '--bus', type=str, default='vcan1', help='CAN bus interface.')
    argp.add_argument('-i', '--informat', type=str, default='otids', help='otids|csv|canshort|canlong|pcap|drdc')
    argp.add_argument('-o', '--outfile', type=str, default=None, help='Optional output file')
    argp.add_argument('infile', type=str, help='Trace/Template file.')

    args = argp.parse_args()

    infile = args.infile
    outfile = args.outfile
    busname = args.bus
    infrmt = args.informat

    if infrmt not in parsers:
        print('Input format: {} is not a valid format.'.format(infrmt))
        sys.exit(1)

    parser = parsers[infrmt]

    start = time.time()

    num_lines = 0
    cmsg_dict ={}


    with open(infile, "r") as ifile:
        for line in ifile:
            cmsg = parser(line)
            
            if not (cmsg.arb_id in cmsg_dict):
                cmsg_dict[cmsg.arb_id]=[]
                cmsg_dict[cmsg.arb_id].append(cmsg.data)
            elif cmsg.arb_id in cmsg_dict:
                cmsg_dict[cmsg.arb_id].append(cmsg.data)
            else:
                
                print("BUG")
                
            num_lines += 1
    
    
    
    with open('field_defn.json') as f:
        j= json.load(f)
        
        
        for can_id_info in j['can_messages']:
                
            user_specified_indexes=[]
            user_classified_fields={}
            
            print("id is ", can_id_info['canid'])
            
            for index_info in can_id_info['fields']:
                ctr_index = (index_info['left_bit'], index_info['length'])
                print(ctr_index)
                user_specified_indexes.append(ctr_index)
                user_classification = (index_info['score'], index_info['type'])
                user_classified_fields[ctr_index] = user_classification
            
            if can_id_info['canid'] in cmsg_dict:
                
                cmsg_list = cmsg_dict[can_id_info['canid']]
                
                extract_can_payload_fields( infile,can_id_info['canid'],cmsg_list, user_specified_indexes, user_classified_fields)
                
                cmsg_dict.pop(can_id_info['canid'])
            else:
                print(" {} is not present in input dataset".format(can_id_info['canid']))
                
        
        while( cmsg_dict):  # classify canids that are not specified by user but present in dataset
            print("still canids exists")
            k_list= list(cmsg_dict.keys())
            for k in k_list:
                extract_can_payload_fields(infile, k,cmsg_dict[k], [],{})
            
        sys.exit()

