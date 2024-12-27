# Promises vs Upgrades

When a Promise is sent across a vat boundary, Swingset assigns that promise an ID (`kpid`, for "Kernel Promise ID"), and starts tracking its state. One vat is the *decider*, and the other vats are *subscribers*. When the Promise is a result of some outbound message, the receiving vat will be the Decider. When the Promise is created with `new Promise()` and exported from a vat, the sending vat is the Decider. (The situation is more complex when the promise is used as a message result and pipelining is involved).

Normally, when neither vat is upgraded, the story looks like this:

(image 1)

The lifetime of each vat is split into *incarnations* by an upgrade event. The only things to survive the upgrade are:

* the identity, state, and contents of durable objects and durable collections
  * if exported, or reachable through the special MapStore named `baggage`
  * the state can retain imports from other vats
* durable promise watchers (described below)

Promises are *not* durable, and they are lost when an upgrade happens.

## Decider is Upgraded: Promises are Rejected

When the *deciding* vat is upgraded, the kernel automatically rejects all its outstanding Promises. As the `resolve()` and `reject()` functions were ephemeral, the new vat incarnation has no equivalent functions (nor any equivalent to the original Promise: note the dashed circle and box in the diagram below). Since the vat no longer has any way to influence those Promises, the kernel rejects them with a particular rejection value known as a "disconnection".

(image)

```js
const disconnection = {
  name: 'vatUpgraded',
  upgradeMessage,
  incarnationNumber,
};
```

The `upgradeMessage` is provided as an argument: `E(adminNode).upgradeVat(bundleCap, { upgradeMessage })`. It can be any string. The `incarnationNumber` is an integer, citing the *old* incarnation (the one that was running before the upgrade).

Subscribing vats need to watch for these distinctive rejection values and treat them differently than a normal rejection. Otherwise, they may mistakenly believe that the original operation has failed, when in fact it might still be outstanding (the new incarnation may still be prepared to resolve/reject the Promise normally). In general, the subscribing vat must be prepared to react to a disconnection by re-acquiring a fresh promise.
 
We have ideas about "durable promises" (see [#3787](https://github.com/Agoric/agoric-sdk/issues/3787)), in which the new vat incarnation would have viable equivalents to the original Promise object, and also the resolve/reject functions. However integrating them with platform-native `Promise` objects (especially `async`/`await` syntax) makes this difficult.
 
 
## Subscriber is Upgraded: Callbacks are Forgotten

When the subscribing vat is upgraded, the new incarnation has no equivalent to the old (imported) Promise object (note the "???" circle in the diagram below), nor is the callback function still around (the "???" rectangle). The kernel still knows that this vat should be told about the `kpid` getting settled (either fulfilled or rejected), but there's nothing left in the upgraded vat which will recognize this `kpid`. As a result, the `dispatch.notify(kpid)` is ignored.

(image 2)

This can easily cause bugs, in which the vat being upgraded forgets to keep following something important. The bug does not usually manifest immediately: nothing surprisinghappens until later, when the original decider calls `resolve()` or `reject()`, but the subscribing vat fails to react the same was as the original incarnation would have.

One way to fix this is for the upgraded vat to save all the objects from which it originally obtained those promises, somewhere in `baggage`. Then, during upgrade, it could iterate through that list, and send messages to acquire fresh promises, as replacements. This is not preferred, as it requires more storage and induces O(N) work at upgrade time (there could be thousands of these promises established by then). So the *Promise Watcher* feature was developed as a better alternative.

## Promise Watchers are Durable

In the examples above, the callback function was an ephemeral (in-RAM) `Function` object, registered by calling some form of `p.then(callback, errback)` on the received Promise. (A similar situation occurs when using `E.when(p, callback, errback)`). As the callback function lives in RAM, it is not durable, and the new incarnation lacks an equivalent to be invoked.

By replacing the ephemeral callback function with a durable "watcher object", we can fix this. These watcher objects are defined to have `.onFulfilled` and/or `.onRejected` methods. These will be called with the resolution (or rejection) value.

The subscribing vat must first use `makeWatcher = defineDurableKind(..)` (or equivalent) to create a Kind for the watchers. Then it must instantiate a watcher by calling their `makeWatcher()`.

Then, when this vat receives a promise that it wants to follow, it should call:

```js
VatData.watchPromise(p, watcher);
```

This will arrange for `watcher.onFulfilled(resolution)` or `watcher.onRejected(rejection)` to be invoked, either during the current incarnation, or in some future incarnation, if and when the decider vat finally settles the promise.

(image 3)

To make it convenient to share the same durable watcher object among multiple promises, each call to `watchPromise()` can include an arbitrary number of additional durable arguments, which will be stored internally, and delivered to the watcher methods:

```js
VatData.watchPromise(p1, watcher, 'foo', 'bar');
VatData.watchPromise(p2, watcher, 'baz');

// later, when p1 is resolved to 'yes' and p2 is rejected with 'no':
// watcher.onFulfilled('yes', 'foo', 'bar');
// watcher.onRejected('no', 'baz');
```

## Watching Local Promises

The Promise Watcher mechanism is mainly intended for watching promises that are decided by some external vat (an "imported" promise). However it is not illegal to call it with a "local" promise, one which is decided by the same vat doing the watching.

```js
const { promise, resolve } = makePromiseKit()
VatData.watchPromise(promise, watcher);
```

If the local promise is resolved or rejected within the same incarnation that started watching it, the `onFulfilled`/`onRejected` method will be invoked as expected:

(image 4)

However if the vat is upgraded before the promise settles, the watcher's `onRejected()` method will be invoked in the new incarnation, some time soon after the upgrade completes. The rationale is that the (ephemeral) `resolve()` and `reject()` methods have gone away, so even if the promise itself survived, there is no longer any way to settle it. The kernel therefore rejects the promise, with the same rejection value that a subscribing vat would observe if the *deciding* vat had been upgraded. This rejection is delivered to the subscribing vat some time after the upgrade completes (during ugprade, the kernel promise entry is marked as rejected, and the `dispatch.notify` messages are pushed onto the end of the run-queue, where they will be delivered after everything else currently on the run-queue).

(image 5)

