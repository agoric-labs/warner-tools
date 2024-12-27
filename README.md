# warner-tools
random analysis tools

# swingset-docs/

This contains partially-complete documents I wrote up about SwingSet internals. They want to live in packages/SwingSet/ or in its docs/ subdirectory.

# liveslots-docs/

More partially-complete documents to live in `packages/swingset-liveslots/docs/`.

# swingstore-docs/

Same but for `packages/swingstore/`.

# swingset-misc-tools-branch/

This directory contains a few dozen SwingSet analysis tools I wrote over the years. It has exactly the same contents as the `warner/swingset-misc-tools` branch, as submitted for merge in PR #10037, so if that gets merged, these are redundant


# swingset-misc-tools-more/

This contains some additional SwingSet analysis tools that didn't make it into PR #10037

# ghost-chain/

This is a tool I wrote to start from a swingstore (usually copied from a mainnet follower) and then execute some number of actions, like:

* replay a recent delivery
* fire the next timer wakeup event
* terminate and delete one or more vats
* upgrade a vat
* execute a core-eval proposal

It wants to be a package in agoric-sdk, so it can import e.g. SwingSet. I usually ran it by `git checkout` -switching to the `warner/ghost-chain-trunk` branch. I had other branches with similar names for when I needed to perform ghost-replays of e.g. upgrade17 or upgrade16 chain state.

The main output is a slogfile, from which we can measure things like how long the operation takes, or whether any unexpected errors occur. I used this to tool to determine that "one-fell-swoop" deleting of a large price-feed vat would exceed the SQLite value size and crash the kernel.
