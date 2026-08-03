# The application runs on a single declared Python version

The application targets **Python 3.13**.

One version is declared, in `.python-version`. Every other place that names an interpreter derives from that declaration and must not diverge from it. There are seven such places, and they are listed because the list is the whole requirement:

- `Dockerfile` - the image that actually ships
- `pyproject.toml` `[tool.ruff] target-version`
- `pyproject.toml` `[tool.mypy] python_version`
- `.github/workflows/ci.yml` - three `setup-python` jobs
- `.pre-commit-config.yaml` `default_language_version`
- `README.md` - the version badge
- `README.md` - the **Prerequisites** list, which is what a new contributor actually installs from

This list has been wrong twice, and both times in the same direction: a place that names the interpreter was not counted, so the application shipped on one version while something else targeted another. First it was CI and pre-commit, which decide whether a change may merge. Then it was the two entries above - the front page - where the cost lands on somebody who has no way to know better: they install what the README says, and `pre-commit` then fails looking for an interpreter they were never told to have.

So: **if an eighth place appears, it belongs on this list**, and a place counts whether or not any tool reads it. Nothing mechanical enforces this - no gate in this repository reads prose - which is precisely why the obligation is written down rather than assumed.

Django 6.0 supports 3.12-3.14; 3.13 sits inside that window with headroom on both sides.
