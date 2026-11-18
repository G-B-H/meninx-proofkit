# Contributing

Start with a reproducible problem, a small patch and the behavior it should change.
For a bug, include the Python version, operating system, command and a minimal
example using invented data. Do not attach credentials, client files or a manifest
that exposes sensitive file names.

## Development loop

Clone the repository and use Python 3.10 or newer. The runtime and tests use the
standard library; neither requires a package download.

```sh
python -m unittest discover -s tests -v
python -m meninx_proofkit create examples/delivery -o delivery-manifest.json
python -m meninx_proofkit verify examples/delivery delivery-manifest.json
```

Keep the create/verify contract consistent, preserve existing outputs when an
operation fails, and add a focused test for changed behavior. Preserve deterministic
JSON. Document platform limits and avoid claims of authenticity or a filesystem
snapshot: the tool provides neither.

Open a pull request explaining the problem, the resulting behavior and the checks
you actually ran. Report checks you could not run. Contributions are under the
repository's [MIT license](LICENSE).

