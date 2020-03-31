import std.conv;
import std.math;
import std.stdio;
import std.string;
import std.traits;
import std.typecons;

struct Cluster(T) {
    uint start;
    uint end;
    T start_val;
    T end_val;
    uint count;
    uint id;
}

struct StatBin(T) {
    uint win_size;
    uint win_pad;
    uint active_bins;
    T bin_width;
    
    bool explicit_range = false;
    T minimum = T.max;
    T maximum = -T.max;
    
    T[] buffer; /* Stores up to the initial N points. */
    uint[] bins;
        
    void set_bin_count(uint count) 
    {
        this.bins.length = count;
        for (uint b = 0; b < bins.length; ++b) 
        {
            this.bins[b] = 0;
        }
    }
    
    ulong num_bins() {
        return this.bins.length;
    }
    
    void add_point(T val) {
        this.buffer ~= val;
    }
    
    void set_range(T min, T max) {
        this.explicit_range = true;
        this.minimum = min;
        this.maximum = max;
    }
    
    /* win_size must be an odd number */
    void calc_bins(uint win_size, T minimum, T maximum)
    {
        uint bin_id;
        
        if (this.explicit_range) {
            minimum = this.minimum;
            maximum = this.maximum;
        }

        this.win_size = win_size;
        
        this.win_pad = win_size/2;
        this.active_bins = to!uint(this.bins.length) - 2*this.win_pad;
        
        writefln("Active bins = %d", this.active_bins);
        
        T delta = maximum - minimum;
        
        this.bin_width = delta / to!T( this.active_bins - 1);
        writefln("Bin width = %f", this.bin_width);
        
        /* Calculate bin counts */
        for (uint i = 0; i < this.buffer.length; i++) {
            bin_id = to!uint( floor((this.buffer[i] - minimum)/bin_width) ) + this.win_pad;
            this.bins[bin_id]++;
            
            //writefln("Updating bin %d to %d", bin_id, this.bins[bin_id]);
        }
    }
    
    /* Assumes calc_bins has already been called. */
    Cluster!T[uint] cluster(uint num_pts, T minimum, T maximum) {
        uint bins_used = 0;
        uint max_bin_count = 0;
        T bin_floor = 0.0;
        
        if (this.explicit_range) {
            minimum = this.minimum;
            maximum = this.maximum;
        }
        
        writefln("Calculating bins in range %f - %f for %d pts.",
                 minimum, maximum, num_pts);
    
        for (uint i = 0; i < this.bins.length; ++i) {
            if (this.bins[i] > 0) {
                bins_used++;
            }
            if (this.bins[i] > max_bin_count) {
                max_bin_count = this.bins[i];
            }
        }

        writef("Bin max = %d", max_bin_count);
        writefln(" Bins used = %d", bins_used);

        int base_win_count = 0;
        for(uint i = 0; i < this.win_size; ++i) {
            base_win_count += bins[i];
        }
        
        uint cluster_id = 0;
        uint prev_cluster = 0;
        
        Cluster!T[uint] clusters;
        
        for(uint i = this.win_pad; i < this.bins.length-this.win_pad; ++i) {
            if (i > this.win_pad) {
                base_win_count += (this.bins[i+this.win_pad] - 
                                    this.bins[i-this.win_pad-1]);
            }
            if (base_win_count < num_pts) {
                if (prev_cluster > 0) {
                    clusters[cluster_id].end = i - 1;
                }
                prev_cluster = 0;
            } else {
                if (prev_cluster == 0) {
                    cluster_id++;
                    Cluster!T clus;
                    clus.start = i;
                    clus.end = 0;
                    clus.id = cluster_id;
                    clusters[cluster_id] = clus;
                    prev_cluster = cluster_id;
                }
                clusters[cluster_id].count += this.bins[i];
            }
        }
        
        writefln("number of clusters = %d", cluster_id);
        float lo, hi;
        foreach(ref clus; clusters) {
            lo = minimum + ((clus.start-this.win_pad) * this.bin_width);
            hi = minimum + ((clus.end - this.win_pad + 1) * this.bin_width);
            writefln("Cluster %d:  %d - %d  [%f - %f] # %d.", clus.id, clus.start, 
                    clus.end, lo, hi, clus.count);
            clus.start_val = lo;
            clus.end_val = hi;
        }
        return clusters;
    }
}

struct StatsAggregator(T) {
    T M = 0.0;
    T SS = 0.0;
    uint count = 0;
    T min = T.max;
    T max = -T.max;
    //Stores the 'high and low' values that bound the exepcted values of this
    //stat.
    bool interval_set = false;
    bool constant = false; /* Does this represent a CONSTANT variable. */
    T valid_high = 0.0;
    T valid_low = 0.0;
    
    StatBin!T bins;
    bool use_bins = false;
    
    //If we have multiple clusters we keep this information here.
    Cluster!T[uint] clusters;
    bool multi_cluster = false;
    
    
    void set_bins(uint num_bins) {
        this.bins.set_bin_count(num_bins);
        this.use_bins = true;
    }
    
    void set_constant(T value) {
        this.constant = true;
    }
    
    @property bool is_constant() {
        return this.constant;
    }
    
    void set_bin_range(T min, T max) {
        if (!this.use_bins) {
            writeln("Error. Setting bin range without bins.");
        } else {
            this.bins.set_range(min, max);
        }
    }
    
    void add_obs(T value) {
        this.count++;
        
        T delta = value - this.M;
        
        this.M += delta / this.count;
        this.SS += delta * (value - this.M);
        
        if (value < this.min) this.min = value;
        if (value > this.max) this.max = value;
        
        if (this.use_bins) {
            this.bins.add_point(value);
        }
    }
    
    @property T mean() {
        return this.M;
    }
    
    @property T variance() {
        return this.SS/to!T((this.count-1));
    }
    
    @property T stdev() {
        import std.math;
        
        return std.math.sqrt(this.variance);
    }
    
    @property T minimum() {
        if (this.min == T.max) return this.max;
        return this.min;
    }
    
    @property T maximum() {
        return this.max;
    }
    
    bool in_interval(T value, T k) {
        if (this.multi_cluster) {
             foreach(c; this.clusters) {
                if (value >= c.start_val && value <= c.end_val) {
                    return true;
                }
            }
            return false;
        } else if (!this.interval_set) {
            T delta = k * this.stdev;
    
            T lo = this.mean - delta;
            T hi = this.mean + delta;
            
            this.valid_low = lo;
            this.valid_high = hi;
            
            this.interval_set = true;
        }
    
        return ( value >= this.valid_low && value <= this.valid_high );
    }
    
    bool dbscan_cluster(float win_size_ratio, float numpts_ratio) {
        float num_bins, total_pts;
        uint win_size;
        uint num_pts;
    
        Cluster!T[uint] cls;
        
        writefln("Baseline stats at start of clustering ...");
        writefln("X = %.6f, min = %.6f, max = %.6f", this.mean, 
                    this.minimum, this.maximum);
        
        if (this.min == this.max) {
            this.constant = true;
            writeln("Skipping clustering for constant VAR %s", to!string(this.min));
            return true;
        } else if (this.min > this.max) {
            writeln("Trying to cluster empty variable.");
            return false;
        }
    
        if (!this.use_bins) 
        {
            writeln("Clustering requires that bins must be initialized.");
            return false;
        }
        
        num_bins = to!float(this.bins.num_bins());
        num_pts = to!uint( to!float(this.count) * numpts_ratio );
        
        float pts_per_bin = to!float(total_pts)/to!float(num_bins);
        
        win_size = to!uint(num_bins*win_size_ratio);
        if (win_size % 2 == 0) win_size++; //Make sure it is odd.
        
        writefln("Running DBSCAN. Threshold is %d pts within %d bins window.",
                 num_pts, win_size);
        
        if (this.min < this.max) {
            this.bins.calc_bins(win_size, this.min, this.max);
            cls = this.bins.cluster(num_pts, this.min, this.max);
        } else {
            writefln("dbscan cluster skipped for value in range %f-%f.",
                     this.min, this.max);
            return false;
        }
        
        if (cls.length != 1) {
            writeln("WARNING: Using multi-clustered value.\n");
            this.clusters = cls;
            this.multi_cluster = true;
            
        } else {
            foreach(c; cls) {
                this.valid_low = c.start_val;
                this.valid_high = c.end_val;
            }
            this.interval_set = true;

            writefln("DSCAN Range = [%f - %f]", this.valid_low, this.valid_high);
        }
        
        return true;
    }
}
