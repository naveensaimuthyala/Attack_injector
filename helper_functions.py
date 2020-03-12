
import contextlib
import sys, os
import subprocess
import queue










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


def drain(q):
  while True:
    try:
      yield q.get_nowait()
    except queue.Empty:  # on python 2 use Queue.Empty
      break



def query_yes_no(question, default=float(0.01)):
    
    """Ask a yes/no question via input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" returns imt  value .
    """
    
    valid = {"yes": float(0.01), "y": float(0.01), "ye": float(0.01)}
    if default is None:
        prompt = " [y/n] "
    elif default == float(0.01):
        prompt = " Do you want to continue with default value imt(0.01) [y/n] : "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        
        if default is not None and choice == '':
            print( " Choosing default IMT 0.01")
            return default
        elif choice in valid:
            return valid[choice]
        
        elif choice in [ 'no', 'NO', 'n']:
            return float(input(" Please respond with IMT value:"))
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")