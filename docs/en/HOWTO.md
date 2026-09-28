# HOWTO: common commands and problems

[Documentation](index.md) → HOWTO · [Русский](../ru/HOWTO.md)

Developers and agents look here when something does not work, before searching for a
new solution. Each problem lists how to fix it and how to return to the previous
state. Project rules are in [maintenance](maintenance.md); this page has the commands.
A new solution to a common problem is added here in the same commit (RU and EN).

Notation: **PS** — PowerShell on Windows, **sh** — a Linux shell (Orange Pi, WSL). Git
commands are the same in both except for quoting (section "The `git land` alias").

## Git: working without pull requests

A branch `<agent>/<task>` is created from a fresh main and, after the checks, merged
into main by fast-forward. This is a temporary order until the first release, while
branches serve as experiments and intermediate steps; it is revised when the release
is prepared. The GitHub web interface cannot merge without a pull
request, and GitHub's automatic branch deletion works for pull requests only, so
merging and cleanup are done locally.

```
git switch main
git pull --ff-only
git switch -c claude/<task>            # new branch
# … commits …
git push -u origin claude/<task>       # CI: wait for green Docs and Offline
git land claude/<task>                 # fast-forward main, push, delete the branch
```

A fast-forward creates no merge commit: main receives the same signed commits, and
GitHub shows them as Verified. If the branch is behind main, `git land` stops at
`--ff-only` without changing anything. Then rebase the branch onto a fresh main and
sign it again:

```
git switch claude/<task>
git rebase -S origin/main              # conflicts: fix, git add, git rebase --continue
git push --force-with-lease            # only for your own unmerged branch
```

Force pushes to main and to other people's branches are not allowed.

### The `git land` alias

Install it with single quotes: inside double quotes PowerShell substitutes `$` itself,
and `\"` does not escape a quote.

```powershell
git config --global --unset-all alias.land   # if it existed; "no such section" is harmless
git config --global alias.land '!f() { b=${1:-$(git branch --show-current)}; git fetch origin && git switch main && git merge --ff-only origin/main && git merge --ff-only $b && git push --atomic origin main :$b && git branch -d $b; }; f'
git config --global --get-all alias.land     # exactly one line with b=${1:-$(git branch --show-current)}
```

The same command works unchanged in sh. `git land <branch>` does: `fetch` →
fast-forward main to `origin/main` → fast-forward main to the branch → one atomic push
that updates main and deletes the branch on GitHub → deletes the local branch.

| Problem | Solution |
| --- | --- |
| `syntax error: unexpected end of file`, the error shows `b=;` | The alias was written in double quotes from PowerShell. Remove it (`--unset-all`) and write it again in single quotes |
| `warning: alias.land has multiple values` | `git config --global --unset-all alias.land`, then write it again; or `git config --global --edit` and delete extra `land = …` lines |
| `fatal: Not possible to fast-forward` | The branch is behind main: `git rebase -S origin/main` (above) |
| Push rejected: protected branch, pull request required | In Settings → Rules remove the pull request requirement for main or allow yourself to bypass it |

Undo: remove the alias with `git config --global --unset-all alias.land`.

### Cleaning up branches

```
git fetch --prune                                  # drop references to branches deleted on GitHub
git branch -r --merged origin/main                 # merged branches on GitHub
git push origin --delete <branch> [<branch> …]     # delete on GitHub
git branch -vv                                     # local branches; [gone] — no longer on GitHub
git branch -d <branch>                             # delete a merged local branch
git branch -D <branch>                             # delete when the hash differs but the content is in main
```

On another computer (Orange Pi) after a merge:

```sh
git switch main && git pull --ff-only && git branch -D <branch> && git fetch --prune
```

### Returning to a previous state

| Situation | Command |
| --- | --- |
| Discard uncommitted changes in files | `git restore <file>` or `git restore .` |
| Unstage a file, keeping the changes | `git restore --staged <file>` |
| Remove untracked files | first `git clean -n` (what would go), then `git clean -f`; `*.local.toml` files are ignored and stay unless `-x` is used — do not use `-x` |
| Undo the last unpushed commit, keeping the changes | `git reset --soft HEAD~1` |
| Local main is broken but not pushed yet | `git switch main && git reset --hard origin/main` |
| A branch was deleted by mistake | `git reflog` → find the hash → `git branch <branch> <hash>`; restore on GitHub with `git push origin <branch>` |
| Undo a commit already pushed to main | `git revert <hash>` as a new signed commit, then the usual cycle; do not rewrite main history |
| Abort a failed rebase or merge | `git rebase --abort` / `git merge --abort` |

### Signing and Verified

```
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519_signing.pub
git config --global commit.gpgsign true
git log --show-signature -1            # check the signature of the last commit
```

The key is added in GitHub as a **Signing Key** (separately from the Authentication
Key), and the author email must be a verified address of the account. Unverified means
the commit is unsigned, signed with another key, or the email does not match. Fix
unpushed commits with `git commit --amend -S --no-edit` (the last one) or
`git rebase -S origin/main` (all commits of the branch). Undo:
`git config --global --unset commit.gpgsign`.

### Line endings and service files

- On Windows `core.autocrlf=true`: CRLF in the working copy, LF in the repository.
  `ci/**`, `.github/**` and `*.sh` are always LF (`.gitattributes`).
- All files show as modified without real edits — line endings: check `git diff --stat`
  with `-c core.autocrlf=true`; after editing `.gitattributes` run
  `git add --renormalize .`.
- `fatal: Unable to create '…/.git/index.lock': File exists` — make sure git is not
  running (IDE, another terminal), then delete `.git/index.lock`.

## Linux stand and Orange Pi

Details: [Linux stand](LINUX_STAND.md).

| Problem | Solution |
| --- | --- |
| `ModuleNotFoundError: No module named 'tomllib'` or "needs Python 3.11+" | The system Python 3.8 was used. In every new shell: `. ~/.local/stm32-gdbtest/env.sh`, check `python3 --version` → 3.11.16 |
| Not sure everything is installed and accessible | `python3 -B -m stm32_gdbtest doctor [--stand <stand>]` |
| `FAIL usb … no read/write access` | udev rules (section "USB access" in [Linux stand](LINUX_STAND.md)), reconnect the debugger |
| `FAIL openocd … interface/stlink.cfg` | OpenOCD 0.10 from apt was found: run `env.sh` so that xPack OpenOCD comes first on `PATH` |
| J-Link STLink (Nucleo): `GDB server startup timed out`, `jlink.log` shows about 10 s to connect | The J-Link STLink terms window waits for confirmation. Once, in a graphical session (monitor or remote desktop): `JLinkExe -USB <serial>`, `connect`, tick the checkbox. Fallback: `startup_timeout_s = 30` in the stand |
| A download failed while installing the environment | Run `python3 tools/linux_stand.py install` again: installed parts are skipped, downloads restart |
| Reinstall one component | `rm -rf ~/.local/stm32-gdbtest/<component directory>` and `python3 tools/linux_stand.py install --only <name>` |

Return the system to its original state:

```sh
rm -rf ~/.local/stm32-gdbtest                     # the whole stand environment
sudo rm /etc/udev/rules.d/60-openocd.rules        # ST-Link udev rules
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo dpkg -r jlink                                # J-Link software
rm -rf /tmp/stm32-gdbtest-locks                   # only when no runner is active
```

## Hardware runs

| Message | What to do |
| --- | --- |
| `Debugger already owned by another runner …` | The debugger is busy with another run (another project, CTest, a second terminal). Wait for it to finish; do not use one debugger in parallel |
| `Abandoned debugger ownership …` | The previous runner crashed. Check and stop leftover servers, then run again (see below) |
| `GDB server exited before ready; see server.log` | Open `server.log` of the run directory: wrong serial, debugger used by another program, no USB access |
| `GDB server startup timed out after N s` | The server did not become ready. Check `server.log` and the server's log; give a slow debugger `startup_timeout_s` in the stand |
| Warning `Flash capacity differs … image fits both` | The factory Flash size is larger than the profile (BluePill-Plus 128 KiB); the run continues |
| After an experiment the board has other firmware or an 0xA5 tail | `run_hw.py … --steps build full-ff` programs the CI firmware with an 0xFF tail |

Leftover server processes:

```sh
pgrep -a openocd; pgrep -a JLink                  # Linux
kill <pid>                                        # then kill -9 <pid> if it does not exit
```

```powershell
Get-Process openocd, JLinkGDBServerCL, ST-LINK_gdbserver, arm-none-eabi-gdb* -ErrorAction SilentlyContinue
Stop-Process -Id <pid>
```

The run directory is printed in the final `run` line and in `summary.json` of
`run_hw.py`. It holds `result.json`, `server.log`, `gdb.log`, `recovery.log`, the server
logs and, for a remote stand, `tunnel.log` ([API](API.md), [checks and CI](testing.md)).

## Remote GDB server over SSH

Setup: [Linux stand](LINUX_STAND.md#remote-gdb-server-windows-or-wsl--orange-pi). Check the
connection manually with the same key options the runner uses:

```powershell
ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes -i <key> orangepi@<host> "python3 --version"
```

| Message | What to do |
| --- | --- |
| `Permission denied (publickey…)` in `tunnel.log` | The key is not in `~/.ssh/authorized_keys` on the stand host or another `identity_file` is set; a key with a passphrase works only through `ssh-agent` |
| `Host key verification failed` | The host key is not in `known_hosts` or has changed (OS reinstall): run `ssh orangepi@<host> exit` once; for a changed key first `ssh-keygen -R <host>` |
| `Stand host refused the run: busy …` | The debugger on the stand host is busy: another run from Windows or a local run on the Orange Pi |
| `Stand host refused the run: abandoned …` | A previous run on the stand host crashed: on the Orange Pi `pgrep -a openocd; pgrep -a JLink`, stop leftovers, retry |
| `Stand host refused the run: executable …` | The server is not found on the stand host: check the `executable` path, for OpenOCD that `~/.local/stm32-gdbtest/env.sh` exists or set `env_script` |
| `GDB server exited before ready; see server.log and tunnel.log (env_script …)` | Code 97: the given `env_script` could not be sourced; code 255: an SSH error (key, host, network) |
| `Stand host refused the run: port …` | The randomly picked server port on the stand host is busy: run again |
| `GDB server startup timed out after N s` for a remote stand | The limit is `startup_timeout_s` + 10 s for SSH; check `server.log` and `tunnel.log` |
| `Passwords are not supported in [remote]` | Passwords are not allowed in the stand: set up key login |

Undo: remove the `[remote]` table from the stand (or the stand file), remove the key
from `~/.ssh/authorized_keys` on the stand host, and the host entry with
`ssh-keygen -R <host>`.

## Docker and CI

| Problem | Solution |
| --- | --- |
| Docker Hub is unreachable while building the image | `docker build --build-arg BASE_IMAGE=<mirror>/ubuntu:24.04 …` ([checks and CI](testing.md)) |
| Files in `build/` are owned by root after a container run on Linux | Run with `--user "$(id -u):$(id -g)" -e HOME=/tmp`; remove old ones: `sudo rm -rf build Tests/firmware/build` |
| CI is red but everything passes locally | Match the checked commit with the branch's latest commit; open the `offline-results` or `linux-stand-*` artifact |

Remove the image and cache: `docker image rm stm32-gdbtest-ci:local`, `docker builder prune`.

## For agents

- An agent in a cloud copy without GitHub access hands commits to the owner through a
  `git bundle` in `build/` of the owner's working copy (writing into `.git` is not
  allowed); there run `git fetch <bundle> <branch>:refs/agent/tmp`, `git cherry-pick -S`
  of the new commits and `git update-ref -d refs/agent/tmp`. The bundle starts from a
  commit the owner has (for example `origin/main`).
- An agent does not push, tag or store passwords; SSH to stands uses keys only.
