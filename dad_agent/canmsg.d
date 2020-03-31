import std.algorithm;
import std.array;
import std.conv;
import std.range;
import std.stdio;
import std.string;


struct can_msg {
    double ts;
    ushort canid;
    ubyte dlc;
    ubyte[8] payload;
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
