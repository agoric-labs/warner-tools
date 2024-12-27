# Follower Tools

I ran a mainnet follower continuously from the Vaults launch (aka "the
bulldozer event") in June 2023. It ran on a 2023-era Intel NUC named
`agreeable`, with an SSD for the backing store.

It was configured to retain all transcripts until 31-oct-2024, when it
was reconfigured to offload old transcript spans to files. At that time
it also changed to set `iavl-disable-fastnode=true` to disable the
not-so-useful IAVL cache which was burning through the SSD pretty badly.

About every 5-7 days I shut down the follower, made a copy of the
database/slogs/stdout, and performed some analysis of the results. Then
I rebooted the machine and restarted the node. I also shut it down for
every chain-halting software upgrade. As of late december 2024, the
machine had about 60 of these "runs", named "run-01", "run-02", etc.

The full data is uploaded to an Agoric google-cloud directory, look for
"Engineering > Slogs and DB snapshots > warner-follower-agreeable". That
directory also has a spreadsheet named "agreeable run notes" with a
table of information about each run.

This directory contains the analysis tools which I ran against those
database copies.

* `process.sh` this drives the analysis process, which takes long enough
  that I ran it in the background. Note that it did not like losing a
  controlling tty (as happens when I logged out of that shell, at least
  on macOS), so I tended to run it like:
  `../process.sh 48 </dev/null >process.out 2>&1 &`.
  The script needs to know the run number to make the right output
  filenames. It starts from a compressed database, unpacks it into a
  temporary file, runs the other tools against that copy, then cleans up
  at the end. Some of the results are saved to files, some are only
  emitted by the stdout of process.sh.

* `size-report.py`: this measures coarse information about the database:
  number of transcript spans and entries, total bytes consumed by
  transcript data, and similar numbers for the kvStore, bundleStore, and
  snapStore. I used this to estimate how much of the database (and the
  growth rate over time) was due to the different components. It
  generated `size-full.json` with the counts for the full DB, and
  `size-pruned.json` for the pruned DB (see next item).

* `prune-transcripts.js` (and -2 and -3): before run-61, my follower's
  database contained complete transcripts since the Vaults launch in its
  `transcriptStore` table. This resulted in a swingstore.sqlite DB file
  (for run-60) of about 436GB (which lz4 could compress down to 47GB),
  which is awfully hard to work with. Most of my analysis did not need
  the full transcript, so as part of the processing step, I ran this
  script to make a pruned copy of the DB, by deleting all the transcript
  items from "historical spans". The pruned DB for run-60 was only 14GB
  (compressed to 2.9GB), and took up to ten hours to execute. The -2 and
  -3 variants were faster versions, which worked by creating a new DB
  and only copying over the subset of data that we really needed. For
  run-61 I used `prune-transcripts-3.js` to make a new pruned DB, and
  moved it into place. That run also started with a swingstore
  configuration which offloaded old spans to new files,
  `[swingset] vat-transcript-retention = "operational"`, plus
  `vat-transcript-archive-dir=`, and these offloaded files were archived
  into `old-transcripts.tar.gz`), so pruning became unnecessary. Runs
  after that point do not include the full DB.

* `categorize-kvstore.js`: this examines the Vatstore (`vNN.vs.*` keys)
  for every vat and creates a JSON report named `kvdata.json`, which
  describes every virtual/durable Kind and Collection in the vat. The
  data records how many instances of each are present, their metadata
  (stateShape or keyShape/valueShape, tag, a sample instance), as well
  as how many are referenced strongly or weakly, and how many are
  exported.

* `extract-clist-db.js`: this examines all the vat c-list entries
  (`vNN.c.*` keys), and builds a new SQLite DB named
  `clist.sqlite`. This DB records the c-list entries in a concise table,
  with columns like vatID/vref/kref, plus data about whether the entry
  is an export or import, and reachable or merely-recognizable. With
  this table, simple SQL `JOIN` statements can answer questions like how
  many v68 exports are being imported by v7, or how many promises are
  being referenced by v9.

* `do-clist.py`: this tool used both `kvdata.json` and `clist.sqlite` to
  measure the scale of the problem of bugs #8400 and #8401. One bug
  involves leftover QuotePayment objects in the price-feed vats, so the
  tool reports the count of the particular durable Kind within the five
  price-feed vats. The other bug involves uncollectable reference cycles
  between v9-zoe and other vats, so the tool reports the size of one
  particular durable collection that participates in that cycle. The
  output is recorded in process.out, and I updated a spreadsheet with
  the counts, so we could see how fast the problem was growing. Note
  that upgrade-17 fixed v9-zoe to break the cycles when Seats are
  exited, and upgrade-18 will install new price feeds that don't retain
  QuotePayments in a RecoverySet, so these counts are not as interesting
  to track as they once were.

* `all-kv.txt.gz`: the processing tool also dumped the entire kvStore
  table with a simple SQLite command. The result is ambiguous
  (/usr/bin/sqlite3 defaults to a pipe separator, but some of our keys
  have pipe characters too), but still plenty useful for the
  grep/jq-based analysis I would do. And the compressed kvStore was much
  smaller and easier to work with than even the pruned DB file.

* `vat-map-from-swingstore.js`: this takes the DB and extracts whatever
  information it can about every vat. It gets data like the `critical`
  flag, the incarnation number, the IDs of the lockdown and supervisor
  (liveslots) bundles used by the vat, the vat source bundleID (which is
  some version of ZCF for all contract vats), the contract bundle ID
  (for contract vats), etc. Adding `--as-json` to the end results in a
  JSON-formatted report, rather than a human-readable text report.

* `vat-map-delta.js`: this takes a pair of JSON-formatted vat maps, and
  reports on the significant differences between them. I ran this
  manually to see which vats had been upgraded, and to confirm they were
  using the expected bundleIDs.

* `monitor-slog-block-time.js`: this is a modified copy of the script
  that lives in packages/SwingSet/misc-tools/ , which I run on my
  follower. The uploaded data includes a `monitor-run-NN.out.gz` file
  with its output. It records one line per block with a summary of
  timing and how much work was done. The output also includes a count of
  signatures (useful to gauge how many followers were unable to keep up)
  and an identifier of the block proposer.

* `extract-non-empty-blocks.py`: given a slogfile, write out separate
  per-block files for all non-empty blocks


The `agd-monitor/` directory contains a daemon which periodically
measures the size of the follower's data (swingstore DB, cosmos DBs) and
records the result in a SQLite database. The daemon also exposes the
recent values over HTTP, to a set of munin plugins which can then graph
the sizes over time. I had problems with DB load once the swingstore got
too large, so I disabled some of the measurements, however with proper
use of a readonly DB connection it should be possible to perform these
measurements without disrupting normal follower activities.

