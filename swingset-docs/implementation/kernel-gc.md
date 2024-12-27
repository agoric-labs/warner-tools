Notes on how GC is implemented inside the kernel.

## kernel object refcount processing

Each kernel object has a (reachable, recognizable) refcount pair, stored in `${kref}.refCounts`. Refcounts come from:

* importing vat c-lists: (1,1) if the entry is marked with an `'R'` for "reachable", (0,1) if marked with `'_'` for "recognizable"
* run-queue messages that include the kref as the target (always 1,1)
* run-queue messages that include the kref in the args (always 1,1)
  * each occurrence in .slots gets a separate refcount, but in general vats don't repeat slots
* promise resolution data that includes the kref (1,1, as above)

Note that the *exporting* vat c-list entry does not get a refcount.

Vat c-list refcounts are incremented as the delivery arguments or syscall.callNow results are translated from krefs to vrefs (for new imports), or when syscall.send/syscall.resolve arguments are translated from vrefs to krefs (for new exports).

`kernelKeeper` holds an ephemeral Set of krefs which need to be examined in `maybeFreeKrefs`. We add krefs to this set when `decrementRefCount` sees either `reachable` or `recognizable` touch zero. We also add krefs that become "orphaned" (they lack an owing vat, signalled by `${kref}.owner` being missing).

We orphan krefs with `kernelKeeper.orphanKernelObjects`, which is called from three places:

* `cleanupAfterTerminatedVat` when the dead vat's exporting c-list entry is deleted
* `processUpgradeVat` when the kernel abandons non-durable exports on the vat's behalf
* `syscall.abandonExports` when a vat explicitly abandons an export
  * (liveslots used to call this during exitVat, but processUpgradeVat took over that job)

We do not process the refcount immediately upon touching zero, because we allow "break before make" sequences, so the refcount might come back up again before the end-of-turn. Instead, the kernel's `processDeliveryMessage` calls `kernelKeeper.processRefcounts()` after the crank is finished (and also after checking the CrankResults for `.abort`, `.terminate`, etc).

`processRefcounts` walks `maybeFreeKrefs` and examines each one to see if it is really dead, and if anything needs to be done. For objects, the case breakdown is:

* still reachable: do nothing
* unreachable, owned by a live vat:
  * check the exporting vat's c-list entry to see whether it thinks of the object as reachable
    * if so, enqueue a `dropExport` gcAction to the exporter
  * if the object is also unrecognizable, enqueue a `retireExport` gcAction to the exporter
* unreachable, owned by a terminated vat:
  * orphan the kref: delete `.owner` and the exporting vat's c-list entry
    * (we don't use `orphanKernelObjects()` because it would push the kref back onto maybeFreeKrefs, and we can avoid a second pass by doing all the work here)
  * then fall through to the "unreachable, orphaned" case
* unreachable, orphaned
  * if recognizable, use `retireKernelObjects()` to enqueue `retireImport` gcActions to all importers
    * and `deleteKernelObject()` to remove `.owner` and `.refCounts`
  * if unrecognizable, just `deleteKernelObject()`

Some tricky cases/constraints to remain aware of:

* once a vat is terminated, we must not send it any messages, including gcActions like `dropExport` or `retireExport`
  * but we also cannot afford to immediately orphan all its exports, we must do that slowly
  * so if one of these "lame exports" is dropped by other vats, the "owned by a terminated vat" case in `processRefcounts` immediately orphans that one export, doing the same work that the slow deletion process would have done, and then falls through to the common "orphaned" case

## Invariants to maintain

* c-list entries always come in pairs, `${vatID}.c.${kref}` and `${vatID}.c.${vref}`, if one is present, the other must be present
* each kref is either owned or orphaned
  * if owned, `${kref}.owner` will be set, and the owning vat will have a c-list entry
  * if orphaned, `${kref}.owner` will be missing, and the owning vat will *not* have a c-list entry
* the owner might think the kref is reachable, or unreachable, indicated by the `'R'` or `'_'` in their `${vatID}.c.${kref}` value
  * this must only be changed during a syscall or delivery: the c-list state must track what the vat has said or has been told
  * any kref-bearing syscall (eg syscall.send arguments) will make it reachable
  * syscall.abandonExports and dispatch.dropExports will make it unreachable
  * but dead vats do not need to be told about changes, the kernel is free to clear the flag when it likes
