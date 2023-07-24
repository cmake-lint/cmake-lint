#!/usr/bin/env python3
import sys
import os
import getopt
import subprocess

(opts, filenames) = getopt.getopt(sys.argv[1:], '',
            ['help', 'filter=', 'config=', 'spaces=', 'linelength=',
                'quiet', 'version', 'diff'])
                
retcode = 0
for file in filenames:
    ret = subprocess.run(["git", "diff", "-U0", "--", "{}".format(file)], capture_output=True)
    call = ["cmakelint", "--diff"]
    for opt, val in opts:
        flag = opt
        if(val):
            flag += "="+str(val)
        call.append(flag)
    ret = subprocess.run(call, input=ret.stdout, capture_output=True)
    if(ret.returncode):
        print(ret.stdout.decode("UTF-8"))
        if(retcode == 0): 
            retcode = ret.returncode
    
exit(retcode)