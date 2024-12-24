import '@endo/init';
import { performance } from 'perf_hooks';
import fs from 'fs';
import sqlite3 from 'better-sqlite3';

// Given a swingstore.sqlite filename, prune all the old (historical,
// not-current-span) transcript entries from it. Note that this is destructive.
//
// With --vacuum-into FN, it will then produce a new DB that has all
// the same (pruned) data, but is a lot smaller.

let [dbfn, ...args] = process.argv.slice(2);
let intofn;
if (args.length >= 2) {
  if (args[0] === '--vacuum-into') {
    intofn = args[1];
    args = args.slice(2);
  }
}
if (args.length) {
  throw Error(`unknown args: ${args.join(' ')}`);
}

const ssdb = sqlite3(dbfn);

let per;
const sql_count = ssdb.prepare("SELECT COUNT(*) FROM transcriptItems WHERE vatID=? AND position<?");
sql_count.pluck(true);
const sql_del = ssdb.prepare("DELETE FROM transcriptItems WHERE vatID=? AND position<?");
const allVats = ssdb.prepare("SELECT * FROM transcriptSpans WHERE isCurrent = 1").all();

allVats.sort((a,b) => Number(a.vatID.slice(1)) - Number(b.vatID.slice(1)));

for (let data of allVats) {
  const { vatID, startPos } = data;
  const count = sql_count.get(vatID, startPos);
  if (count === 0) {
    console.log(`skipping vat ${vatID}, already pruned`);
    continue;
  }
  let expected = "?";
  if (per !== undefined) {
    expected = `${Math.floor(1000 * per * startPos)/1000} s`;
  }
  console.log(`pruning vat ${vatID}: count = ${count}, eta ${expected}`);
  const start = performance.now() / 1000;
  sql_del.run(vatID, startPos);
  const finish = performance.now() / 1000;
  const elapsed = finish - start;
  let new_per = elapsed / count;
  if (per === undefined) {
    per = new_per;
  }
  per = (per + new_per) / 2;
  console.log(`                took ${Math.floor(1000*elapsed)/1000} s, ${Math.floor(per*1e6)} us/item`);
}
console.log(`pruning complete`);

if (intofn) {
  console.log(`vacuuming, takes a minute or two`);
  ssdb.prepare(`VACUUM INTO '${intofn}'`).run();
  console.log(`vacuum complete: ${intofn}`);
}
