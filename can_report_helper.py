import sys, os , shutil
import json
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
import collections
import pandas as pd

class GenerateReport():

    """
    This class helps to generate basic statistics of each CanMessage data frame parsed to it. 
    """
    def __init__(self , canid_dict =dict(),perid_count= dict(), canstats=[], sum_avg= dict() ):
        self.canid_dict=canid_dict # dictionary to store the addition of logical 1 bits . it stores key as arb-id and value as array of data field i.e 64bits
        self.perid_count = perid_count # dictionary to store the count of each unique id on whole data.
        self.can_stats= [0]*64 # intialised array of size 64 to store can statistics of entire data
        self.sum_avg=sum_avg


    def parse_canmsg_datafield(self, cmsg):
        """
        This function parses payload filed afile_pathnd stores sum/avg in a dictionary and returns sum/avg disctionary
        """

            
            #print("{} \n".format(cmsg.arb_id))
        if  not ((cmsg.arb_id in self.canid_dict) and (cmsg.arb_id in self.perid_count)):
            self.canid_dict[cmsg.arb_id]= [0]*64  
            self.perid_count[cmsg.arb_id]= 0


        if cmsg.arb_id in self.perid_count:

            temp_int = self.perid_count[cmsg.arb_id]
            temp_int +=1
            self.perid_count[cmsg.arb_id]= temp_int


        for index, bit in enumerate(cmsg.binary_candata):
            if bit== 1:
                self.can_stats[index] += 1
                if cmsg.arb_id in self.canid_dict:
                    temp_arr= self.canid_dict[cmsg.arb_id]
                    temp_arr[index]+=1
                    self.canid_dict[cmsg.arb_id]= temp_arr

        for key in self.canid_dict:
            value1= self.canid_dict.get(key)
            value2= self.perid_count.get(key)
            value3=[round(eachbit/value2,2) for eachbit in value1]
            self.sum_avg[key]= value3
            
        return self

class GenerateTimeseries():
    def __init__(self):
        self.timeseries=dict()
        self.dict2=dict()
        self.prev_value= 0
        self.time_intvl = []
    def parse_canmsg_timestamp(self, cmsg, canid):
        
        if( canid== cmsg.arb_id):
            if not(canid in self.timeseries):
                self.prev_value = cmsg.timestamp
                self.timeseries[canid]={}
                self.timeseries[canid][cmsg.timestamp]= 0
            elif canid in self.timeseries:
                difference=  round(cmsg.timestamp-self.prev_value, 4)
                self.timeseries[canid][cmsg.timestamp]= difference
                self.prev_value= cmsg.timestamp


        return self
    def generate_timeseries_plots(self, canid,  infile, timeseries_bin_cnt_frame):
        """
        This function generates the 2 seperate plots to analyse can data 
        1. Bins plot to check how many can data pkts are present in each bin , bins are divided in to 40 numbers
            the minimum being first timestamp and maximum being last time stamp
        2. Data distribution plot with two subplots 
            Subplot1:
            Subplot2:
        All plots are saved to inputfile_plots folder folder in current working directory
        """
        print(" input",infile)
        inpfile= infile.replace(".txt", "").replace("./", "")
        current_file_path = os.path.dirname(os.path.abspath(__file__)) # Figures out the absolute path  in case your working directory moves around.
        path_to_save_plots = current_file_path+"/"+inpfile+"_plots"
        pktcnt_intimeseries = Counter(self.timeseries[canid].values())
        pktcnt_intimeseries= dict(pktcnt_intimeseries) 
        od = collections.OrderedDict(sorted(pktcnt_intimeseries.items()))
        k=list(od.keys())
        v= list(od.values())
        df = pd.DataFrame(list(zip(k, v)), columns =['time_intvl', 'cnt'], index=None) 
        nBins = 40
        my_bins = np.linspace(df.time_intvl.min(),df.time_intvl.max(),nBins)
        bindf=df.groupby(pd.cut(df.time_intvl, bins =nBins)).sum()['cnt']
        lists = sorted(self.timeseries[canid].items()) # sorted by key, return a list of tuples
        x, y = zip(*lists) # unpack a list of pairs into two tupleshttps://catalogue.uottawa.ca/en/graduate/master-applied-science-electrical-computer-engineering/#Coursestext
        fig, ax = plt.subplots(nrows=3, ncols=1, figsize=(60, 50))
        fig.suptitle("Timeseries plot for Can id : {}".format(canid),fontweight="bold", size=30) # Title
        ax[0].plot(k,v) #row=0, col=0
        ax[1].plot(x,y) #row=0, col=1
        ax[2] =bindf.plot(kind='bar',figsize=(50,45), fontsize = 25)

        ax[1].set_xlabel("Timestamp of canid in seconds", fontsize = 25)
        ax[1].set_ylabel("Inter packet Time interval" , fontsize=25)
        ax[1].xaxis.set_tick_params(labelsize=25)
        ax[1].yaxis.set_tick_params(labelsize=25)

        ax[0].set_xlabel("Inter packet Time interval", fontsize=25)
        ax[0].set_ylabel("Number of CAN packets", fontsize=25)
        ax[0].xaxis.set_tick_params(labelsize=25)
        ax[0].yaxis.set_tick_params(labelsize=25)

        ax[2].set_xlabel(" Time Interavl Range bins  ", fontsize =25)
        ax[2].set_ylabel(" Number of can pkts in a bin", fontsize=25)
        ax[2].set_title(" Bin plots for No of pkts in a Timeseries bin",fontsize=25)
        
        try:
            if not os.path.exists(path_to_save_plots):
                os.makedirs(path_to_save_plots)
        except Exception as e:
            print('Failed to create directory  {}. Reason: {}'.format(path_to_save_plots, e))
        
        fig.savefig(path_to_save_plots+"/"+str(canid)+".png", dpi=150)
        bindf.to_csv( path_to_save_plots+"/"+str(canid)+".csv")

        plt.close('all')

def report_error_handler(repotype):
    """
    This function handles error if none of report types are choosen in arguments 
    """
    if repotype== None:
        print(" --- please select the report type sums/avg|timeseries")
        sys.exit()
    else:
        return


def fill_dict_with_ids(file, parser, dictionary):
    """
    This function is used to create a dictionary of unique can ids before doing IMT for each CAN-ID 
    """
    with open(file, "r") as ifile:
        for line in ifile:
            cmsg = parser(line)
            if cmsg.arb_id in dictionary :
                dictionary[cmsg.arb_id]+= 1
            else:
                dictionary[cmsg.arb_id]=1
    
    







    

    


