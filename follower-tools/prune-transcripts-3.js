import '@endo/init';
import { performance } from 'perf_hooks';
import fs from 'fs';
import sqlite3 from 'better-sqlite3';

// Given an original swingstore.sqlite, and a new (initialized but not
// populated) pruned.sqlite, populate the new DB with everything from
// the original except for the old (historical, not-current-span)
// transcript entries. This does not modify the original.
//
// before running this, create the new DB with a copy of the old schema:
//  sqlite3 orig.sqlite .schema | sqlite3 new.sqlite
//
// then invoke this tool like:
//  node prune-transcripts-3.js orig.sqlite pruned.sqlite


let [dbPath, newPath] = process.argv.slice(2);
if (!fs.existsSync(dbPath)) {
  throw Error(`dbPath '${dbPath}' must exist`);
}
if (!fs.existsSync(newPath)) {
  throw Error(`newPath '${newPath}' must exist`);
}

const ssdb = sqlite3(newPath);
ssdb.exec(`ATTACH DATABASE '${dbPath}' AS old`);

// run-59: 7m total

// copy all tables except transcriptItems
const tables = [
  'pendingExports',
  'bundles',
  'snapshots', // run-59: 31s
  'transcriptSpans', // run-59: 2s
  'kvStore', // run-59: 395s
]

for (const table of tables) {
  console.log(`copying ${table} ..`);
  const start = performance.now() / 1000;
  ssdb.exec(`INSERT INTO main.${table} SELECT * FROM old.${table}`);
  const finish = performance.now() / 1000;
  const elapsed = finish - start;
  console.log(`  finished, ${elapsed} s`);
}

console.log(`copying transcriptItems ..`);

const sql_copy = ssdb.prepare(`
  INSERT INTO main.transcriptItems
  SELECT * FROM old.transcriptItems
  WHERE vatID = ? AND position >= ?
`);

const allVats = ssdb.prepare("SELECT * FROM old.transcriptSpans WHERE isCurrent = 1").all();
allVats.sort((a,b) => Number(a.vatID.slice(1)) - Number(b.vatID.slice(1)));
for (let data of allVats) {
  const { vatID, startPos, endPos } = data;
  console.log(` copying vat ${vatID}: count = ${endPos - startPos}`);
  //const start = performance.now() / 1000;
  sql_copy.run(vatID, startPos);
  //const finish = performance.now() / 1000;
  //const elapsed = finish - start;
  //console.log(`   finished, ${elapsed} s`);
  // too short to bother logging, max 6ms
}

console.log(`detaching old`);
ssdb.exec(`DETACH old`);

console.log(`pruning complete`);




// copy current items

// We basically want to do `sqlite3 old.db ".dump TABLE" | sqlite3
// new.db` for all tables except transcriptItems, but our kvStore has
// keys with NULs in them, and the sqlite3 CLI tools do not handle
// them well: the keys get truncated, causing corruption (and
// duplicates, which violate the UNIQUE KEY constraint). It is
// possible to write a CLI query with format() and hex() to build
// INSERT statements that will not corrupt the data, but the new DB
// gets BLOBs instead of STRINGs, and then my usual 'select * from
// kvStore' tools don't give me readable results.

// So we do the copy from userspace. It's probably not much slower.

// .schema includes CREATE TABLE and CREATE INDEX
// .dump includes CREATE TABLE but not index
//
// so maybe use .dump on all tables except transcriptItems, then parse
// .schema output to get and execute the CREATE INDEX statements (and
// execute table+index for transcriptItems), then copy old items

// sqlite3 ss.sqlite .tables
//   then join lines with spaces, then split on spaces
// sqlite3 ss.sqlite '.dump TABLE' | sqlite3 new.sqlite


// TODO it would be nice to confirm the table names, to make sure that
// this copying code isn't missing anything that was added later. I
// think our use of INSERT INTO / SELECT * means that we aren't at
// risk of missing any columns.


// 4m35s to dump+import kvStore on run-58. but had four UNIQUE constraint failures
//  52s to .dump

// the only index is currentTranscriptIndex, on transcriptSpans

// 2m19s to lz4cat run-58
// a few seconds to copy
// 23m36s to drop table transcriptItems


// confirm table names

// TODO confirm table names, ideally confirm row names

// separate statement to copy each table, given need to enumerate all
// rows in the INSERT arguments


