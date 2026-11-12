---
title: "MPF Docs"
---

Documentation for people building a pinball machine with the Mission Pinball Framework (MPF). Everything here is
derived from the MPF source code (version `0.82.0.dev0`) and the configs in its test suite, and stands on its own.

**New here?** Follow the path:

1. [Install and run MPF](/get-started/install-and-run/)
2. [The machine folder](/get-started/machine-folder/)
3. [Your first machine](/get-started/first-machine/): a startable game on virtual hardware
4. [Writing config files](/get-started/config-files/)
5. [Connecting FAST hardware](/build/fast-hardware/)

MPF supports many hardware platforms through the same config. FAST is documented first; the platform-neutral pages
apply to all of them.

**Looking something up?** The [reference](/reference/) lists every config section and setting, every annotated event,
the command line and the built-in modes. It is generated from the source, so it matches the code.

**Working on MPF itself?** See [For developers](/architecture/) for the boot sequence and internals.

{{< note >}}
Pages are marked when something has not been run against a real MPF install or real hardware. Treat those as
carefully assembled from the source, and tell us what breaks.
{{< /note >}}
