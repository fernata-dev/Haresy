# Install Bawwab (بوّاب) — every system

Bawwab is a Python program (3.11 or newer, no other dependencies). After installing you get two
commands: `bawwab` (the tool and the app) and `hares` (the research benchmark).

> Tested automatically on Linux (Ubuntu, Python 3.11 and 3.13), macOS and Windows (Python 3.12) by
> the CI on every push; see `.github/workflows/ci.yml`. The app-menu launcher is Linux-only.
> Until this branch is merged, the install URL needs `@ccr-bf26486f-ag5cn6` at the end.
> If the repository is private, git will ask you to sign in to GitHub.

## CachyOS / Arch Linux

Arch marks the system Python as "externally managed", so do **not** use `sudo pip install`;
use `pipx` (one isolated environment for Bawwab).

```bash
sudo pacman -S --needed git python python-pipx
pipx ensurepath            # then open a new terminal
pipx install "git+https://github.com/fernata-dev/Haresy.git@ccr-bf26486f-ag5cn6"
bawwab ui                  # opens the app in your browser
bawwab shortcut            # optional: adds "Bawwab / بوّاب" to your app menu
```

Local AI for the research pilot (Ollama from the Arch repositories):

```bash
sudo pacman -S ollama          # NVIDIA: ollama-cuda   AMD: ollama-rocm
sudo systemctl enable --now ollama
ollama pull qwen2.5:7b-instruct
```

## Debian / Ubuntu

```bash
sudo apt install git python3 python3-venv pipx
pipx ensurepath
pipx install "git+https://github.com/fernata-dev/Haresy.git@ccr-bf26486f-ag5cn6"
bawwab ui
```

## macOS

```bash
brew install python git pipx
pipx ensurepath
pipx install "git+https://github.com/fernata-dev/Haresy.git@ccr-bf26486f-ag5cn6"
bawwab ui
```

## Windows (PowerShell)

```powershell
winget install Python.Python.3.12 Git.Git      # or install Python from python.org ("Add to PATH")
py -m pip install --user pipx
py -m pipx ensurepath                           # then open a new PowerShell window
pipx install "git+https://github.com/fernata-dev/Haresy.git@ccr-bf26486f-ag5cn6"
bawwab ui
```

## For the research work (all systems)

The benchmark needs the repository itself (data, results, tests):

```bash
git clone -b ccr-bf26486f-ag5cn6 https://github.com/fernata-dev/Haresy.git
cd Haresy
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m hares restore-tags
python -m pytest
```

Then follow `docs/STUDENT_GUIDE.md`.

## Uninstall

```bash
bawwab unprotect          # first, if you applied protection (restores your configs)
bawwab shortcut --remove  # if you added the launcher
pipx uninstall bawwab
```
