#!/usr/bin/env python3

import sys, os, time
from signal import SIGTERM

pidfile = sys.argv[1]
if os.path.exists(pidfile):
    with open(pidfile) as f:
        pidstr = f.read().strip()
    pid = int(pidstr)
    os.kill(pid, 0) # is it even running?

    os.kill(pid, SIGTERM)
    while True:
        try:
            os.kill(pid, 0)
            break
        except OSError:
            pass
        time.sleep(1)
    while os.path.exists(pidfile):
        time.sleep(1)

    print("pid %s finished" % pid)
sys.exit(0)
