# Manifest format v1

A manifest is UTF-8 JSON with exactly three top-level members. Duplicate JSON
member names are rejected.

```json
{
  "version": 1,
  "algorithm": "sha256",
  "files": [
    {
      "path": "hello.txt",
      "size": 0,
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  ]
}
```

`version` is the integer 1. `algorithm` is exactly `sha256`. Every file has a
relative POSIX path, a non-negative integer byte size and a lowercase, 64-character
SHA-256 digest. Booleans are not accepted as integers. Creation sorts entries by
path and includes no timestamp or machine identity.

Paths must be canonical and relative. Absolute paths, traversal components,
backslashes, colons, NUL characters and duplicate paths are rejected. Creation
applies the same path validation as verification. The tool does not rename files
to make them portable; incompatible names must be changed by their owner first.
Case-sensitive file names remain distinct. A case-insensitive filesystem may be
unable to represent a delivery created on a case-sensitive filesystem.

All regular files are included, including hidden files. Empty directories,
permissions, ownership, timestamps, alternate streams and extended attributes
are outside this format. Symlinks, Windows reparse points and special files are
rejected. The manifest must be stored outside the delivery directory.

Verification compares file paths, byte sizes and hashes. A result is one of:

| Exit code | Result | Meaning |
| --- | --- | --- |
| 0 | `created` or `ok` | The requested operation completed. |
| 1 | `changed` | The delivery has missing, modified or unexpected files. |
| 2 | `error` | Invalid input or an operational error prevented completion. |

`--json` produces one JSON result for an operation. Argument-parser errors and
`--help` retain the standard command-line text format. A successful comparison is
meaningful only with a trusted manifest and stable input files. It does not
identify an author, authenticate a sender or prove a delivery is safe to execute.

