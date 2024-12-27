// @ts-nocheck
/* eslint-disable */
import '@endo/init';
import { performance } from 'perf_hooks';
import { importBundle } from '@endo/import-bundle';
import bundleSource from '@endo/bundle-source';
// import { importLocation } from '@endo/compartment-mapper';
import { makeReadPowers } from '@endo/compartment-mapper/node-powers.js';
import fs from 'fs';
import url from 'url';
import { entryPaths as lockdownEntryPaths } from '@agoric/xsnap-lockdown/src/paths.js';
import { entryPaths as supervisorEntryPaths } from '@agoric/swingset-xsnap-supervisor/src/paths.js';
import { importLocation2 } from './archive-util.js';

const targets = {
  kernel: ['../src/kernel/kernel.js', undefined],
  adminDevice: ['../src/devices/vat-admin/device-vat-admin.js', undefined],
  adminVat: ['../src/vats/vat-admin/vat-vat-admin.js', undefined],
  comms: ['../src/vats/comms/index.js', undefined],
  vattp: ['../src/vats/vattp/vat-vattp.js', undefined],
  timer: ['../src/vats/timer/vat-timer.js', undefined],

  lockdown: [ lockdownEntryPaths.lockdown, 'getExport' ],
  supervisor: [ supervisorEntryPaths.supervisor, 'getExport' ],
};

const readPowers = makeReadPowers({ fs, url });

async function run() {
  console.log(
    `${'name'.padStart(12)}  bundle    size       import   importLocation`,
  );
  for (const [name, [rel, format]] of Object.entries(targets)) {
    const fn = new URL(rel, import.meta.url).pathname;
    const start_ms = performance.now();
    const bundle = await bundleSource(fn, { format });
    const bundle_ms = `${Math.floor(performance.now() - start_ms)}`;
    let size;
    if (bundle.endoZipBase64) {
      size = bundle.endoZipBase64.length;
    } else if (bundle.source) {
      size = bundle.source.length;
    }
    size = `${size}`;
    const t1 = performance.now();
    if (name === 'kernel') {
      const ns = await importBundle(bundle, {
        filePrefix: 'kernel/...',
        endowments: {
          console,
          assert,
          // require: kernelRequire,
          // URL: globalThis.Base64, // Unavailable only on XSnap
          // Base64: globalThis.Base64, // Available only on XSnap
        },
      });
    }
    const t2 = performance.now();
    const import_ms = `${Math.floor(t2 - t1)}`;

    const entry = url.fileURLToPath(new URL(rel, import.meta.url));
    const t3 = performance.now();
    if (name === 'kernel') {
      const { namespace } = await importLocation2(
        entry,
        {
          endowments: {
            console,
            assert,
            TextDecoder,
            TextEncoder,
            URL,
          },
        },
        readPowers,
      );
    }
    const t4 = performance.now();
    const importLocation_ms = `${Math.floor(t4 - t3)}`;
    console.log(
      `${name.padStart(12)}: ${bundle_ms.padStart(4)}ms   (${size.padStart(
        9,
      )}) ${import_ms.padStart(4)}ms ${importLocation_ms.padStart(4)}ms`,
    );
  }
}

run().catch(err => console.log(err));
