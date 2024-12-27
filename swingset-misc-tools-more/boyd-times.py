import sys, json, gzip, re, time
import statistics

# Given a slogfile on stdin with 'deliver' and 'deliver-result' lines for a
# single vatID, emit a TSV table of [deliveryNum, time, elapsed] for all the
# BOYD deliveries

vatID = None

start = None
elapsed = []

for line in sys.stdin:
    if isinstance(line, bytes):
        line = line.decode("utf-8")
    if not line.strip():
        continue

    data = json.loads(line.strip())
    if vatID:
        assert data["vatID"] == vatID
    else:
        vatID = data["vatID"]
    type = data["type"]
    when = data["time"]

    if type == 'deliver':
        dnum = data["deliveryNum"]
        vd = data["vd"]
        if vd[0] == "bringOutYourDead":
            start = when
    if type == 'deliver-result':
        if start is not None:
            elapsed = when - start
            print("%d\t%d\t%f" % (dnum, start, elapsed))
            start = None
