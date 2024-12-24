#!/bin/sh

# run in the background with:
#  cd run-NN
#  ../process.sh NN </dev/null >process.out 2>&1 &
#
# if you omit the </dev/null and logout , the python commands will fail in
# init_sys_streams as it tries to open the missing stdin
#
#Fatal Python error: init_sys_streams: can't initialize sys standard streams
#Python runtime state: core initialized
#OSError: [Errno 9] Bad file descriptor
#Current thread 0x00000001e8b24c00 (most recent call first):
#  <no Python frame>

# exit on any error
set -e
# error on undefined variables
set -u
# print command before execution
set -x
# exit on command pipe failure
set -o pipefail


# $@ is the run number
PRUNED_COMPRESSED=run-$@-swingstore-pruned.sqlite.lz4
PRUNED=ss.sqlite

if [ ! -f ${PRUNED_COMPRESSED} ]; then
    echo "missing run-NN-swingstore.sqlite.lz4 (${PRUNED_COMPRESSED}), bailing"
    exit 1
fi

echo "decompressing.."
date
lz4cat ${PRUNED_COMPRESSED} >${PRUNED}
date

# TODO: measure size of externalized transcript files too, starting with run-57

echo "measuring size-pruned.."
date
python3 ../size-report.py ${PRUNED} | tee size-pruned.json
date

echo "using categorize-kvstore.js to create kvdata.json.."
date
node ~/stuff/agoric/agoric-sdk/packages/SwingSet/misc-tools/categorize-kvstore.js --datafile kvdata.json ingest ${PRUNED}
date

echo "using extract-clist-db.js to create clist.sqlite.."
date
node ~/stuff/agoric/agoric-sdk/packages/SwingSet/misc-tools/extract-clist-db.js ${PRUNED} clist.sqlite
date

echo "extracting #8400/#8401 counts"
date
python3 ../do-clist.py kvdata.json clist.sqlite
date

echo "extracting whole kvStore"
date
sqlite3 ${PRUNED} 'select * from kvStore' | sort | gzip >all-kv.txt.gz
date

echo "computing vat map"
node ~/stuff/agoric/agoric-sdk/packages/SwingSet/misc-tools/vat-map-from-swingstore.js ${PRUNED} >vat-map.txt
node ~/stuff/agoric/agoric-sdk/packages/SwingSet/misc-tools/vat-map-from-swingstore.js ${PRUNED} --as-json >vat-map.json

echo "compressing kvdata.json.."
gzip kvdata.json

echo "compressing clist.sqlite.."
gzip clist.sqlite

echo "removing temporary uncompressed file"
rm ${PRUNED}

echo "Done"

