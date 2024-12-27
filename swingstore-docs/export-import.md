(redundant, use data-export.md instead, merge these contents in)

# Exporting / Importing Swingstore Data

To enable host applications to clone their state (eg to efficiently start a new instance, like a new validator or follower node), the swing-store provides an API to "export" the entire state into an "Export Dataset". A corresponding API enables the creation of a new swing-store from such a dataset.

The dataset consists of two pieces: the "export-data" records (string/string key-value pairs), and a list of named "artifact" blobs. Each export-data record is fairly small, although there may be a lot of them. The bulk data is stored in the artifacts, whose values contain arbitrary binary data (such as compressed heap snapshots).

Exports can take a long time, so the export code is designed to not interfere with ongoing updates of the swingstore state: you don't need to stop execution while the export proceeds.

# Export API

To create an export dataset, start by calling `makeSwingStoreExporter()` (note that it is a standalone function, *not* a method of `hostStorage`):

```js
import { makeSwingStoreExporter } from '@agoric/swing-store;

const exporter = makeSwingStoreExporter(dbDir, options);
```

The exporter will be locked to whatever swingstore state was committed at the time of the call, even if subsequent execution causes changes to accumulate.




# Validation

The export-data records are used to validate the artifacts. That means an importing swingstore relies upon the export-data being correct: your application must provide a secure channel to deliver the export-data records without corruption. But, once that is accomplished, the importing swingstore can detect corruption in the artifact contents, so your application can safely use an insecure channel for the artifacts. The worst an attacker can do is prevent the import from succeeding: they cannot trick the importer into accepting corrupted artifact data.




The exporting application 
