import sys

data = []
for line in sys.stdin.readlines():
    r = line.strip().split(",")
    data.append([r[0], r[1], int(r[2]), float(r[3])])

data2 = []
cur = None # or [classification, runIDs, total_computrons, total_elapsed

for d in data:
    if d[0].endswith("-continuation"):
        assert cur
        assert d[0] == cur[0] + "-continuation", (cur, d)
        cur[1].append(d[1])
        cur[2] += d[2]
        cur[3] += d[3]
    else:
        if cur:
            data2.append(cur)
            cur = None
        cur = [d[0], [d[1]], d[2], d[3]]
if cur:
    data2.append(cur)

for d in data2:
    if d[3] < 5:
        continue
    print("{:25s}  {:>12,}   {:>6.2f}    {:s}".format(d[0], d[2], d[3], ",".join(d[1])))
