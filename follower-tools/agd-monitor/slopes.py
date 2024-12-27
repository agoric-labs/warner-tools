import sqlite3
import statistics

db = sqlite3.connect("monitor.sqlite")

def abbreviate_space(s):
    """
    Given size in bytes summarize as English by returning unicode string.
    """
    if s is None:
        return "unknown"
    U = 1000.0
    isuffix = "B"
    def r(count, suffix):
        return "%.2f %s%s" % (count, suffix, isuffix)

    if s < 1024: # 1000-1023 get emitted as bytes, even in SI mode
        return "%d B" % s
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

def get(name):
    current = db.execute("SELECT value FROM data WHERE name=? ORDER BY time DESC LIMIT 1", (name,)).fetchone()[0]
    rows = db.execute("SELECT time, value FROM data WHERE name=? AND interval=?", (name, 0)).fetchall()
    times = [time for time,value in rows]
    values = [value for time,value in rows]
    rate_per_second, intercept = statistics.linear_regression(times, values)
    rate_per_week = rate_per_second * 60 * 60 * 24 * 7
    return current, rate_per_second, rate_per_week

name = "swingset_total"
current, rate_per_second, rate_per_week = get(name)
print(name, "current", abbreviate_space(current))
print(name, "rate", "%s/week  (%s/s)" % (abbreviate_space(rate_per_week), abbreviate_space(rate_per_second)))



