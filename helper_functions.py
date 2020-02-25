
import contextlib
import sys, os
import subprocess












@contextlib.contextmanager
def manage_output_stream(filename=None):
    """
    Borrowed from:
    
    https://stackoverflow.com/questions/17602878/how-to-handle-both-with-open-and-sys-stdout-nicely
    """
    if filename and filename != '-':
        fh = open(filename, 'w')
    else:
        fh = sys.stdout

    try:
        yield fh
    finally:
        if fh is not sys.stdout:
            fh.close()
            




def file_len(fname):
    
    """
    This function calculates the number of lines present in inputfile that is passed to this fucntion \
    and returns the integer value of number of lines present in inp file \
    """
    
    p = subprocess.Popen(['wc', '-l', fname], stdout=subprocess.PIPE, 
                                              stderr=subprocess.PIPE)
    result, err = p.communicate()
    if p.returncode != 0:
        raise IOError(err)
    return int(result.strip().split()[0])
