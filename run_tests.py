import subprocess , os
import json
import sys
import shutil
import argparse

def SubDirPath (d):
    return list(filter(os.path.isdir, [os.path.join(d,f) for f in os.listdir(d)]))


class Attack_inj_params:
    def __init__( self, d,j,items):
        self.d = d
        self.j = j      
        self.test_name   = items['name']
        self.attack_name = items['attack']
        self.informat = items['informat']
        self.attack_start_time = items['attackstarttime']
        self.attack_duration = items['attackduration']
        self.imt = items['imt']
        self.can_id = items['can_id']
        self.replay_seq_length = items['replay_seq_length']
        self.number_of_times_to_replay = items['number_of_times_to_replay']
        

        
        self.attack_inj_arguments =""
       
        
    def attack_inj_params ( self):
        
        attck_file=os.path.isfile(self.d+'/'+self.test_name+"/"+self.j['Testfile']['name']+"."+self.attack_name+".log")
        gnd_truth_file=os.path.isfile(self.d+'/'+self.test_name+"/"+self.j['Testfile']['name']+"."+self.attack_name+".gtt")
        params_file=os.path.isfile(self.d+'/'+self.test_name+"/"+self.j['Testfile']['name']+"."+self.attack_name+"_params.json")
        
        if( attck_file and gnd_truth_file and params_file):
            return "already exists"
        
           
        if self.attack_name in ["dos_vol" , "dos_prio", "fuzzy_ins"]:
            
            if self.imt == "default":
                
                attack_inj_arguments = "python3,attack_injector.py,-i,{},-a,{},-at,{},-ad,{},-t,{},{}".format(self.informat,self.attack_name,self.attack_start_time, \
                    self.attack_duration,self.d+'/'+self.test_name, self.d+'/'+self.j['Testfile']['name']+'.log')
            else:
                
                attack_inj_arguments = "python3,attack_injector.py,-i,{},-a,{},-at,{},-ad,{},-imt,{},-t,{},{}".format(self.informat,self.attack_name,self.attack_start_time, \
                    self.attack_duration,self.imt,self.d+'/'+self.test_name, d+'/'+self.j['Testfile']['name']+'.log')
                
        elif self.attack_name in [ "fuzzy_owrite"]:
                   
            attack_inj_arguments = "python3,attack_injector.py,-i,{},-a,{},-at,{},-ad,{},-t,{},{}".format(self.informat,self.attack_name,self.attack_start_time, \
                self.attack_duration,self.d+'/'+self.test_name, self.d+'/'+self.j['Testfile']['name']+'.log')
        
        elif self.attack_name in ["replay"]:
            
            if self.can_id == "default":
                self.can_id = -1
            if self.replay_seq_length == "default":
                self.replay_seq_length = 1
            if self.number_of_times_to_replay == "default":
                self.number_of_times_to_replay= 1
            if self.imt == "default":
                
                attack_inj_arguments = "python3,attack_injector.py,-i,{},-a,{},-at,{},-ad,{},-id,{},-w,{},-rn,{},-t,{},{}"\
                    .format(self.informat,self.attack_name,self.attack_start_time, \
                        self.attack_duration, self.can_id, self.replay_seq_length, self.number_of_times_to_replay,\
                            self.d+'/'+self.test_name, self.d+'/'+self.j['Testfile']['name']+'.log')
            else:
                 attack_inj_arguments = "python3,attack_injector.py,-i,{},-a,{},-at,{},-ad,{},-id,{},-imt,{},-w,{},-rn,{},-t,{},{}"\
                    .format(self.informat,self.attack_name,self.attack_start_time,\
                        self.attack_duration, self.can_id,self.imt, self.replay_seq_length, self.number_of_times_to_replay,\
                            self.d+'/'+self.test_name, self.d+'/'+self.j['Testfile']['name']+'.log') 
                    
                
        return attack_inj_arguments
    

    

  
  
                                      
class Dad_agent_params:
    def __init__(self,d,j,items, dad_test):
        
        self.d = d
        self.j = j      
        self.test_name   = items['name']
        self.attack_name = items['attack']
        self.dad_test_name = dad_test['dad_test_name']
        self.dad_imt = dad_test['dad_imt']
        self.dad_entropy = dad_test['dad_entropy']
        
        self.anom_bckof_rate = dad_test[ 'B']
        self.anom_threshold = dad_test['R']
        self.window_threshold = dad_test['W']
        self.time_win_eps = dad_test['C']
        self.dbscan_win_size = dad_test['D']
        self.dbscan_cluster_len = dad_test['P']      
        self.dad_arguments = ""
         


    def dad_agent_params( self):
        
        if (self.dad_imt == "1" and self.dad_entropy == "1"):
            
            dad_arguments = "dad_agent/dadpoc,-t,{},-m,{},-B,{},-R,{},-W,{},-C,{},-D,{},-P,{},-i,-e,-n,{}".format(self.d+"/"+self.j['Testfile']['name']+".log" , \
                self.d+"/"+self.test_name+"/"+self.j['Testfile']['name']+"."+self.attack_name+".log" ,self.anom_bckof_rate, self.anom_threshold,self.window_threshold, \
                    self.time_win_eps,self.dbscan_win_size,self.dbscan_cluster_len,self.test_name)
            
        elif(self.dad_imt =="1" and self.dad_entropy !="1"):
            
            dad_arguments = "dad_agent/dadpoc,-t,{},-m,{},-B,{},-R,{},-W,{},-C,{},-D,{},-P,{},-i,-n,{}".format(self.d+"/"+self.j['Testfile']['name']+".log" , \
                self.d+"/"+self.test_name+"/"+self.j['Testfile']['name']+"."+self.attack_name+".log" ,self.anom_bckof_rate, self.anom_threshold,self.window_threshold, \
                    self.time_win_eps,self.dbscan_win_size,self.dbscan_cluster_len,self.test_name)
            
        elif(self.dad_imt !="1" and self.dad_entropy =="1"):
            
            dad_arguments = "dad_agent/dadpoc,-t,{},-m,{},-B,{},-R,{},-W,{},-C,{},-D,{},-P,{},-e,-n,{}".format(self.d+"/"+self.j['Testfile']['name']+".log" , \
                self.d+"/"+self.test_name+"/"+self.j['Testfile']['name']+"."+self.attack_name+".log" ,self.anom_bckof_rate, self.anom_threshold,self.window_threshold, \
                    self.time_win_eps,self.dbscan_win_size,self.dbscan_cluster_len,self.test_name)
            
        elif(self.dad_imt =="0" and self.dad_entropy =="0"):
            
            print("**Both IMT and Entropy cannot be 0 **\n **please choose atleast one method** ")
            sys.exit()
            

        return  dad_arguments       


    def dad_validator_params(self, dad_file_path):
    
        validator_arguments = "python3,dad_validator/dad-validator.py,-t,{},-a,{},-d,{},-p,{},-I,-H"\
            .format( self.d+"/"+self.test_name+"/"+self.j['Testfile']['name'],self.attack_name,self.test_name,dad_file_path)
                
        return validator_arguments
    
 
 
 
            
def remove_file_if_exists(filename):
    if os.path.isfile(filename):
        try:
            print("File already exists- overwriting {}".format(os.path.basename(filename)))
            os.remove(filename)
        except OSError:
            pass
        
def create_directory_ifnot_exists(directory):
    
    if not os.path.exists(directory): 
        os.makedirs(directory)
         

argp = argparse.ArgumentParser(description='This File is intented to Run Multiple tests sequentially')
argp.add_argument('-c', '--clean', type=str, default='N', help=' Cleans all files Yes|Y|No|N')


args = argp.parse_args()

clean_command = args.clean

    
    
test_dir= SubDirPath('validation')

if( clean_command in ["Y", "yes"]):
    pass # have to implement deletion 
    



for d in test_dir:

    with open (d+'/'+'test.json') as f:
        j = json.load(f)
        for items in j['Testfile']['Tests']:
            print(items['dad_tests'])
                                  
            attack_inj_arg=Attack_inj_params(d,j,items)
            
            inj_params= attack_inj_arg.attack_inj_params()
            print( "obj",inj_params)
            if inj_params != "already exists":    
                attack_inj_list = list(inj_params.split(","))

                inj_result = subprocess.run(attack_inj_list, stdout=subprocess.PIPE)
                inj_result = inj_result.stdout.decode('utf-8')
                print(inj_result)
            else:
                print("***Skipping Generation of attack file***")
            
            for each_test in items['dad_tests']:
                print( each_test)
                
                dad_obj= Dad_agent_params(d,j,items, each_test)
                dad_params = dad_obj.dad_agent_params()
                
                print("dad_p",dad_params)
                
                dad_agent_list= list(dad_params.split(","))

                dad_result = subprocess.run(dad_agent_list,env={'PATH': '/dad_agent/dadpoc'},stdout=subprocess.PIPE)
                dad_result = dad_result.stdout.decode('utf-8')
                print(dad_result)
                
                
                full_path = os.path.dirname(os.path.abspath(__file__))
                dad_agent_dest_path = full_path+"/"+dad_obj.d+"/"+dad_obj.test_name+"/"+dad_obj.dad_test_name
                create_directory_ifnot_exists(dad_agent_dest_path)
                
                #All generated files from dad agent will be saved to run_tests file direc before moving them
                adp_file_curr_path = dad_obj.j['Testfile']['name']+"."+dad_obj.attack_name+"."+dad_obj.test_name+"."+"adp"
                dad_file_curr_path = dad_obj.j['Testfile']['name']+"."+dad_obj.attack_name+"."+dad_obj.test_name+"."+"dad"
                dad_log_curr_path= dad_obj.j['Testfile']['name']+"."+dad_obj.attack_name+"."+dad_obj.test_name+"."+"dad-log"
                
                dad_files = [adp_file_curr_path, dad_file_curr_path , dad_log_curr_path]
                #Move all dad-agent created files to validation/dataset/test<n> directory

                for dad_agent_file in dad_files:
                    
                    chck_file_exists = dad_agent_dest_path+"/"+os.path.basename(dad_agent_file)
                    remove_file_if_exists(chck_file_exists)   #Remove file if it is existing inplace already                 
                    dad_agent_file = full_path+"/"+dad_agent_file
                    shutil.move( dad_agent_file , dad_agent_dest_path)
                
                
                
                validator_arg = dad_obj.dad_validator_params(dad_agent_dest_path)
                varg_list= list(validator_arg.split(","))

                print("attackname path",varg_list)
            
                validator_res =subprocess.Popen(varg_list ,stdout=subprocess.PIPE)           
                stdout = validator_res.communicate()[0]
                dad_validator_res = stdout.decode('utf-8')
                print(dad_validator_res)           

                
                
                