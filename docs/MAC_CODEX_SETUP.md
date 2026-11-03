# Open OpenMHD-RS in Codex on a Mac Pro

This is a *local setup guide*. Files in this repository can be cloned to the Mac; this GitHub handoff does **not** automatically install software, clone a local folder, or import a ChatGPT conversation as a Codex chat.

## 1. Prerequisites

- The combined ChatGPT desktop app supports Codex on **macOS 14+** and either **Intel or Apple Silicon (M1 or newer)**; see <https://chatgpt.com/download/> and <https://help.openai.com/en/articles/9275200-downloading-the-chatgpt-macos-app>.
- Git installed. If not already installed, `xcode-select --install` can install Apple's Command Line Tools.
- GitHub repository is public, so no GitHub credentials are required to clone. Authenticated GitHub access will be needed to push.
- Rust toolchain is needed when implementation begins, not simply to open planning docs. Install via <https://rustup.rs/> following current platform guidance.

Check the system in macOS Terminal:

```bash
uname -m
sw_vers -productVersion
git --version
```

## 2. Clone the project to the Mac

```bash
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/arm2arm/openmhd-rs-.git
cd openmhd-rs-
git status
```

**Important:** The GitHub repo name ends with a trailing hyphen: `openmhd-rs-`.

If you already cloned it, run `git pull --ff-only` inside the existing clone instead of cloning a second copy.

## 3. Open the local folder in Codex

1. Install or update ChatGPT desktop from <https://chatgpt.com/download/>.
2. Sign in with the ChatGPT account you use for Codex.
3. Select **Codex** from the desktop app's mode/menu.
4. Choose **Add new project** (or **Cmd+O**, if available) and select `~/Projects/openmhd-rs-`.
5. Create a new Codex chat in that project. Codex should read the root `AGENTS.md`; verify by asking it to summarize the project and M0 gate.
6. Paste the first prompt from `codex/FIRST_TASK.md` (or ask: `Read codex/FIRST_TASK.md and perform its task.`).

Existing **ChatGPT conversation history does not automatically become Codex chat history**. The repository contains a curated handoff at `docs/CODEX_HANDOFF.md`.

## 4. Optional command-line workflow

If you already have Codex CLI installed and configured, start it from the cloned repository root:

```bash
cd ~/Projects/openmhd-rs-
codex
```

Do not assume Codex CLI is installed by the desktop application. Refer to the official Codex CLI documentation for installation and authentication.

## 5. Development toolchain (later)

When M1 starts, install Rust using rustup and configure an MPI implementation compatible with the `mpi` crate (e.g., through a package manager such as Homebrew). Verify `rustc --version`, `cargo --version`, `mpicc --version` and MPI linking before adding rsmpi-based code.

Mac Pro local tests are useful for development. Slurm/MPI multi-node tests require access to an HPC cluster and a configured compatible runtime; the repository does not grant that access.
