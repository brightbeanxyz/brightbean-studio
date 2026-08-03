# Dependency versions are ranges, with no lockfile

`requirements.txt` declares ranges. There is no `uv.lock`, `poetry.lock` or `requirements.lock` in the repository, so the resolved transitive tree differs between any two installs.

This migration verified that the full declared set resolves against Django 6.0.7 (83 packages, no conflicts), but a successful resolution is not a reproducible one.

Decision: **left as-is.** Introducing a lockfile changes how every deployment target installs dependencies, which is a larger and independent change. Recorded so the absence is understood as unaddressed rather than considered and accepted.
