# MENINX ProofKit

**Check that the files you received match the files that were delivered.**

[![Verify ProofKit](https://github.com/G-B-H/meninx-proofkit/actions/workflows/ci.yml/badge.svg)](https://github.com/G-B-H/meninx-proofkit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-c6a86b.svg)](LICENSE)

Create a deterministic SHA-256 manifest for a delivery folder, then identify
missing, modified or unexpected files. ProofKit runs offline with Python 3.10+
and has no third-party runtime dependencies.

Useful for checking a handoff, a copied release folder or a collection of build
artifacts against a manifest you trust. The command does not upload files,
contact a service or execute the delivery.

## Try it in a minute

```sh
git clone https://github.com/G-B-H/meninx-proofkit.git
cd meninx-proofkit
python -m meninx_proofkit create examples/delivery -o delivery-manifest.json
python -m meninx_proofkit verify examples/delivery delivery-manifest.json
```

A matching delivery prints `Integrity verified.` and exits with code 0. Edit one
of the example files and run verification again: the changed file is reported and
the exit code becomes 1.

The examples are invented. From a checkout, no installation or package download
is required. If your machine calls Python `python3` or `py`, use that command.
You can also install the local project with `python -m pip install .` in a suitable
build environment to obtain the `meninx-proofkit` console command. This may fetch
build dependencies; execution of the installed tool remains offline. There is no
claim of a PyPI publication.

## Commands

| Task | Command |
| --- | --- |
| Create a manifest | `python -m meninx_proofkit create delivery -o manifest.json` |
| Verify a delivery | `python -m meninx_proofkit verify delivery manifest.json` |
| Request JSON output | Append `--json` to either command. |
| Replace an existing manifest | Append `--force` to `create`, intentionally. |
| Read command help | `python -m meninx_proofkit create --help` |

Keep the manifest **outside** the delivery directory. Both commands reject an
internal manifest. Creation protects existing outputs unless `--force` is
provided, and completes validation before writing a replacement. It writes a
temporary file on the destination filesystem and publishes the completed file
atomically. Creation without `--force` uses an atomic hard link, so that filesystem
must support hard links; unsupported filesystems return an operational error.

Verification reports the three difference categories independently:

```text
missing: instructions.txt
modified: release.json
unexpected: temporary.log
```

This is an illustrative result. With `--json`, an operation returns a single JSON
object. Argument syntax errors and help retain the standard text format.

| Exit code | Meaning |
| --- | --- |
| `0` | Manifest created, or all recorded files match. |
| `1` | Verification found differences. |
| `2` | Invalid input or an operational error prevented completion. |

## What is checked

The [versioned manifest](docs/FORMAT.md) contains sorted POSIX-relative paths,
byte sizes and SHA-256 digests, with no timestamp or machine identity. Every regular
file is included, including hidden files. No files are silently excluded. Changes
to file contents are detected even if the byte size stays the same.

Creation and verification share path validation. Absolute paths, traversal,
noncanonical paths, backslashes, colons, NUL characters, duplicate paths and
duplicate JSON members are rejected. Symlinks, Windows reparse points and special
files are rejected in the delivery tree. The manifest must be a regular file.
The path rules do not guarantee that every allowed Linux filename can be created
on Windows: filesystem naming and case-sensitivity differences still apply.

## Trust and limits

A comparison is meaningful only with a **trusted manifest**. Hashes do not identify
an author, authenticate a sender or establish that files are safe to execute.
Keep or transmit the manifest through a trusted channel, or sign it separately.

ProofKit does not take a filesystem snapshot or lock the input files. Concurrent
changes can produce inconsistent results. Use stable delivery folders; do not use
this as a boundary against an adversary who can modify the tree during scanning.

Empty directories, permissions, ownership, timestamps, alternate data streams
and extended attributes are outside the format. Case-sensitive filenames remain
distinct. GitHub Actions is configured to exercise the CLI and tests on Windows
and Linux, with Python 3.10 and 3.13; the [run history](https://github.com/G-B-H/meninx-proofkit/actions/workflows/ci.yml)
is the source for actual execution results. Other platforms are not claimed as tested.

## Develop and contribute

```sh
python -m unittest discover -s tests -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development loop and
[CHANGELOG.md](CHANGELOG.md) for changes. Report a reproducible problem through
[Issues](https://github.com/G-B-H/meninx-proofkit/issues) using invented data.

Original project by MENINX AGENCY. Licensed under [MIT](LICENSE).
