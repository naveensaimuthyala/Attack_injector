USAGE dadpoc 

Running with no special options

./dadpoc -t Kia_m304.log -m Kia_m304.noattack.log -i -n test1

Where 
-t is the name of the training file.  This should be the canplayer .log
file used to generate the attack file

-m is the name of the file to be monitored for attacks.

-i use IMT threshold
-c filter on CANID (Don't use this option if you plan to use the validator, it
                    assume one output for every msg in the source file for which
                    you have ground truth).
                    
-e use entropy detection.
-n test name       (DAD agent will append this to BaseName.AttackName.log to give
                    you BaseName.AttackName.TestName

dadpoc will output two files.

BaseName.AttackName.TestName.adp (Command used to create this dataset)
BaseName.AttackName.TestName.dad (Results of DAD that can be fed to validator)

TUNING PARAMETERS (Upper case identifiers are use for parameters)

The following parameters will impact the operation of the DAD algorithms.  None of
these parameters are required, and if they are skipped the indicated defaults will
be used.

ANOMALY SCORE PARAMETERS

-B [integer]   Integral value that specified the backoff rate. Impacts the 
               Anomaly Score method.  When an anomalous IMT is encountered
               the anomaly score is incremented, and upon reaching this 
               a threshold will generate an alert.  When B consecutive 
               GOOD imts are encountered the Anomaly score is decremented.
               [Default 5]
               
-R [integer]   The threshold used the the Anomaly Score.  If the score reaches
               this value then an alert is raised.
               [Default 8]
               
WINDOW COUNT PARAMETERS
               
-W [integer]   Window threshold. It this many anomalous IMTs appear with the
               test window, then an alert is raised [Default 10]
               
TOTAL TIME WINDOWS
               
-C [float]     Used to set the epsilon value to the total time window. For
               every 100 messages (depending on buffer size) we calculate the
               total time this represents. During training we determine the
               minimum (Tmin) and maximum (Tmax) windows encountered.  
               
               Let R = Tmax - Tmin.
               
               During monitoring we calculate the current Twin value, and raise
               an alert if the following condition does not hold.
               
               Tmin - (R*C)  <=   Twin     <=    Tmax + (R*C)
               
               [Default 0.15]

DBSCAN RELATED PARAMETERS

These parameters influence the DBSCAN operation used to identify the range
of normal IMTs, as such they will impact both the Anomaly Score and Window Count
methods (but not Total Time Window method which effectively doesn't care about
individual IMT values).
               
-D [float]      DBSCAN window size ratio.  This determines the size of the 
                search window for clusters as a percentage of the total number of
                bins.
                [Default 0.0075]
                
-P [float]      DBSCAN adds a bin to a cluster if the number of points inside
                the search windows exceeds a certain number of points. This 
                number of points (NP) is a function of the total number of observations N
                times the ratio (P).  So NP = N * P.
                [Default 0.01]
                
Example:

./dadpoc -t Kia_m304.log -m Kia_m304.noattack.log -i -n test1 -C=0.1 -P=0.005 -D=0.01
               
               

