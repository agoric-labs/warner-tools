import sys, json

# Given a slogfile on stdin (with deliver / deliver-result / heap-snapshot-load
# / heap-snapshot-save lines) for a single vatID, emit a TSV table of [time,
# elapsed] for all the span-rollover heap snapshot work (from deliver-result to
# heap-snapshot-save)

vatID = None

deliver_result_time = None
heap_snapshot_load_time = None

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
        vd = data["vd"]
        if vd[0] == "bringOutYourDead":
            start = when
    if type == 'deliver-result':
        deliver_result_time = when
    if type == 'heap-snapshot-load':
        heap_snapshot_load_time = when
    if type == 'heap-snapshot-save':
        if deliver_result_time is not None and heap_snapshot_load_time is not None:
            elapsed = when - deliver_result_time
            print("%d\t%f" % (start, elapsed))
            deliver_result_time = None
            heap_snapshot_load_time = None
