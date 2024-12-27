import json, sys
from collections import deque

SLOW = 1.0
SIZE = 10
MIDDLE = SIZE // 2
log = deque([], SIZE)

for line in sys.stdin.readlines():
    data = json.loads(line)
    gap = None
    if len(log):
        gap = data["monotime"] - log[-1][1]["monotime"]
    log.append((gap, data))
    if len(log) < SIZE:
        continue
    if log[MIDDLE][0] > SLOW and log[MIDDLE][1]["type"] != "cosmic-swingset-run-start":
        for gap, row in log:
            if gap > SLOW:
                print('{"gap":%.2f}' % gap)
            print(json.dumps(row))
        print("{}\n{}\n{}")
