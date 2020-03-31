import std.algorithm;
import std.array;
import std.conv;
import std.file;
import std.getopt;
import std.math;
import std.range;
import std.stdio;
import std.string;
import std.typecons;

import circbuffer;
import stats_aggregator;

/* Globals */
enum imtAnomalyWin = 25; /* Window to count anomalous/non-anomalous IMTs */
enum windowSize = 100; /* Number of can messages stored in buffer. */

struct Globals {
    double k = 4;
    double hk = 1.5;
    double twin_threshold = 0.15;
    int anom_backoff_rate = 5;
    int win_anomaly_threshold = 10;
    int running_anomaly_threshold = 8;
    double dbscan_win_size_ratio = 0.0075;
    double dbscan_pts_ratio = 0.01;
    bool verbose = false;
    std.stdio.File hreport;
    std.stdio.File log;
}

Globals globals;

struct can_msg {
    double ts;
    ushort canid;
    ubyte dlc;
    ubyte[8] payload;
}

enum EntropyAlert {skipped, ok, alert};

string EntropyAlertAsString(EntropyAlert el) {
    switch(el) {
        case EntropyAlert.skipped:
            return "Skipped";
        case EntropyAlert.ok:
            return "OK";
        case EntropyAlert.alert:
            return "Alert";
        default:
            return "?";
    }
}

struct entropyAlertInfo 
{
    ubyte[16] win_scores;
    float[16] entropies;
    ubyte total_score;
}


struct messageReport 
{
    bool imt_anomalous = false;
    bool score_alert = false;
    uint score_val = 0;
    bool window_count_alert = false;
    uint wincount_val = 0;
    bool total_time_alert = false;
    double total_time_val = 0.0;
    double imt = 0.0;
    EntropyAlert entropy = EntropyAlert.skipped;
    entropyAlertInfo entropy_info;
}

void print_can_msg(can_msg cm) {
    writef("TS = %f  ID = %d  DLC = %d ", cm.ts, cm.canid, cm.dlc);
    writeln(cm.payload);
}

can_msg parse_can_message(char[] line)
{
    can_msg result;
    
    auto parts = line.splitter!(a => a=='#' || a==' ').array;
    
    result.ts = to!double(strip(parts[0], "(", ")"));
    result.canid = parse!ushort(parts[2], 16);
    result.dlc = to!ubyte(parts[3].length / 2);
    
    int idx;
    foreach(hpair; parts[3].chunks(2)) {
        result.payload[idx++] = parse!ubyte(hpair, 16);
        if (idx == 8) break; //Just to be safe.
    }
    
    return result;
}

float entropy( ubyte[] arr ) {
    float total = 0.0;
    float p_i;
    
    float N = sum( arr[] );
    
    for (int i = 0; i < arr.length; i++) {
        if (arr[i] == 0) continue;
        p_i = to!float(arr[i])/N;
        total += p_i * log2(p_i);
    }
    
    return -total;
}

//Note we assume a window < 256 elements.
float[16] calc_entropy( CircularBuffer!(can_msg, windowSize) buffer) {
    ubyte[16][16] counts = 0;
    ubyte[] payload;
    ubyte word1, word2;
    
    //Count up the symbols appearing in each word.
    for (uint i = 0; i < buffer.length; ++i) {
        payload =  buffer.at(i).payload;
        for (uint j = 0; j < 8; ++j) {
            word1 = payload[j] & 0xf;
            word2 = payload[j] >> 4;
            
            counts[j*2][word1]++;
            counts[j*2+1][word2]++;
        }
    }
    
    float[16] entropies = 0.0;
    
    for (uint word = 0; word < 16; ++word) {
        entropies[word] = entropy( counts[word] );
    }
    
    return entropies;
}

bool has_key(T,K)(K key, T[K] aa) {
    if ((key in aa) == null) {
        return false;
    }
    return true;
}

struct CanIdInfo {
    StatsAggregator!double imts;
    StatsAggregator!(float)[16] entropies;
    
    ushort canid;
    double Tmin = double.max;
    double Tmax = 0.0;
    bool filling = true;
    bool training = true;
    
    CircularBuffer!(can_msg, windowSize) buffer;
    CircularBuffer!(bool, imtAnomalyWin) imt_anom_buffer;
    
    uint imt_alerts = 0;
    uint entropy_alerts = 0;
    uint window_count = 0; //Number of entropy windows evaluated.
    uint ts_threshold = 0;
    uint anomalous_imts_count = 0;
    uint twin_anomalies = 0;
    
    bool imt_modeling = false;
    bool entropy_modeling = false;

    
    this(ushort canid, bool imt, bool entropy) {
        this.canid = canid;
        
        this.imt_modeling = imt;
        this.entropy_modeling = entropy;
        
        if (this.imt_modeling) {
            this.imts.set_bins(2048);
        }
        
        if (this.entropy_modeling) {
            for(int i = 0; i < 16; i++) {
                this.entropies[i].set_bins(256);
                this.entropies[i].set_bin_range(0.0, 4.0);
            }
        }
    }
    
    void set_ts_threshold() {
        //TODO
    }
    
    /*
     * The numpts value should be tuned to the total we have encountered so far.
     */
    void set_to_monitor() {
        double Twin_range, Twin_offset;
    
        this.buffer.clear();
        
        if (this.imt_modeling) {
            this.imts.dbscan_cluster(globals.dbscan_win_size_ratio, 
                                     globals.dbscan_pts_ratio);
            
            /* 
             * For the total time window add a percentage (specified by twin_threshold)
             * of the total window range MIN and MAX values and use those values as the
             * absolute range of allowable values.
             */
            
            Twin_range = this.Tmax - this.Tmin;
            Twin_offset = Twin_range * globals.twin_threshold;
            
            this.Tmax += Twin_offset;
            this.Tmin -= Twin_offset;
            
        }
        
        if (this.entropy_modeling) {
            for(int i = 0; i < 16; i++) {
                writefln("Entropy values before clustering");
                writefln( this.entropy_report() );
                writefln("Calculating Entropy Clusters for Msg %d: window %d", this.canid, i);
                //For entropy is seems a wider window is needed as the relatively small
                //number of bins typically results in a window of size 1.
                this.entropies[i].dbscan_cluster(globals.dbscan_win_size_ratio*4,
                                                 globals.dbscan_pts_ratio);
            }
        }
    }
    
    void anomalous_imts(double imt, double Twin, ref messageReport mr) {
        static int anom_score = 0;
        static int anom_free_count = 0;
        static uint win_anomalies = 0;
        static uint count = 0;
        
        Nullable!bool evicted_imt;
        
        //Anomalous IMT
        if (!this.imts.in_interval(imt, globals.k)) {
            anom_free_count = 0;
            anom_score++;
            win_anomalies++;
            this.anomalous_imts_count++;
            mr.imt_anomalous = true;
            evicted_imt = imt_anom_buffer.insert(true);
            if (globals.verbose) {
                writefln("Anomalous imt %f @ %d: anom_score = %d  win_anoms = %d", 
                        imt, count, anom_score, win_anomalies);
            }
        } else {
            anom_free_count++;
            
            if (anom_score > 0 && (anom_free_count % globals.anom_backoff_rate == 0)) {
                anom_score--;
            }
            evicted_imt = imt_anom_buffer.insert(false);
        }
        
        if (!evicted_imt.isNull && evicted_imt.get == true) {
            if (win_anomalies > 0) win_anomalies--;
        }
        
        if (anom_score > globals.running_anomaly_threshold) {
            mr.score_alert = true;
            anom_score = 0;
            this.imt_alerts++;
        }
        
        if (win_anomalies > globals.win_anomaly_threshold) {
            //writefln("Window anomaly threshold exceeded (%d).", win_anomalies);
            win_anomalies = 0;
            mr.window_count_alert = true;
            this.imt_alerts++;
        }
        
        if (Twin < this.Tmin || Twin > this.Tmax) {
            mr.total_time_alert = true;
            this.twin_anomalies++;
        }
        
        mr.score_val = anom_score;
        mr.wincount_val = win_anomalies;
        mr.total_time_val = Twin;
        
        count++;
    }
    
    entropyAlertInfo anomalous_entropies(float[] H) {
        entropyAlertInfo ainfo;
        
        ainfo.entropies = H.dup;
        
        for (ulong i = 0; i < 16; i++) {
            if (this.entropies[i].is_constant) 
            { 
                if (!std.math.approxEqual(H[i], this.entropies[i].min)) {
                    ainfo.win_scores[i] = 2;
                    ainfo.total_score += 2;
                    writefln("Incrementing alert level (CONSTANT) on word %d: %f (%f excpected).", 
                                i, H[i], this.entropies[i].min);
                }
                
                continue;
            }
            
            if (!this.entropies[i].in_interval(H[i], globals.k)) {
                writefln("Incrementing alert level (VARIABLE) on word %d.", i);
                ainfo.win_scores[i] = 1;
                ainfo.total_score += 1;
            }
        }
        
        return ainfo;
    }
    
    string entropy_report() {
        float delta;
        
        string str = format("Min\t\tStd-k\t\tVal\t\tStd+K\tMax\n");
        
        for (int i = 0; i < 16; i++) {
            delta = globals.hk * this.entropies[i].stdev;
            str ~= format("%.6f\t%.6f\t%.6f\t%.6f\t%.6f\n",
                            this.entropies[i].minimum,
                            this.entropies[i].mean - delta,
                            this.entropies[i].mean,
                            this.entropies[i].mean + delta,
                            this.entropies[i].maximum );
        }
        
        return str;
    }
    
    void train_message(can_msg cm) {
        static bool filling = true;
        double Twin;
        double imt;
        
        uint count = 0;
        
        this.buffer.insert(cm);
        
        if (!buffer.atCapacity()) {
            return;
        } else if (filling) {
            writeln("Calculating initial training window.");
            filling = false;
            
            if (this.imt_modeling) {
                for (uint i = 1; i < windowSize; i++) {
                    imt = this.buffer.at(i).ts - this.buffer.at(i-1).ts;
                    this.imts.add_obs(imt);
                }
            
                Twin = this.buffer.newest().ts - this.buffer.oldest().ts;
                this.Tmax = Twin;
                this.Tmin = Twin;
            
                writefln("Initial Twin = %f", Twin);
            
                if (this.entropy_modeling) {
                    writeln("H = ", calc_entropy(this.buffer));
                }
                return;
            }
        }
 
        if (this.imt_modeling) {
            Twin = this.buffer.newest().ts - this.buffer.oldest().ts;
            //This could possibly be moved inside Stats_aggregator ?
            if (Twin > this.Tmax) this.Tmax = Twin;
            if (Twin < this.Tmin) this.Tmin = Twin;
            
            imt = this.buffer.newest().ts - this.buffer.at(windowSize-2).ts;
        
            imts.add_obs(imt);
        }
        
        
        if (this.entropy_modeling && (this.buffer.cnt % windowSize == 0))
        {
            /*
             * Entropies are calculated each time the buffer contains
             * completely new data.
             */
            float[] entropies = calc_entropy(this.buffer).dup;
            
            if (globals.verbose) {
                writef("H @ %d = ", this.buffer.cnt);
                writeln(entropies);
            }

            if (globals.hreport.isOpen()) {
                globals.hreport.writeln(this.entropy_report());
            }
            

            for (uint i = 0; i < 16; i++) {
                this.entropies[i].add_obs( entropies[i] );
            }

            this.window_count++;
        }
    }
    
    /* We don't start monitoring until the buffer fills. */
    messageReport monitor_message(can_msg cm, uint line) {
        static bool filling = true;
        double Twin;
        double imt;
        double curr_ts;
        
        messageReport msg_report; 
        
        this.buffer.insert(cm);
        
        if (!buffer.atCapacity()) {
            msg_report.imt = 0.0;
            return msg_report;
        } else if (filling) {
            if (this.imt_modeling) {
                for (uint i = 1; i < windowSize; i++) {
                    imt = this.buffer.at(i).ts - this.buffer.at(i-1).ts;
                    this.imts.add_obs(to!double(imt));
                }
            
                Twin = this.buffer.newest().ts - this.buffer.oldest().ts;
            
                writefln("Initial Twin = %f", Twin);
            
                filling = false;
            
                if (this.entropy_modeling) {
                    writeln("H = ", calc_entropy(this.buffer));
                }
                return msg_report;
            }
        }
        
        if (this.imt_modeling) {
            curr_ts = this.buffer.newest().ts;
        
            Twin = curr_ts - this.buffer.oldest().ts;            
            imt = curr_ts - this.buffer.at(windowSize-2).ts;
            
            msg_report.imt = imt;
        
            anomalous_imts(imt, Twin, msg_report);
        }
                
        if (this.entropy_modeling && (this.buffer.cnt % windowSize == 0)) {
            float[] H = calc_entropy(this.buffer).dup;
            
            msg_report.entropy_info = anomalous_entropies(H);
            if (msg_report.entropy_info.total_score > 1) {
                writefln("Entropy alert raised (%d).\n", line);
                msg_report.entropy = EntropyAlert.alert;
            } else {
                msg_report.entropy = EntropyAlert.ok;
            }
        } else {
            msg_report.entropy = EntropyAlert.skipped;
        }
 
        return msg_report;
    }
    
    void print_summary() {
        writefln("ID(%d) : %d msgs, Tmax = %f, Tmin = %f,  IMT = %f (%f) [%f - %f]", 
                this.canid, this.buffer.cnt, this.Tmax, this.Tmin, this.imts.mean, 
                this.imts.stdev, this.imts.minimum, this.imts.maximum);
        
        writeln("Entropies: [");
        foreach(e; this.entropies[] ) {
            writefln("\t%f:(%f) [%f-%f]", e.mean, e.stdev, e.minimum, e.maximum);
        }
        writeln("]");
        
        writefln("IMT alerts %d", this.imt_alerts);
        writefln("Entropy alerts %d [%d windows].", this.entropy_alerts, this.window_count);
    }
}

CanIdInfo[ushort] train_models( string tfile, bool model_imt, bool model_entropy, 
                                string log_file=null)
{
    CanIdInfo[ushort] model;
    can_msg next_msg;
    uint count = 0;
    ushort canid = ushort.max;
    
    auto file = File(tfile); // Open for reading
    foreach(line; file.byLine() ) {
        count++;
        next_msg = parse_can_message(line);
        
        if (canid != ushort.max && next_msg.canid != canid) {
            continue;
        }
        
        if (!has_key(next_msg.canid, model)) { 
            model[next_msg.canid] = CanIdInfo(next_msg.canid, model_imt, 
                                                model_entropy);
        }
        
        model[next_msg.canid].train_message(next_msg);
    }
    
    writefln("Training completed on %d lines.", count);
    return model;
}

void finalize_models(CanIdInfo[ushort] models) 
{
    foreach(ref m; models) {
        m.set_to_monitor();
    }
}

void run_monitoring(string mfile, CanIdInfo[ushort] model, string rfile, string log_file) 
{
    import std.path;

    can_msg next_msg;
    uint lcount = 0;
    ushort canid = ushort.max;
    
    string resultFile = baseName(stripExtension(mfile)) ~ ".dad";
    
    writefln("Opening file for monitoring %s\n", mfile);
    auto infile = File(mfile);
    auto repfile = File(rfile, "w");
    auto logfile = File(log_file, "w");
    
    scope(exit) {
        repfile.close();
        logfile.close();
    }
    
    //repfile.writeln("Msg,Time,IMT,AnomScore,WinCount,TimeWindow,Entropy");
    
    foreach(line; infile.byLine() ) {
        next_msg = parse_can_message(line);
        
        if (!has_key(next_msg.canid, model)) {
            writefln("Alert: Invalid canid detected. Possible DoS attack. L%d",
                    lcount);
            repfile.writeln("%f,%d,Out-of-Range,-,-,-", next_msg.ts, next_msg.canid);
            continue;
        }
        
        //CanIdInfo canid_model = model[next_msg.canid];
        messageReport mr = model[next_msg.canid].monitor_message(next_msg, lcount);
        
        repfile.writefln("%f,%d,%f,%s,%s,%d,%s,%d,%s,%f,%s",
                        next_msg.ts,
                        next_msg.canid,
                        mr.imt,
                        mr.imt_anomalous ? "Anom": "OK",
                        mr.score_alert ? "Alert": "OK",
                        mr.score_val,
                        mr.window_count_alert ? "Alert": "OK",
                        mr.wincount_val,
                        mr.total_time_alert ? "Alert": "OK",
                        mr.total_time_val,
                        EntropyAlertAsString(mr.entropy));
       
       if (mr.entropy == EntropyAlert.alert) {
            logfile.writefln("Entropy Alert triggered at line %d.", lcount);
            logfile.writeln("Trained Entropies");
            logfile.writeln(model[next_msg.canid].entropy_report());
            logfile.writefln("Window Entropies (Total Alert Level %d", 
                            mr.entropy_info.total_score);
            for (uint i = 0; i < 16; i++) {
                logfile.writefln("%f\t%d", mr.entropy_info.entropies[i], 
                                mr.entropy_info.win_scores[i]);
            }
       }
                        
       lcount++;
    }
}

void set_twin_threshold(string val) {
    globals.twin_threshold = to!double(val);
}

int main(string[] args)
{
    import std.path;

    uint tot_count = 0;
    string training_file = null;
    string results_file = null;
    string hreport_file = null;
    string monitoring_file = null;
    string param_file = null;
    string report_file = null;
    string log_file = null;
    string test_name = null;
    bool use_entropy = false;
    bool use_imt = false;
    bool logging_on = true;
    ushort canid;

    CanIdInfo[ushort] model;
    
    string param_list = std.array.join(args, " ");
    
    auto help_info =  getopt(args,  
            std.getopt.config.caseSensitive,
            "verbose|v", "Verbose output.", &globals.verbose, 
            "kvalimt|k", "K value for IMT alerts.", &globals.k, 
            "entropy|e", "Use entropy anomaly detection [False].", &use_entropy, 
            "imt|i", "Use IMT anomaly detection [False].", &use_imt,
            "canid|c", "Filter on this can id.", &canid,
            "train|t", "Training file.", &training_file,
            "name|n", "Test name.", &test_name,
            "input|m", "File to monitor.", &monitoring_file,
            "log|l", "Generate LOG file.", &logging_on,
            "backoff|B", "Anomaly backoff rate (IMT) [5]", 
                    &globals.anom_backoff_rate,
            "RScore|R", "Running anomaly score threshold (IMT) [8]", 
                    &globals.running_anomaly_threshold,
            "window_t|W", "Window threshold (IMT) [10]", 
                    &globals.win_anomaly_threshold,
            "CumTime|C", "Cumulative time window (IMT) [0.15]", 
                    &globals.twin_threshold,
            "DWin|D", "DBSCAN window size ratio [0.0075]", 
                    &globals.dbscan_win_size_ratio,
            "Dpts|P", "DBSCAN pts per window ratio [0.01]",
                    &globals.dbscan_pts_ratio,
            "report|r", "Entropy report file name.", &hreport_file);
            
    if (hreport_file != null) {
        globals.hreport = File(hreport_file, "w");
    }
    
    if (training_file == null) {
        writeln("Training file required.");
        return 0;
    }
    
    if (monitoring_file == null) {
        writeln("Monitoring file required.");
        return 0;
    }
    
    if (test_name != null)
    {
        report_file = baseName(stripExtension(monitoring_file)) ~ 
                            "." ~ test_name ~ ".dad";
        param_file = baseName(stripExtension(monitoring_file)) ~ 
                            "." ~ test_name ~ ".adp";
        log_file = baseName(stripExtension(monitoring_file)) ~
                            "." ~ test_name ~ ".dad-log";
                            
        writefln("Report file %s\nParam file %s\nLog file%s",
                report_file, param_file, log_file);
    }
        
    if (param_file != null) {
        std.file.write(param_file, param_list);
    }
    
    if (logging_on) {
        if (exists(log_file)) {
            remove(log_file);
        }
    }
    
    
    
    model = train_models(training_file, use_imt, use_entropy, log_file);
    
    finalize_models(model);
    
    if (!monitoring_file) {
        writeln("Monitoring skipped, no monitor file supplied.");
    } else {
        run_monitoring(monitoring_file, model, report_file, log_file);
    }
    
    foreach(m; model) {
        writefln("CANID %d IMT anomalies %d.", m.canid, m.anomalous_imts_count);
    }
    
    return 0;
} 
