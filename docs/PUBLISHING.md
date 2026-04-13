# Publishing Klauso to PyPI

This document lists **what maintainers need** so a release can reach https://pypi.org/project/klauso/

## Option A — Trusted Publishing (recommended)

No long-lived API token on your laptop.

1. **PyPI account**  
   Register at https://pypi.org/account/register/ if you do not have one.

2. **Create the project on PyPI** (first release only)  
   - Either upload once with **Option B** below, **or**  
   - Create an empty project in the PyPI web UI if available for your account.

3. **Configure the trusted publisher on PyPI**  
   - Project → **Settings** → **Publishing** → **Add a new pending publisher**  
   - Publisher: **GitHub**  
   - Repository: `OWNER/REPO` (e.g. `Mecha-Aima/AI-coding-agent-harness`)  
   - Workflow name: `publish.yml` (or whatever file you add under `.github/workflows/`)  
   - Environment: `pypi` (optional but recommended; must match the workflow `environment:` name)

4. **Merge the publish workflow** in this repo (see [.github/workflows/publish.yml](../.github/workflows/publish.yml)) and ensure it runs on **`release`** (published) or **`workflow_dispatch`** as you prefer.

5. **Bump version** in [pyproject.toml](../pyproject.toml) (`[project] version = ...`), commit, tag (`git tag v0.1.1 && git push origin v0.1.1`), then **create a GitHub Release** from that tag so the workflow runs and uploads to PyPI.

## Option B — API token (manual upload)

1. **PyPI account** (same as above).

2. **Create an API token**  
   - https://pypi.org/manage/account/token/  
   - Scope: project `klauso` (or whole account for the first upload).

3. **Build artifacts**

   ```bash
   python3 -m pip install build twine
   cd /path/to/repo
   rm -rf dist/
   python3 -m build
   ```

4. **Upload**

   ```bash
   python3 -m twine upload dist/*
   ```

   When prompted, username `__token__`, password the token value (including `pypi-` prefix if shown).

**Environment variable (CI or local):**

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YOUR_TOKEN_HERE
python3 -m twine upload dist/*
```

## What the automation / I cannot do without you

| Item | Who provides it |
|------|------------------|
| PyPI account | You |
| First project creation or token | You |
| Trusted publisher mapping (GitHub repo + workflow) | You in PyPI UI |
| Git tag + version bump | Maintainer |
| `PYPI_API_TOKEN` in CI secrets | You (only if using token-based upload in Actions instead of OIDC) |

After the first successful upload, users can install with:

```bash
pip install klauso
# or
pipx install klauso
```
