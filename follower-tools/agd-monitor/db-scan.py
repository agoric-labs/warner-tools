import os, json, re, sys
import sqlite3
from collections import defaultdict

dbpath = os.path.expanduser('~/.agoric/data/agoric/swingstore.sqlite')
#dbpath = './11-53.sqlite'

# kvstore has pairs like:
#  "v$NN.c.ko45": "R o+4"      # reachable export
#  "v$NN.c.ko46": "_ o+5"      # merely-recognizable export
#  "v$NN.c.ko47": "R o-6"      # reachable import
#  "v$NN.c.ko48": "_ o-7"      # merely-recognizable import
#  "v$NN.c.kp70": "R p+12"      # promise (always "R", sometimes "p+" sometimes "p-")


vatIDRE = re.compile('^v\d+$')

def new_stat():
    return {
        'object_exports_reachable': 0,
        'object_exports_recognizable': 0,
        'object_imports_reachable': 0,
        'object_imports_recognizable': 0,
        'promises': 0,
        'vatstore_keys': 0,
    }

def scan(dbpath):
    db = sqlite3.connect(dbpath)
    c = db.cursor()
    height = int(c.execute('SELECT value from kvStore WHERE key = "host.height"').fetchone()[0])
    vat_stats = defaultdict(new_stat)
    for (key,value) in c.execute('SELECT key,value FROM kvStore WHERE key LIKE "v%"'):
        pieces = key.split('.')
        if vatIDRE.search(pieces[0]):
            vatID = pieces[0]
            stat = vat_stats[vatID]
            if pieces[1] == 'c':
                if pieces[2].startswith('ko'):
                    reachable = value[0] == 'R'
                    is_export = value[3] == '+'
                    if is_export:
                        if reachable:
                            stat['object_exports_reachable'] += 1
                        else:
                            stat['object_exports_recognizable'] += 1
                    else:
                        if reachable:
                            stat['object_imports_reachable'] += 1
                        else:
                            stat['object_imports_recognizable'] += 1
                    #stat['objects'] += 1
                if pieces[2].startswith('kp'):
                    stat['promises'] += 1
            if pieces[1] == 'vs':
                stat['vatstore_keys'] += 1
    data = {
        'height': height,
        'vat_stats': vat_stats,
    }
    return data

if len(sys.argv) > 1:
    dbpath = sys.argv[1]
print(json.dumps(scan(dbpath)))
