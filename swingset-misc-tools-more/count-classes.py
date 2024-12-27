
# First, use a commany like this to create a directory of
# classes/${class}.jsonl summary files:
#
# cat runs-5* | jq -r '.class' |sort |uniq >classes.txt
# for c in `cat classes.txt`; do echo $c; cat runs-5*.jsonl |jq -c "select(.class==\"${c}\")" >classes/${c}.jsonl; done
#
# Then point this tool at that directory, and it will emit a summary table

import os, sys, json, statistics

path = sys.argv[1]

classes = {}

def stats(data):
    q = statistics.quantiles(data, n=100)
    s = {
        "min": min(data),
        "max": max(data),
        "mean": statistics.mean(data),
        "p10": q[10-1],
        "p50": q[50-1],
        "p90": q[90-1],
        }
    return s

for fn in os.listdir(path):
    assert fn.endswith(".jsonl")
    name = fn[:-len(".jsonl")]
    count = 0
    total_elapsed = []
    total_computrons = []
    normal_elapsed = []
    normal_computrons = []
    for row in open(os.path.join(path, fn),"r"):
        d = json.loads(row.strip())
        count += 1
        total_elapsed.append(d["total"]["elapsed"])
        total_computrons.append(d["total"]["computrons"])
        normal_elapsed.append(d["normal"]["elapsed"])
        normal_computrons.append(d["normal"]["computrons"])
    classes[name] = {
        "count": count,
        "total": { "elapsed": stats(total_elapsed), "computrons": stats(total_computrons) },
        "normal": { "elapsed": stats(normal_elapsed), "computrons": stats(normal_computrons) },
        }

namelen = max(len(name) for name in classes.keys())

def show(kind):
    title_fmt = "| %%%ds | %%6s | %%6s | %%6s | %%6s | %%6s |" % namelen
    title = title_fmt % ("type", "count", "mean", "10pct", "median", "90pct")
    print(title)
    print("-" * len(title))

    fmt = "| %%%ds | %%6d | %%6s | %%6s | %%6s | %%6s |" % namelen
    for name in sorted(classes.keys(), key=lambda name: classes[name][kind]["elapsed"]["p50"], reverse=True):
        c = classes[name]
        t_e = c[kind]["elapsed"]
        print(fmt % (name, c["count"], "%.3f" % t_e["mean"], "%.3f" % t_e["p10"], "%.3f" % t_e["p50"], "%.3f" % t_e["p90"]))
    print()

    title_fmt = "| {:>%ds} | {:>7s} | {:>13s} | {:>13s} | {:>13s} | {:>13s} |" % namelen
    title = title_fmt.format("type", "count", "mean", "10pct", "median", "90pct")
    print(title)
    print("-" * len(title))
    fmt = "| {:%ds} | {:7,d} | {:13,d} | {:13,d} | {:13,d} | {:13,d} |" % namelen
    for name in sorted(classes.keys(), key=lambda name: classes[name][kind]["computrons"]["p50"], reverse=True):
        c = classes[name]
        t_c = c[kind]["computrons"]
        print(fmt.format(name, c["count"], int(t_c["mean"]), int(t_c["p10"]), int(t_c["p50"]), int(t_c["p90"])))
    print()


print("total execution (including BOYD, GC, replay, snapshot load/store)")
show("total")
print()
print("normal execution (excluding BOYD, GC, replay, snapshot load/store)")
show("normal")
