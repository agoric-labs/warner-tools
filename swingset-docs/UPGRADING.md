# How to upgrade a deployed kernel

The SwingSet library is designed to be embedded in a "host application", which provides all IO, persistence (via the swing-store), and when-to-run execution policy. Deployed instances are typically very long lived (years or more), and must maintain stable+predictable behavior over that entire lifetime. Consensus deployments (blockchains), in particular, require identical behavior amongst all copies despite scheduled upgrades.

Each running instance will be executing some "kernel code", which is loaded off disk every time the host application is launched. The entry point will be the host application itself, which then does an `import` of code from the `@agoric/swingset-vat` package (primarily `initializeSwingset` and `makeSwingsetController`). The swingset code then imports other packages. It also generates a kernel bundle at startup, which causes code to be imported from still more packages.

These running instances will interact with saved state, in the form of the "swingstore" database. The host application is responsible for importing `initSwingStore` and `openSwingStore` from the `@agoric/swing-store` package, calling them to create a DB on disk, and passing a handle to the new kernel. This SQLite database contains all other durable state, including the contents of vats.

From time to time, the host application will be upgraded: one version is shut down, then a new version is launched, against the same swingstore DB. The new host app may use new kernel code, by virtue of having a `package.json` whose `dependencies:` list cites a higher version of some kernel package than before.

This new kernel code must be able to work with the swingstore state generated by the earlier version, just like a typical desktop word processor application must be able to load documents created by an earlier version.

In some cases, to take full advantage of new kernel features, the host application must perform explicit upgrade calls, *after* launching with the new kernel code, to update the saved state. This does not happen automatically.

This document describes the changes from one version of kernel code to the next, and lists the application-visible upgrade steps that are necessary to achieve complete functionality.

## Kernel Instance Components

A deployed instance of the kernel consists of several components, all of which must be compatible with one another. These components are broken up into several categories.

The first category is the kernel runtime code. This is all the code imported by the host application, each time it starts up. Host applications typically need to import from `@agoric/swing-store` to create the swingstore DB handle, then they import something like `makeSwingsetController` from `@agoric/swingset-vat` to build the kernel controller itself. Internally, the controller will bundle and immediately execute additional sources from `SwingSet/src/kernel/`, which provides the bulk of the kernel itself. None of this code is stored in a database, and every application startup uses the code that it finds on the disk in that moment.

The second category are the built-in vat bundles. These are bundled only once, during kernel initialization, when the host application is started for the very first time, from whatever code is on disk at that moment

The first category are the libraries of code which run in the "controller" or the "kernel compartment", which come from multiple packages. Each time

Looking at the long-term lifecycle of the kernel, we can describe it as a series of "kernel incarnations" (each using a different version of kernel code)

When a given deployment is first initialized, 


## Kernel Packages and their Versions

The "kernel" is a collection of code that makes up the SwingSet runtime kernel. This code is not stored in the database, but rather is loaded from disk each time the host application is started, as is typical for a Node.js application.

Some portions of this code are "bundled" (aggregated into a single file, using `@endo/bundle-source`), and the bundle is stored in the DB for use later. 






The agoric-sdk monorepo is maintained in a coherent state: all kernel packages in any given commit are tested to work against each other. That means a new deployment which is initialized from 

As a monorepo, the version numbers of the individual kernel packages are not updated with every commit: they only change when a release is performed. As a result, between releases, a package version string like "@agoric/swingset-vat@0.32.2" is not unique: many commits, which various behaviors, all have a package.json whose `version:` property says `0.32.2`.

The packages published to NPM at release time are the canonical definition of each version. Each version is associated with a tag in the `agoric-sdk` monorepo with the matching code. So when this document describes e.g. "swingset-vat at 0.32.2", it means the code as present on NPM at that version, which will be generated from the code in `agoric-sdk` with the `@agoric/swingset-vat@0.32.2` tag.


## Kernel Versions

### First Release: 0.32.2 02-Jun-2023

* @agoric/swingset-vat 0.32.2
* 02-Jun-2023
* agoric-sdk monorepo commit 91cf51bfc622c128bd559f01d6c1b0a617beb13c
