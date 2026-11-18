"""Create and check file integrity manifests without network access."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile


class ProofError(Exception):
    pass


def is_reparse(st):
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(getattr(st, "st_file_attributes", 0) & flag)


def canonical_name(name):
    if not isinstance(name, str) or not name or name == "." or "\\" in name or "\x00" in name:
        raise ProofError("invalid manifest path")
    p = PurePosixPath(name)
    if p.is_absolute() or str(p) != name or any(part in (".", "..") for part in p.parts) or ':' in name:
        raise ProofError("unsafe or noncanonical manifest path: " + name)
    return name


def root_path(value):
    path = Path(value).absolute()
    # Examine each lexical component before resolving '..', so links cannot be hidden.
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        st = current.lstat()
        if stat.S_ISLNK(st.st_mode) or is_reparse(st):
            raise ProofError("link or reparse point in delivery root path: " + str(current))
    path = path.resolve(strict=True)
    if not path.is_dir():
        raise ProofError("delivery root must be an existing directory")
    return path


def scan(root):
    records = {}
    def walk(folder):
        with os.scandir(folder) as entries:
            for entry in sorted(entries, key=lambda e: e.name):
                path = Path(entry.path)
                rel = canonical_name(path.relative_to(root).as_posix())
                info = entry.stat(follow_symlinks=False)
                mode = info.st_mode
                if stat.S_ISLNK(mode) or is_reparse(info):
                    raise ProofError("symlink is not allowed: " + rel)
                if stat.S_ISDIR(mode):
                    walk(path)
                elif stat.S_ISREG(mode):
                    digest = hashlib.sha256()
                    size = 0
                    with path.open("rb") as file:
                        for chunk in iter(lambda: file.read(1024 * 1024), b""):
                            size += len(chunk)
                            digest.update(chunk)
                    records[rel] = {"path": rel, "size": size, "sha256": digest.hexdigest()}
                else:
                    raise ProofError("special file is not allowed: " + rel)
    walk(root)
    return records


def manifest_data(path):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ProofError("duplicate JSON key: " + key)
            result[key] = value
        return result
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or is_reparse(info):
            raise ProofError("manifest must be a regular file, not a link or reparse point")
        with path.open(encoding="utf-8") as f:
            data = json.load(f, object_pairs_hook=unique_object)
    except (OSError, ValueError) as e:
        raise ProofError("cannot read manifest: " + str(e)) from e
    if not isinstance(data, dict) or set(data) != {"version", "algorithm", "files"} or type(data['version']) is not int or data['version'] != 1 or data['algorithm'] != "sha256" or not isinstance(data['files'], list):
        raise ProofError("invalid or unsupported manifest")
    records = {}
    for item in data['files']:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256"}:
            raise ProofError("invalid manifest entry")
        name, size, digest = item['path'], item['size'], item['sha256']
        canonical_name(name)
        if name in records:
            raise ProofError("duplicate manifest path: " + name)
        if type(size) is not int or size < 0 or not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ProofError("invalid size or hash: " + name)
        records[name] = item
    return records


def write_atomic(output, content, force):
    if output.is_symlink():
        raise ProofError("output must not be a symlink")
    if output.exists() and not force:
        raise ProofError("output already exists; use --force to replace it")
    fd, name = tempfile.mkstemp(prefix=".proofkit-", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        if force:
            os.replace(name, output)
        else:
            # Link is atomic and fails if a competing writer created output.
            os.link(name, output)
            os.unlink(name)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def execute(args):
    root = root_path(args.directory)
    if args.command == "create":
        output = Path(args.output).absolute()
        # resolve parent to catch an output alias through a symlink.
        resolved = output.parent.resolve() / output.name
        if resolved == root or root in resolved.parents:
            raise ProofError("manifest output must be outside the delivery root")
        records = scan(root)
        payload = {"version": 1, "algorithm": "sha256", "files": [records[key] for key in sorted(records)]}
        write_atomic(output, json.dumps(payload, ensure_ascii=True, indent=2) + "\n", args.force)
        return {"status": "created", "files": len(records), "manifest": str(output)}, 0
    manifest = Path(args.manifest)
    resolved_manifest = manifest.resolve(strict=False)
    if resolved_manifest == root or root in resolved_manifest.parents:
        raise ProofError("manifest must be outside the delivery root")
    expected = manifest_data(manifest)
    actual = scan(root)
    missing = sorted(expected.keys() - actual.keys())
    unexpected = sorted(actual.keys() - expected.keys())
    modified = sorted(p for p in expected.keys() & actual.keys() if expected[p] != actual[p])
    ok = not (missing or unexpected or modified)
    return {"status": "ok" if ok else "changed", "missing": missing, "modified": modified, "unexpected": unexpected}, 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="meninx-proofkit", description="Create and verify deterministic SHA-256 delivery manifests.")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create", help="create a manifest outside the delivery root")
    create.add_argument("directory")
    create.add_argument("-o", "--output", required=True)
    create.add_argument("--force", action="store_true", help="replace existing output")
    create.add_argument("--json", action="store_true", help="emit machine-readable result")
    verify = sub.add_parser("verify", help="compare a directory with a manifest")
    verify.add_argument("directory")
    verify.add_argument("manifest")
    verify.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = parser.parse_args(argv)
    try:
        result, code = execute(args)
    except (ProofError, OSError, ValueError) as e:
        result, code = {"status": "error", "error": str(e)}, 2
    if args.json:
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    elif code == 2:
        print("Error: " + result['error'], file=sys.stderr)
    elif args.command == "create":
        print("Created {} ({} files)".format(result['manifest'], result['files']))
    elif code == 0:
        print("Integrity verified.")
    else:
        for category in ("missing", "modified", "unexpected"):
            for path in result[category]:
                print(category + ": " + path)
    return code
