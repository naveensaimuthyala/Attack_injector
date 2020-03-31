import std.stdio;
import std.typecons;

struct CircularBuffer(T, int Capacity = 50) {
    uint count = 0;
    T[Capacity] data;
    
    /**
     * Insert the item t into the circular buffer.  If the insertion
     * of t results in the eviction of an element, the evicited element
     * is returned. Otherwise a NULL value is return using the Nullable 
     * structure.
     */
    Nullable!T insert(T t) {
        Nullable!T evicted;
    
        uint npos = this.count % Capacity;
        
        if (this.count >= Capacity) {
            evicted = data[npos];
        }
        data[npos] = t;
        
        count++;
        
        return evicted;
    }
    
    bool atCapacity() {
        return this.count >= Capacity;
    }
    
    void clear() {
        this.count = 0;
    }
    
    /*
     *   Total number of items added (including those discarded).
     */
    @property uint cnt() {
        return this.count;
    }
    
    @property uint length() {
        if (this.count < Capacity) return this.count;
        
        return Capacity;
    }
    
    //For now undefined if count = 0;
    T newest() {
        uint pos = (this.count-1) % Capacity;
        return data[pos];
    }
    
    T oldest() {
        if (this.count < Capacity) return data[0];
    
        uint pos = (this.count - Capacity) % Capacity;
        return data[pos];
    }
    
    //0 is oldest, N - 1 is newest.
    T at(uint pos) {
        if ( pos >= this.count || pos >= Capacity ) {
            writeln("AT out of range, you are likely getting garbage back.");
            return data[0];
        }
        
        uint spos = 0;
        
        if (this.count < Capacity) {
            spos += pos;
        } else {
            spos = (this.count - Capacity + pos) % Capacity;
        }
        
        return this.data[spos];
    }
}
