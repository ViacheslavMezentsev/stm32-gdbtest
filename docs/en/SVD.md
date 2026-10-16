# SVD loading and capture

[Документация](index.md) · [Русский](../ru/SVD.md)

The first 0.5.0 package adds an SVD resource to run configuration.
MMIO read/write and Target.mmio are not implemented yet; selecting SVD grants no access.

```toml
[config]
target = "target.toml"
[mmio]
svd = "device.svd"
```

Paths are relative to session.toml, without home/environment expansion, MCU lookup or
network access. Omit [mmio] to preserve existing behavior. An explicitly selected invalid
SVD produces a preparation ERROR before server startup, not a firmware FAIL.
Exact bytes and SHA-256 travel in config.json: capsules with SVD use schema=2;
without SVD schema=1 is retained. Update the receiving module before using schema=2
packages; older modules cannot accept them. ZIP carries the snapshot in config.json,
without requiring the original source path. Runner additionally saves source.svd and
svd metadata in result.json before starting the server, even without records capture.
A write failure prevents startup.

The catalog is immutable. Each capsule receiver verifies the hash and constructs its
catalog from captured bytes; no serialized Python objects are transported. Reuse is
within a configuration context, not a promise of one parse across all processes.
There is no disk cache.

The supported subset includes registers/fields, arrays/clusters, tested derivedFrom
forms, access rights and side-effect descriptions. Widths are 8/16/32, address units
are 8 bits, addresses aligned and 32-bit, endian little or omitted. This is not full
CMSIS-SVD or vendor-extension support. Unknown constructs are rejected. Missing access
is not replaced with rw; writeOnce/writeConstraint and effects remain restrictions,
not authorization for future operations.

Budgets: 8 MiB input, XML depth 64, 100000 XML nodes, derived depth 32, 100000 instances,
100000 registers, 2000000 copied XML nodes. Arrays have at most 4096 elements.
DTD/entities are prohibited. Public TOML cannot change these budgets; they never grow automatically.

Loader errors have code, stage=configuration, effect=none: svd.source (read),
svd.syntax (XML/description), svd.forbidden_construct (unsupported/prohibited),
svd.limit (budget), svd.reference (inheritance), svd.integrity (hash/snapshot check),
svd.capture (runner write). ZIP integrity may fail earlier at the package layer.
Messages/details are diagnostic; codes provide stable classification.

This validates a description, not a board, Renode model or physical MMIO transaction.
Operations, override and transport qualification remain a separate package.
