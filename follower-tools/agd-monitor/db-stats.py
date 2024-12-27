import os, subprocess, json, time, re, sys
import sqlite3
from collections import defaultdict, namedtuple

dbpath = os.path.expanduser('~/.agoric/data/agoric/swingstore.sqlite')
#dbpath = './11-53.sqlite'

statsdbpath = './stats.sqlite';
statsdb = sqlite3.connect(statsdbpath)
statsdb.execute('''
CREATE TABLE IF NOT EXISTS vatStats (
  vatID TEXT,
  blockHeight INT,
  clist_voids INT,
  clist_vpids INT,
  vatstore_keys INT,
  PRIMARY KEY (vatID, blockHeight)
  UNIQUE (vatID, blockHeight)
)
''')



def db_one(c, stmt):
    return c.execute(stmt).fetchone()[0]

GET = 'SELECT value FROM kvStore WHERE key = ?'
def get(c, key):
    return c.execute(GET, (key,)).fetchone()[0]

COUNT = 'SELECT count(key) FROM kvStore WHERE key LIKE ?'
def count(c, prefix):
    assert '%' not in prefix
    return c.execute(COUNT, (prefix + '%',)).fetchone()[0]

def all_vatIDs(c):
    vat_ids = []
    for name in json.loads(get(c, 'vat.names')):
        vat_ids.append(get(c, 'vat.name.%s' % name))
    dynamicIDs = json.loads(get(c, 'vat.dynamicIDs'))
    vat_ids.extend(dynamicIDs)
    return sorted(vat_ids)

vatIDRE = re.compile('^v\d+$')

COUNT_ONLY = True
def new_stat_count_only():
    return {
        'clist_voids': 0,
        'clist_vpids': 0,
        'vatstore_keys': 0,
    }
def new_stat_with_nexts():
    return {
        'next_void': None,
        'next_vpid': None,
        'clist_voids': 0,
        'clist_vpids': 0,
        'vatstore_keys': 0,
    }

def scan(dbpath):
    db = sqlite3.connect(dbpath)
    c = db.cursor()
    height = int(get(c, 'host.height'))
    vat_ids = all_vatIDs(c)
    vat_stats = defaultdict(new_stat_count_only if COUNT_ONLY else new_stat_with_nexts)
    for (key,) in c.execute('SELECT key FROM kvStore WHERE key LIKE "v%"'):
        pieces = key.split('.')
        if vatIDRE.search(pieces[0]):
            vatID = pieces[0]
            stat = vat_stats[vatID]
            if not COUNT_ONLY:
                if pieces[1] == 'o' and pieces[2] == 'nextID':
                    stat['next_void'] = int(get(c, key))
                if pieces[1] == 'p' and pieces[2] == 'nextID':
                    stat['next_vpid'] = int(get(c, key))
            if pieces[1] == 'c':
                if pieces[2].startswith('o'):
                    stat['clist_voids'] += 1
                if pieces[2].startswith('p'):
                    stat['clist_vpids'] += 1
            if pieces[1] == 'vs':
                stat['vatstore_keys'] += 1
    data = {
        'height': height,
        'num_vats': len(vat_ids),
        'vat_stats': vat_stats,
    }
    return data

STORE = '''
INSERT
 INTO vatStats (vatID, blockHeight, clist_voids, clist_vpids, vatstore_keys)
 VALUES (?,?,?,?,?)
 ON CONFLICT DO NOTHING
'''
def store(data):
    c = statsdb.cursor()
    for vatID in data['vat_stats']:
        stats = data['vat_stats'][vatID]
        c.execute(STORE, (vatID, data['height'], stats['clist_voids'], stats['clist_vpids'], stats['vatstore_keys']))
    statsdb.commit()
    c.close()

MINUTE = 60
cached = [None, None, None] # [dbpath, when, data]

def get_cached_or_update(dbpath):
    if cached[0] == dbpath and cached[1] and (time.time() - cached[1]) < MINUTE:
        return cached[2]
    data = scan(dbpath) # takes 2-4s
    store(data)
    cached[0] = dbpath
    cached[1] = time.time()
    cached[2] = data
    return data

if __name__ == '__main__':
    if len(sys.argv) > 1:
        dbpath = sys.argv[1]
    print(json.dumps(get_cached_or_update(dbpath)))
