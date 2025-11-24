"""
Lightweight package shim for running this repository as package `pudao`.

This module sets the package __path__ to the project root so that
subpackages stored in sibling directories (e.g. `gate`, `cli`, `dsl`, `smt`)
can be imported as `pudao.gate`, `pudao.cli`, etc. This avoids having to
physically move files into a `pudao/` subtree.

This is intentionally minimal and safe for development only.
"""
import os

# Make `import pudao.<subpkg>` search both the package directory and the
# project root (one level up). Keeping the original package directory in
# `__path__` ensures that subpackages located under `pudao/` (e.g.
# `pudao/evidence`) are still discoverable, while adding the project root
# allows a development layout where modules live at the repo root.
pkg_dir = os.path.dirname(__file__)
project_root = os.path.normpath(os.path.join(pkg_dir, ".."))
# Preserve the default package directory and also search the project root.
__path__ = [pkg_dir, project_root]
