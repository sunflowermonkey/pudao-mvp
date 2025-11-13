"""
Lightweight package shim for running this repository as package `pudao`.

This module sets the package __path__ to the project root so that
subpackages stored in sibling directories (e.g. `gate`, `cli`, `dsl`, `smt`)
can be imported as `pudao.gate`, `pudao.cli`, etc. This avoids having to
physically move files into a `pudao/` subtree.

This is intentionally minimal and safe for development only.
"""
import os

# Make `import pudao.<subpkg>` search the project root (one level up).
__path__ = [os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))]
