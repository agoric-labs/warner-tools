import os, sys, subprocess, json, time
import sqlite3
import tempfile
import statistics
from twisted.python import log
from twisted.internet import reactor, defer
from twisted.internet.endpoints import serverFromString
from twisted.internet.utils import getProcessOutput
from twisted.application.service import Application
from twisted.application.internet import StreamServerEndpointService, TimerService
from twisted.web.resource import Resource
from twisted.web import server, static

application = Application("agd-monitor")

# Twisted, threads, and sqlite3 apparently don't play well together. If I open
# the DB at the top level and keep using the same connection everywhere
# (including functions spawned by TimerService), some data just vanishes. Using
# a separate connection for each (synchronous) context seems to work ok.

class DB:
    def __init__(self):
        self.db = sqlite3.connect("monitor.sqlite")
        self.db.execute('PRAGMA journal_mode=WAL');
        self.db.execute('PRAGMA synchronous=FULL');
        # we leave .isolation_level alone, which gets us "", which does a
        # CREATE TRANSACTION DEFERRED on each statement that needs it, at least
        # under python-3.10
    def execute(self, *args):
        return self.db.execute(*args)
    def commit(self):
        self.db.commit()

def create():
    db = DB()
    db.execute("CREATE TABLE IF NOT EXISTS data (name STRING, time NUMBER, interval NUMBER, value NUMBER)")
    # querying the latest wants (name, time)
    # calculating slope wants (name, time)
    # deleting old wants (time, interval), but there are only three intervals
    db.execute("CREATE INDEX IF NOT EXISTS data_name_time ON data (name, time)");
    db.execute("CREATE INDEX IF NOT EXISTS data_time ON data (name,time)");
    db.commit()
create()

MINUTE = 60
HOUR = 60*MINUTE
DAY = 24*HOUR
WEEK = 7*DAY

SHORT = 0 # sample 1/5min or 1/10min, retain for two days
SAMPLE_SHORT_FAST = 5*MINUTE - 3 # some offset to reduce resonance
SAMPLE_SHORT_SLOW = 60*MINUTE - 4
RETAIN_SHORT = 2*DAY

MEDIUM = 1 # sample 1/hour, retain for two weeks
PROMOTE_MEDIUM = 1*HOUR
RETAIN_MEDIUM = 2*WEEK

LONG = 2 # sample 1/day, retain forever
PROMOTE_LONG = 1*DAY

PRUNE_INTERVAL = 1*DAY + 2

names = [
    "total",
    "cosmos_total",
    "cosmos_application",
    "cosmos_blockstore",
    "cosmos_cs",
    "cosmos_evidence",
    "cosmos_snapshots",
    "cosmos_state",
    "cosmos_tx_index",
    "swingset_total",
    "swingset_bundle_count",
    "swingset_bundle_size",
    "swingset_flightrecorder_size",
    "swingset_kvstore_count",
    "swingset_kvstore_size",
    "swingset_slogfile",
    "swingset_snapshot_count",
    "swingset_snapshot_size",
    "swingset_transcript_count",
    "swingset_transcript_span_count",
    "swingset_transcript_size",
    "swingset_koid_count", # local.kernelStats kernelObjects
    "swingset_kpid_count", # local.kernelStats kernelPromises
    "swingset_clist_count", # local.kernelStats clistEntries
    "swingset_dispatches", # local.kernelStats dispatches
    "swingset_syscalls", # local.kernelStats syscalls
    "swingset_vats", # local.kernelStats vats
    ]

def add_data(db, name, value):
    interval = SHORT
    db.execute("INSERT INTO data VALUES (?,?,?,?)", (name, time.time(), interval, value))

def get_latest(db, name):
    now = time.time()
    recent = now - 2*HOUR
    cur = db.execute("SELECT value,time FROM data WHERE name=? ORDER BY time DESC LIMIT 1", (name,))
    row = cur.fetchone()
    if row:
        value,tim = row
        if tim < recent:
            return None
        return value
    return None

def prune_interval(db, cutoff, interval):
    db.execute("DELETE FROM data WHERE time < ? AND interval <= ?", (cutoff, interval))

def prune_all():
    log.msg("prune_all")
    now = time.time()
    db = DB()
    before = db.execute("SELECT COUNT(*) FROM data").fetchone()[0]
    #monitorcur.execute("BEGIN TRANSACTION")
    prune_interval(db, now - RETAIN_SHORT, SHORT)
    prune_interval(db, now - RETAIN_MEDIUM, MEDIUM)
    # LONG is retained forever
    after = db.execute("SELECT COUNT(*) FROM data").fetchone()[0]
    db.commit()
    log.msg(" deleted %d rows (%d->%d)" % (before-after, before, after))

def promote_to_interval(interval):
    log.msg("promote_to_interval", interval)
    db = DB()
    for name in names:
        db.execute("UPDATE data"
                   " SET interval = ?"
                   " WHERE name = ?"
                   "   AND interval < ?" # don't accidentally demote latest entry
                   " ORDER BY time DESC LIMIT 1",
                   (interval, name, interval))
    db.commit()

ssdbpath = os.path.expanduser("~/.agoric/data/agoric/swingstore.sqlite")
#ssdbpath = "./ss.sqlite";
assert os.path.isfile(ssdbpath)

SNAPSHOTS = "SELECT sum(compressedSize) FROM snapshots WHERE compressedSnapshot is not null"
NUM_SNAPSHOTS = "SELECT count(compressedSize) FROM snapshots WHERE compressedSnapshot is not null"
KVSTORE = "SELECT sum(length(key)+length(value)) FROM kvStore"
NUM_KVSTORE = "SELECT count(*) FROM kvStore"
BUNDLES = "SELECT sum(length(bundle)) FROM bundles"
NUM_BUNDLES = "SELECT count(bundle) FROM bundles"
TRANSCRIPTS = "SELECT sum(length(item)) FROM transcriptItems"
NUM_TRANSCRIPTS = "SELECT count(*) FROM transcriptItems"
NUM_TRANSCRIPT_SPANS = "SELECT count(*) FROM transcriptSpans"
LOCAL_STATS = 'SELECT value FROM kvStore WHERE key="local.kernelStats"'

ssdb = sqlite3.connect(ssdbpath)
def ssdb_exec(stmt):
    return ssdb.execute(stmt).fetchone()[0]

def ssdb_spawn_and_add(name, stmt):
    d = getProcessOutput("sqlite3", [ssdbpath, stmt])
    def _done(stdout):
        db = DB()
        add_data(db, name, int(stdout))
        db.commit()
    d.addCallbacks(_done, log.err)
    return d

def du(path):
    path = os.path.expanduser(path)
    p = subprocess.Popen(["du", "--bytes", path], stdout=subprocess.PIPE)
    stdout = p.communicate()[0].strip()
    sizes = {}
    for line in stdout.splitlines():
        size, subpath = line.split(maxsplit=1)
        size = int(size)
        subpath = subpath[len(path+os.pathsep):].decode("utf-8")
        sizes[subpath] = size
    return sizes

def sizeof(path):
    path = os.path.expanduser(path)
    assert os.path.isfile(path), path
    return os.stat(path).st_size

def count(path):
    return len(os.listdir(os.path.expanduser(path)))

def sample_slow():
    log.msg("sample_slow disabled")
    return
    log.msg("starting sample_slow()")
    # this takes 62s as of oct-2023, so run it in a child process, less frequently
    d1 = ssdb_spawn_and_add("swingset_transcript_size", TRANSCRIPTS)
    #d1 = defer.succeed(0)
    # this takes 3-14s
    d2 = ssdb_spawn_and_add("swingset_kvstore_size", KVSTORE)
    d3 = defer.DeferredList([d1, d2])
    d3.addCallbacks(lambda _: log.msg("sample_slow() done and committed"), log.err)
    return d3

def sample_fast():
    log.msg("starting sample_fast() (SQL operations disabled)")
    db = DB()

    stats = json.loads(ssdb_exec(LOCAL_STATS))
    add_data(db, "swingset_koid_count", stats["kernelObjects"])
    add_data(db, "swingset_kpid_count", stats["kernelPromises"])
    add_data(db, "swingset_clist_count", stats["clistEntries"])
    add_data(db, "swingset_dispatches", stats["dispatches"])
    add_data(db, "swingset_syscalls", stats["syscalls"])
    add_data(db, "swingset_vats", stats["vats"])

    #add_data(db, "swingset_snapshot_size", ssdb_exec(SNAPSHOTS))                    #    430ms
    #add_data(db, "swingset_snapshot_count", ssdb_exec(NUM_SNAPSHOTS))               #    460ms

    #add_data(db, "swingset_kvstore_count", ssdb_exec(NUM_KVSTORE))                  #     95ms

    #add_data(db, "swingset_bundle_size", ssdb_exec(BUNDLES))                        #      3ms
    #add_data(db, "swingset_bundle_count", ssdb_exec(NUM_BUNDLES))                   #     21ms

    #add_data(db, "swingset_transcript_count", ssdb_exec(NUM_TRANSCRIPTS))           #    550ms
    #add_data(db, "swingset_transcript_span_count", ssdb_exec(NUM_TRANSCRIPT_SPANS)) #      7ms

    add_data(db, "swingset_flightrecorder_size", sizeof("~/.agoric/data/agoric/flight-recorder.bin"))

    slogfile = os.path.expanduser("~/chain.slog")
    if os.path.exists(slogfile):
        add_data(db, "swingset_slogfile", sizeof(slogfile))

    ds = du("~/.agoric/data")                           #    100ms
    add_data(db, "total", ds[""])
    add_data(db, "cosmos_total", ds[""] - ds["agoric"])
    add_data(db, "cosmos_application", ds["application.db"])
    add_data(db, "cosmos_blockstore", ds["blockstore.db"])
    add_data(db, "cosmos_cs", ds["cs.wal"])
    add_data(db, "cosmos_evidence", ds["evidence.db"])
    add_data(db, "cosmos_snapshots", ds["snapshots"])
    add_data(db, "cosmos_state", ds["state.db"])
    add_data(db, "cosmos_tx_index", ds["tx_index.db"])

    add_data(db, "swingset_total", ds["agoric"]) # vaults/mainnet1B/bulldozer
    db.commit()
    log.msg("sample_fast() done and committed")

    # launch 19-jun-2023, sample 08-oct-2023, L+16wk

    # all                   6.3GB/wk until 01-oct, 17GB/wk 01-08-oct
    #  cosmos
    #    cosmos_application 4.2GB/wk until 01-oct, 15GB/wk 01-08-oct
    #    cosmos_blockstore              7.3-8.6GB, flat/pruned sawtooth
    #    cosmos_cs (.wal)               1.1GB
    #    cosmos_evidence                265k
    #    cosmos_snapshots               2.2GB flat
    #    cosmos_state       1.32 GB/wk, 21GB on 08-oct-2023
    #    cosmos_tx_index    1.25 GB/wk, 20GB on 08-oct-2023
    #  swingset
    #    swingset_xs_snapshots + swingset_num_xs_snapshots
    #    swingset_kvstore + swingset_num_kvstore
    #    swingset_transcripts + swingset_num_transcripts + swingset_num_transcript_spans
    #    swingset_bundles + swingset_num_bundles
    #    swingset_flightrecorder
    #    swingset_overhead

def fetch_latest():
    db = DB()
    def get(name):
        return get_latest(db, name)

    transcript_size = get("swingset_transcript_size")
    kv_size = get("swingset_kvstore_size")
    bundle_size = get("swingset_bundle_size")
    snapshot_size = get("swingset_snapshot_size")
    swingset_total = get("swingset_total")
    swingset_overhead = None
    if (swingset_total and transcript_size and kv_size and bundle_size and snapshot_size):
        swingset_overhead = swingset_total - transcript_size - kv_size - bundle_size - snapshot_size

    data = {
        "total": get("total"),
        "cosmos": {
            "total": get("cosmos_total"),
            "application": get("cosmos_application"),
            "blockstore": get("cosmos_blockstore"),
            "cs": get("cosmos_cs"),
            "evidence": get("cosmos_evidence"),
            "snapshots": get("cosmos_snapshots"),
            "state": get("cosmos_state"),
            "tx_index": get("cosmos_tx_index"),
            },
        "swingset": {
            "total": swingset_total,
            "transcript": {
                "size": transcript_size,
                "spans": get("swingset_transcript_span_count"),
                "items": get("swingset_transcript_count"),
                },
            "kv": {
                "size": kv_size,
                "entries": get("swingset_kvstore_count"),
                },
            "bundle": {
                "size": bundle_size,
                "count": get("swingset_bundle_count"),
                },
            "snapshot": {
                "size": snapshot_size,
                "count": get("swingset_snapshot_count"),
                },
            "flightrecorder": get("swingset_flightrecorder_size"),
            "overhead": swingset_overhead,
            },
        "slogfile": get("swingset_slogfile"),
        "kernel_stats": {
            "koids": get("swingset_koid_count"),
            "kpids": get("swingset_kpid_count"),
            "clists": get("swingset_clist_count"),
            "dispatches": get("swingset_dispatches"),
            "syscalls": get("swingset_syscalls"),
            "vats": get("swingset_vats"),
            },
        }
    # fetch_latest() is read-only, so no db.commit()
    return data

class Fetch(Resource, object):
    def render_GET(self, req):
        req.setHeader("content-type", "text/plain")
        data = fetch_latest()
        return json.dumps(data).encode("utf-8") + b"\n"

"""
class FetchData(Resource, object):
    def __init__(self, name, db):
        super(FetchData, self).__init__()
        self.name = name
        self.db = db
    def render_GET(self, req):
        start = 0
        if b"start" in req.args:
            start_arg = req.args[b"start"][0]
            if start_arg.endswith(b"H"):
                start = time.time() - 3600 * int(start_arg[:-1])
            else:
                start = int(start_arg)
        rows = db.execute("SELECT * FROM `%s`"
                          " WHERE `when` > ?"
                          " ORDER BY `when` ASC" % self.name,
                          (start,)).fetchall()
        data = []
        for r in rows:
            d = {}
            for n in ["when", "temperature", "humidity", "pressure", "light"]:
                d[n] = r[n]
            data.append(d)
        req.setHeader("content-type", "text/plain")
        return json.dumps(data).encode("utf-8")
"""

def abbreviate_size(s, isuffix):
    if s is None:
        return "unknown"
    U = 1000.0
    def r(count, suffix):
        return "%.2f %s%s" % (count, suffix, isuffix)

    if s < 1024: # 1000-1023 get emitted as bytes, even in SI mode
        return "%d %s" % (s, isuffix)
    if s < U*U:
        return r(s/U, "k")
    if s < U*U*U:
        return r(s/(U*U), "M")
    if s < U*U*U*U:
        return r(s/(U*U*U), "G")
    if s < U*U*U*U*U:
        return r(s/(U*U*U*U), "T")
    if s < U*U*U*U*U*U:
        return r(s/(U*U*U*U*U), "P")
    return r(s/(U*U*U*U*U*U), "E")

def report_one_name(db, name, interval, cutoff):
    current = db.execute("SELECT value FROM data WHERE name=? ORDER BY time DESC LIMIT 1", (name,)).fetchone()[0]
    rows = db.execute("SELECT time, value FROM data"
                      " WHERE name = ? AND interval >= ? AND time > ?",
                      (name, interval, cutoff)).fetchall()
    times = [time for time,value in rows]
    values = [value for time,value in rows]
    rate_per_second, intercept = statistics.linear_regression(times, values)
    rate_per_week = rate_per_second * 60 * 60 * 24 * 7
    return current, rate_per_second, rate_per_week

def build_report(interval, age=None):
    cutoff = time.time() - age if age else 0
    headers = ("Name", "Current     ", "       %", "Rate / week", "       %")
    fmt = "{:<35s} {:<13s} {:>8s}     {:<11s}  {:>8s}"
    lines = []
    lines.append(fmt.format(*headers))
    lines.append(fmt.format(*("-" * len(h) for h in headers)))
    db = DB()
    reports = [(name, report_one_name(db, name, interval, cutoff)) for name in names if name != "swingset_slogfile"]
    total = reports[0][1]
    for name,report in reports:
        current, rate_per_second, rate_per_week = report
        if name.endswith("_count"):
            current_s = abbreviate_size(current, "c")
            rate_s = abbreviate_size(rate_per_week, "c")
            perc_current_s = ""
            perc_rate_s = ""
        else:
            current_s = abbreviate_size(current, "B")
            rate_s = abbreviate_size(rate_per_week, "B")
            perc_current = 100.0 * current / total[0]
            perc_current_s = "({:.1f}%)".format(perc_current)
            perc_rate = 100.0 * rate_per_second / total[1]
            perc_rate_s = "({:.1f}%)".format(perc_rate)
        prefixlen = 0
        if name != "total":
            prefixlen = 1
            if not name.endswith("total"):
                prefixlen = 2
        name_prefix = " "*prefixlen
        cur_prefix = "{:<3s}".format(">"*prefixlen)
        current_s = cur_prefix + "{:>9s}".format(current_s)
        #rate_s = cur_prefix + "{:>9s}".format(rate_s)
        rate_s = "{:>9s}".format(rate_s)
        line = fmt.format(name_prefix + name,
                          current_s,
                          perc_current_s,
                          rate_s,
                          perc_rate_s,
                         )
        lines.append(line)
    return "\n".join(lines) + "\n"

class Report(Resource, object):
    def render_GET(self, req):
        req.setHeader("content-type", "text/plain")
        desc = "Average over last day:\n"
        data = desc + build_report(SHORT, 1*DAY)
        return data.encode("utf-8")

root = Resource()
#root.putChild(b"", static.Data(b"hello\n", "text/plain"))
root.putChild(b"", Report())

root.putChild(b"data", Fetch())

s = server.Site(root)
ep = serverFromString(reactor, "tcp:30003")
StreamServerEndpointService(ep, s).setServiceParent(application)

TimerService(SAMPLE_SHORT_FAST, sample_fast).setServiceParent(application)
TimerService(SAMPLE_SHORT_SLOW, sample_slow).setServiceParent(application)

# this will immediately promote the most recent samples to LONG
TimerService(PROMOTE_MEDIUM, promote_to_interval, MEDIUM).setServiceParent(application)
TimerService(PROMOTE_LONG, promote_to_interval, LONG).setServiceParent(application)
TimerService(PRUNE_INTERVAL, prune_all).setServiceParent(application)

if __name__ == "__main__":
    print("Average over last day:")
    print(build_report(SHORT, 1*DAY))
    sys.exit(0)
    #promote_to_interval(INTERVAL_HOURLY)
    #prune_all()
    sample_fast()
    if True:
        d = sample_slow()
    else:
        d = defer.Deferred()
        reactor.callLater(0, d.callback, None)
    def done(_):
        data = fetch_latest()
        print(json.dumps(data))
        reactor.stop()
    d.addCallback(done)
    reactor.run()

