import '@endo/init';
import fs from 'fs';
import sqlite3 from 'better-sqlite3';

// create a DB that records block heights, block time, cranks, computrons
// and: votes and tendermint rounds
// and (non-consensus): swingset execution time

// The votes/rounds can be pulled cleanly from 'agd query' from a
// follower, but only back to the pruning depth (my follower prunes
// after 200k blocks, which is about 16 days). They can also be parsed
// from my monitor.out summaries, which I have back to 02-apr-2024
// (block 14450245)l


function makeDB(dbPath) {
  const db = sqlite3(dbPath);
  const indexes = [];
  const sql = {};
  db.exec(`PRAGMA journal_mode=WAL`);

  db.exec(`CREATE TABLE IF NOT EXISTS blocks (
blockNum INTEGER, -- or 'bootstrap'
blockTime INTEGER,
cranks INTEGER,
computrons INTEGER,
votes INTEGER, -- or NULL if the info isn't available
round INTEGER, -- 0 means the first round succeeded. NULL if unavailable
-- the following are outside of consensus
compute_time FLOAT, -- cosmic-swingset-{begin,end}-block : includes cosmos-sdk time
swingset_time FLOAT -- cosmic-swingset-end-block-{start,finish} : only swingset time
-- PRIMARY KEY (blockNum) -- INTEGER or STRING, so cannot be PRIMARY KEY
)`);
  sql.addBlock = db.prepare(
    `INSERT INTO block VALUES (@blockNum, @blockTime, @cranks, @computrons, @votes, @round, @compute_time, @swingset_time)`,
  );
  indexes.push(`CREATE INDEX IF NOT EXISTS block_blockNum ON block (blockNum)`);
