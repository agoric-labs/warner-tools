import sys, json

print("{:25s}  {:<12s}   {:<6s}    {:s}".format("classification", "computrons", "time", "runs"))

for line in sys.stdin.readlines():
    d = json.loads(line)
    # { classification, runids, computrons, elapsed }
    print("{:25s}  {:>12,}   {:>6.2f}    {:s}".format(d["classification"], d["computrons"], d["elapsed"], ",".join(d["runids"])))
