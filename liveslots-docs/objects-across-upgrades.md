# Object References vs Upgrades

When a vat exports an object, the kernel assigns a "kref" (kernel reference) ID to it. This identifier serves as the name of the object to use in the c-list that sit between each vat and the kernel. The exported object might be "ephemeral", like the in-RAM objects created with `Far`. The Swingset code frequently calls this type of object a "Remotable".

```js
const ephemeral = Far('iface name', {
  method1: arg => arg+1,
  method2: () => 'you just called method two',
});
```

They can also be "virtual", as created from a Kind creator function (the type returned by `defineKind()`). Finally, they can be "durable", as created from a durable-Kind creator function (the type returned by `defineDurableKind()`, or it's Exo cousins). The JavaScript object you get back from the creator function is called a "Representative".

When the object is imported into some other vat, the importing vat's userspace code receives a "Presence", through which it can send messages and compare identities. The importing vat does not know whether the exported object was ephemeral, virtual, or durable.

## Exported Objects vs Upgrades

Only durable objects survive the exporting vat being ugpraded.

(image)

What actually happens is that the new incarnation of the exporting vat contains enough data in its vat-store database to reconstruct the state of the object, if and when the kref ever appears again. The new incarnation has a new `defineDurableKind` call to associate new behavior with the Kind. Together, new behavior and old state can be combined to make a new Representative. Liveslots carefully prevents userspace from being able to tell that the original Representative ever went away.

If the exported object is merely virtual, or ephemeral, when the exporting vat is upgraded, then the object marked as "abandoned". The kernel maps the kref to a special "dead object" (really, the kernel merely erases the "owner" field for the kref). Sending messages to a dead object will always reject the result promise, with a special `Error` object whose `.message` field is the string `vat terminated`. The object maintains its identity, however, so it can still be used for `===` EQ comparison, or as the key of a WeakMap or WeakStore.

(image)

## Imports Across Upgrades

When the *importing* vat is upgraded, the Presence survives if it is somehow held in durable state.

For example, you might store the imported Presence in the state of a durable object, which is itself reachable from the special `baggage` MapStore. Then, in the new incarnation, the code might reach through `baggage` to retrieve an equivalent Presence. The first and second versions of the Presence are functionally indistinguishable (they are different JS objects, but it is not possible to compare them for equality with `===` because they do not exist simultaneously in the same memory space).

(image)

If the imported Presence was only held by ephemeral RAM, and/or stored in merely-virtual state, then the imports are lost across the upgrade. The second incarnation can only reach things through `baggage`, and `baggage` can only reference three things: durable objects, durable collections, and imports.

When the SwingSet upgrade-time GC code is complete, the act of upgrading the vat will drop the reference counts on all the non-durably-held imports. For now, however, we do not have the code to figure out which imports are held durably and which are not, so they will not be released. It will be as if the second incarnation holds a hidden reference to all previous-imported objects.
