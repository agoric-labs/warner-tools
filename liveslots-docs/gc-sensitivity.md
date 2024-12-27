
## Unweakable

Any object that meets all of the following criteria must be marked as "unweakable":

* 1: the object is exposed to userspace in any way
* 2: the object is eligible for use as a WeakMap key (so JS `Object`s, not strings)
* 3: the object's lifetime is tied to that of a Representative
* 4: the object does not have a vref

This generally includes the incidental containers we give to userspace in the process of delivering more functional objects, for example the `facets` container which holds all of the named facet Representatives.

per-kind, per-lifetime
