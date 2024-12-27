import os, subprocess, json, time, re, sys, collections
import sqlite3

statsdbpath = './stats.sqlite';
statsdb = sqlite3.connect(statsdbpath)

all_vatIDs = set()
interesting_voids = set()
interesting_vpids = set()
interesting_vs_keys = set()
last_data = dict()

data = collections.defaultdict(dict)
for row in statsdb.execute('SELECT * FROM vatStats'):
    (vatID, block, voids, vpids, keys) = row
    data[block][vatID] = { 'voids': voids, 'vpids': vpids, 'keys': keys }
    if vatID in last_data:
        if last_data[vatID]['voids'] != voids:
            interesting_voids.add(vatID)
        if last_data[vatID]['vpids'] != vpids:
            interesting_vpids.add(vatID)
        if last_data[vatID]['keys'] != keys:
            interesting_vs_keys.add(vatID)
    last_data[vatID] = data[block][vatID]
    all_vatIDs.add(vatID)

#vatIDs = sorted(interesting_vatIDs)
interesting_voids = sorted(interesting_voids)
interesting_vpids = sorted(interesting_vpids)
interesting_vs_keys = sorted(interesting_vs_keys)

header = ['block']
for vatID in interesting_voids:
    header.append('%s voids' % vatID)
for vatID in interesting_vpids:
    header.append('%s vpids' % vatID)
for vatID in interesting_vs_keys:
    header.append('%s vs_keys' % vatID)

print(','.join(header))

for block in sorted(data.keys()):
    row = [str(block)]
    blockdata = data[block]
    for vatID in interesting_voids:
        row.append(str(blockdata[vatID]['voids']))
    for vatID in interesting_vpids:
        row.append(str(blockdata[vatID]['vpids']))
    for vatID in interesting_vs_keys:
        row.append(str(blockdata[vatID]['keys']))
    print(','.join(row))
