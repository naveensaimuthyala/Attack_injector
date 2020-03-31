import argparse
import io
import sys, os

def as_html(outfile, tables,caption):
    print("<!DOCTYPE html><html><head>", file=outfile)
    print("<style>table, th, td { border: 1px solid black; }</style>", file=outfile)
    print("</head><body>", file=outfile)
    print("<h1 style=\"color:green;\">{}</h1>".format(caption), file=outfile)
    for t in tables:
        print(t, file=outfile)

    print("</body></html>", file=outfile)
    
def html_confmatrix(confusion_matrix, title):
    output = io.StringIO()
    
    tp = confusion_matrix["TP"]
    fp = confusion_matrix["FP"]
    tn = confusion_matrix["TN"]
    fn = confusion_matrix["FN"]
    
    acc = float(tp + tn)/float(tp+fp+tn+fn)
    tpr = float(tp)/float(tp+fn)
    
    
    output.write('<h2 style=\"color:blue;\">{}</h2>\n'.format(title))
    output.write('<table>\n')
    output.write("<tr><th></th><th>Actual Attack</th><th>Actual Regular</th></tr>")
    output.write("<tr><th>Predicted Attack</th><td>TP ={}</td><td>FP ={}</td></tr>"\
            .format(confusion_matrix["TP"],confusion_matrix["FP"]))
    output.write("<tr><th>Predicted Regular</th><td>FN ={}</td><td>TN ={}</td></tr>"\
            .format(confusion_matrix["FN"],confusion_matrix["TN"]))
    output.write("</table>\n")
    output.write("<br>\n")
    output.write("<h4  style=\"color:#00FF33;\">Accuracy TP+TN/(TP+FP+TN+FN) = {}<h4>".format(acc))
    output.write("<br>\n")
    
    res = output.getvalue()
    output.close()
    return res

class dad_line_obj():
    def __init__(self, parts):
        self.entropy_alert = None
        if (len(parts) > 9):
            self.ts = float(parts[0])
            self.canid = parts[1]
            self.imt = parts[2]
            self.imt_anom = parts[3]
            self.anom_score_alert = parts[4]
            self.anom_score = parts[5]
            self.win_count_alert = parts[6]
            self.win_count = parts[7]
            self.time_win_alert = parts[8]
            self.time_win = parts[9]
        if (len(parts) > 10):
            self.entropy_alert = parts[10].rstrip()
        else:
            print("DAD Error readline line", parts)
            
class line_comparator():
    def __init__(self, gline, dline):
        self.all_clear = True  #This is a regular line with no detection.
        self.gt = gline
        self.dad = dline
        
        if (gline.ts != dline.ts):
            self.ts_err = True
            self.ts_skew = float(gline.ts) - float(dline.ts)
            self.all_clear = False
        else:
            self.ts_err = False
            self.ts_skew = 0.0
        
        #Process anomalies at message level.
        if (gline.typ == "R"):
            if (dline.imt_anom == "OK"):
                self.IMT = "TN"
            else:
                self.IMT = "FP"
                self.all_clear = False
                
            if (dline.anom_score_alert == "OK"):
                self.ALERT_AS = "TN"
            else:
                self.ALERT_AS = "FP"
                self.all_clear = False
                    
            if (dline.win_count_alert == "OK"):
                self.ALERT_WC = "TN"
            else: 
                self.ALERT_WC = "FP"
                self.all_clear = False
                
            if (dline.time_win_alert == "OK"):
                self.ALERT_TW = "TN"
            else:
                self.ALERT_TW = "FP"
                self.all_clear = False
        else:  #Source trace has attack message.
            self.all_clear = False
            if (dline.imt_anom == "OK"):
                self.IMT = "FN"
            else:
                self.IMT = "TP"
                
            if (dline.anom_score_alert == "OK"):
                self.ALERT_AS = "FN"
            else:
                self.ALERT_AS = "TP"
                    
            if (dline.win_count_alert == "OK"):
                self.ALERT_WC = "FN"
            else: 
                self.ALERT_WC = "TP"
                
            if (dline.time_win_alert == "OK"):
                self.ALERT_TW = "FN"
            else:
                self.ALERT_TW = "TP"

                
    def __str__(self):
        return '{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}'.format(\
            self.dad.ts, self.dad.canid, self.gt.typ, self.gt.seqid, self.dad.imt_anom, self.dad.imt, self.IMT,\
            self.dad.anom_score_alert, self.dad.anom_score, self.ALERT_AS, self.dad.win_count_alert, self.dad.win_count, self.ALERT_WC,\
            self.dad.time_win_alert, self.dad.time_win, self.ALERT_TW)
        
def get_line_comparator(gtt_line, dad_line, line_num):
    gline = gtt_line_obj(gtt_line.split(','))
    dline = dad_line_obj(dad_line.split(','))
    return line_comparator(gline, dline)

def print_confusion_matrix(name, matrix, out):
    sum = 0
    for m in matrix.values():
        sum = sum + m
        
    TP = matrix["TP"]
    TN = matrix["TN"]
    FP = matrix["FP"]
    FN = matrix["FN"]
        
    print("{},{},{},{},{},{}".format(name, TP, FP, FN, TN, sum), file=out)
    
    
parser = argparse.ArgumentParser(description='DAD Validator')
parser.add_argument('-t', '--tracename', type=str, default=None, 
                    help='Trace name')
parser.add_argument('-a', '--attackname', type=str, default=None,
                    help='Attack name')
parser.add_argument('-d', '--dadtest', type=str, default=None,
                    help='DAD test name.')
parser.add_argument('-I', '--imt', help='Show IMT results.', action='store_true')
parser.add_argument('-H', '--entropy', help='Show Entropy results.', action='store_true')
parser.add_argument('-T', '--html', type=str, default=None, help='HTML Output File')
parser.add_argument('-C', '--caption', type=str, default=None, help='HTML File Caption')

args = parser.parse_args()

if not args.tracename:
    print("tracename (-t) is required.");
    sys.exit(0)
    
if not args.attackname:
    print("attackname (-a) is required.");
    sys.exit(0)
    
if not args.dadtest:
    print("attackname (-d) is required.");
    sys.exit(0)
    
if args.imt is True:
    print('Displaying IMT Results');
    
if args.entropy is True:
    print('Displaying Entropy Results');
    
class gtt_line_obj():
    def __init__(self, parts):
        if (len(parts) == 3):
            self.ts = float(parts[0])
            self.typ = parts[1]
            self.seqid = parts[2].rstrip()
        else:
            print("GTT Error readling line ", parts)    
    

trace_attack_log = args.tracename + "." + args.attackname + ".log"
trace_attack_gt = args.tracename + "." + args.attackname + ".gtt"
dad_output = args.tracename + "." + args.attackname + "." + args.dadtest + ".dad"
val_log = args.tracename + "." + args.attackname + "." + args.dadtest + ".vlog"
val_cm = args.tracename + "." + args.attackname + "." + args.dadtest + ".cm"
val_html = args.tracename + "." + args.attackname + "." + args.dadtest + ".html"

print("Trace attack log = ", trace_attack_log)
print("Trace attack ground truth = ", trace_attack_gt)
print("DAD ouptut = ", dad_output)
print("Validator Output = ", val_log)
print("Validator Confusion = ", val_cm)
print("Validator HTML = ", val_html)

count = 0

imt_conf_matrix = { "TP": 0, "FP": 0, "TN": 0, "FN": 0 }
alert_as_conf_matrix = { "TP": 0, "FP": 0, "TN": 0, "FN": 0 }
alert_wc_conf_matrix = { "TP": 0, "FP": 0, "TN": 0, "FN": 0 }
alert_tw_conf_matrix = { "TP": 0, "FP": 0, "TN": 0, "FN": 0 }
alert_H_conf_matrix = { "TP": 0, "FP": 0, "TN": 0, "FN": 0 }

#Increment when we see an attack.
attack_on = 0

with open(trace_attack_gt) as gtt_file,open(dad_output) as dad_file, open(val_log, "w") as vlog:
    print("Line,TS,CANID,MSG-TYPE,SEQ,IMT_ANOM,IMT,IMT_STATUS,ALERT_ASCORE,ASCORE,"\
          "ASCORE_DEC,ALERT_WCOUNT,WCOUNT,WCOUNT_DEC,ALERT_TWIN,TWIN,TWIN_DEC", file=vlog)
    for gtt_line, dad_line in zip(gtt_file, dad_file):
        cmp = get_line_comparator(gtt_line, dad_line, count)
        
        if cmp.gt.typ != 'R':
            attack_on += 1
        
        imt_conf_matrix[cmp.IMT] += 1
        alert_as_conf_matrix[cmp.ALERT_AS] += 1
        alert_wc_conf_matrix[cmp.ALERT_WC] += 1
        alert_tw_conf_matrix[cmp.ALERT_TW] += 1
        
        if cmp.dad.entropy_alert is not None and cmp.dad.entropy_alert != 'Skipped':
            if (attack_on > 0): #Some attacks detected.
                if (cmp.dad.entropy_alert == 'Alert'):
                    alert_H_conf_matrix["TP"] += 1
                else:
                    alert_H_conf_matrix["FN"] += 1
            else:
                if (cmp.dad.entropy_alert == 'Alert'):
                    alert_H_conf_matrix["FP"] += 1
                else:
                    alert_H_conf_matrix["TN"] += 1
            attack_on = 0
        
        print('{}, {}'.format(count, str(cmp)), file=vlog)
        
        count += 1
        
with open(val_cm, "w") as mout:      
    print("CAT,TP,FP,FN,TN,SUM", file=mout)

    if args.imt is True:
        print_confusion_matrix("IMT", imt_conf_matrix, mout)
        print_confusion_matrix("ALERT WIN COUNT", alert_wc_conf_matrix, mout)
    elif args.entropy is True:
        print_confusion_matrix("ENTROPY ALERTS", alert_H_conf_matrix, mout)
    else:
        print_confusion_matrix("IMT", imt_conf_matrix)
        print_confusion_matrix("ALERT ANOMALY SCORE", alert_as_conf_matrix, mout)
        print_confusion_matrix("ALERT WIN COUNT", alert_wc_conf_matrix, mout)
        print_confusion_matrix("ALERT TIME WIN", alert_tw_conf_matrix, mout)
        print_confusion_matrix("ENTROPY ALERTS", alert_H_conf_matrix, mout)

    
if args.html is not None:
    caption = "Results"
    if args.caption is not None:
        caption = args.caption
    
    html_file = open(args.html, 'w')
    tables = []
    
    if args.imt is True:
        tables.append(html_confmatrix(imt_conf_matrix, "IMT Anomaly Confusion Matrix"))
        tables.append(html_confmatrix(alert_wc_conf_matrix, "Win Count Alert Confusion Matrix"))
    elif args.entropy is True:
        tables.append(html_confmatrix(alert_H_conf_matrix, "Entropy Confusion Matrix"))
    else:
        tables.append(html_confmatrix(imt_conf_matrix,"IMT Anomaly CM"))
        tables.append(html_confmatrix(alert_as_conf_matrix, "Anomaly Score Alerts CM"))
        tables.append(html_confmatrix(alert_wc_conf_matrix, "Win Count Alert CM"))
        tables.append(html_confmatrix(alert_tw_conf_matrix, "Time Window CM"))
        tables.append(html_confmatrix(alert_H_conf_matrix, "Entropy CM"))        
    as_html(html_file, tables, caption)

print("All done.")
