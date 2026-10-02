# HOWTO: common commands and problems

[Documentation](index.md) → HOWTO · [Русский](../ru/HOWTO.md)

Developers and agents look here when something does not work, before searching for a
new solution. Each problem lists how to fix it and how to return to the previous
state. Project rules are in [maintenance](maintenance.md); this page has the commands.
A new solution to a common problem is added here in the same commit (RU and EN).

Notation: **PS** — PowerShell on Windows, **sh** — a Linux shell (Orange Pi, WSL). Git
commands are the same in both except for quoting (section "The `git land` alias").

## Git: working without pull requests

### Local SSH signature verification

The `gpg.ssh.allowedSignersFile needs to be configured` error from `git verify-commit`
does not mean the signature is missing: Git needs trusted public keys. Create a
local untracked file (for example under `build/`) containing
`<email> namespaces="git" ssh-ed25519 <public-key>` from a previously verified
public Signing Key. Then run:

```text
git -c gpg.ssh.allowedSignersFile=build/allowed-signers verify-commit HEAD
```

The setting applies only to this command; no rollback is needed. Do not commit keys
or the local list. Success verifies against the selected key, not its GitHub
registration or the server's Verified status.

### Work sequence

A branch `<agent>/<task>` is created from a fresh main and, after the checks, merged
into main by fast-forward. This order applies to one maintainer working with agents and is reconsidered when the team grows. The GitHub web interface cannot merge without a pull
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
| A download failed while installing the environment (e.g. HTTP 500 from GitHub) | The script itself retries downloads and `git fetch` up to 4 times with 15, 30, 60 s pauses; if that fails, run `python3 tools/linux_stand.py install` again: installed parts are skipped. In CI re-run the failed job (Re-run failed jobs); downloads are cached |
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

## Prepared run packages and hardware CI

Details: [hardware CI](HARDWARE_CI.md).

| Message | What to do |
| --- | --- |
| `Preparation failed, package not written: …` | A scenario's preparation gave ERROR: run `run --prepare-only` for it and read `result.json` |
| `Package file changed: …`, `Package contents do not match its manifest` | The package is damaged or changed after `pack`: create it again, do not edit the zip by hand |
| `The Tests directory must be inside the profile directory` | The scenario directory is outside the profile: move it or pack from the profile |
| A scenario on the stand cannot find a helper module | Add it when packing: `pack … --include helpers` |
| The `hardware` job does not start | The runner is offline or lacks the `stm32-stand` label: Settings → Actions → Runners |

Undo: delete `build/ddtt-packages` and `build/packages`; for the runner see "Installing the
runner" in [hardware CI](HARDWARE_CI.md).

## Docker and CI

| Problem | Solution |
| --- | --- |
| Docker Hub is unreachable while building the image | `docker build --build-arg BASE_IMAGE=<mirror>/ubuntu:24.04 …` ([checks and CI](testing.md)) |
| Files in `build/` are owned by root after a container run on Linux | Run with `--user "$(id -u):$(id -g)" -e HOME=/tmp`; remove old ones: `sudo rm -rf build tests/firmware/build` |
| CI is red but everything passes locally | Match the checked commit with the branch's latest commit; open the `offline-results` or `linux-stand-*` artifact |

Remove the image and cache: `docker image rm stm32-gdbtest-ci:local`, `docker builder prune`.

## For agents

- An agent in a cloud copy without GitHub access hands commits to the owner through a
  `git bundle` in `build/` of the owner's working copy (writing into `.git` is not
  allowed); there run `git fetch <bundle> <branch>:refs/agent/tmp`, `git cherry-pick -S`
  of the new commits and `git update-ref -d refs/agent/tmp`. The bundle starts from a
  commit the owner has (for example `origin/main`).
- An agent does not push, tag or store passwords; SSH to stands uses keys only.

## Do not compare reserved MMIO bits

F030 ADC CFGR2 read 0x1000 with CKMODE=0 in this experiment. Check the documented field `ADC1->CFGR2 & ADC_CFGR2_CKMODE`, not the whole register. Verify masks against the selected MCU header/RM; do not mask unexpected results without analysis. [Report](F030_CMSIS_ADC_DMA.md).

Owned profiles/examples and new packages use `tests`; old `Tests` inputs remain supported. Local remote stands use ignored `remote.toml` / `<profile>-remote.toml`. Reconfigure after renaming. [Conventions](maintenance.md).

## Standalone fixture build

For “Output directories must remain inside the selected project root”, place
build inside the fixture (tests/hal-f030/build/debug), not the module-wide build
directory. Fix preset binaryDir rather than disabling runner containment checks.

## CMake cache when switching Windows and Linux

Do not reuse one build alternately from Windows and a Linux container: CMakeCache
stores absolute paths. “Current CMakeCache.txt directory is different” occurs before
firmware validation and does not establish a firmware defect. Preserve the failed
report and old build under another name inside the workspace, then create a clean
build for the current OS. tests/hal-f030 CI uses build/ci-gcc13; preserve that exact
directory, not the Git checkout or the whole hardware evidence directory.
If the HAL rerun succeeds, report two runs rather than a single 15/15 PASS.

## Do not mix prepare and hardware reports from one session

### Selecting another GDB version


CLI `run --gdb` selects GDB for --package. With --session, GDB comes from the
session's gdb field. Compare versions using local session copies with separate gdb
and out fields and the same ELF/manifest, or pass `-DSTM32_GDBTEST_GDB=<path>` at
CMake configure time. Keep global PATH unchanged for an isolated experiment.
Verify gdb_version in result.json; use the original session to restore the previous
GDB. See the [comparison example](RC3_API_R1.md).

### Separating reports

CTest prepare and CLI run write result.json to session.out. Run them serially
or use separate sessions/out directories. Counting every new result.json without
a mode/id filter can misattribute prepare output to a hardware scenario. Preserve
the evidence and repeat the complete set separately; do not claim a complete PASS.

## Reports from repeated package runs

If summary references missing JSON from earlier runs, check the module version: the old open_package deleted the previous extraction directory. The fixed version keeps separate sessions; update artifact collection patterns as described in [Hardware CI](HARDWARE_CI.md). A green workflow does not replace inspection of retained results.

## Same Cube package name, different RCC signatures

Do not select HAL contracts by Windows/Linux or CubeF0 V1.11.6 directory name.
The [F030 investigation](F030_HAL_GPIO_RCC.md) found mutable/const differences
between the installed package and CI gitlink. Use reviewed source hashes and
strict ELF types. Unknown hashes need review, not disabled preflight.
Do not reuse a CMake cache containing /workspace paths on Windows: use a separate
build/copy. WinError5 creating a restore report is not an MCU failure: retain
ERROR, resolve access and confirm boot/blink separately.

## Windows tests directory casing

If the physical Windows directory is still named Tests, adding a new directory
with `git add tests/<directory>` may skip files. Add explicit lowercase file paths
(`git -c core.ignorecase=false add -- tests/<directory>/<file>`) and inspect `git diff --cached --name-only`.
Do not introduce a second Tests root into the index. A new consumer must exclude
its build/ directory using a local .gitignore.

## Watchpoint installed but GDB does not report its number

On the tested F411/OpenOCD0.12.0 ST-Link HLA connection, the server sent T05 without
watch/rwatch/awatch addresses. Do not treat any stop as watchpoint success.
Keep RSP/server logs and inspect the interface driver. In the [R2 experiment](RC3_API_R2.md),
native stlink-dap/dapdirect_swd resolved this on the same stand. The --native-stlink
flag exists only in the consumer runner; the production module and installed
OpenOCD remain unchanged. Omit the flag to revert. This is not a universal
recommendation to switch drivers on other stands.

## Watch does not stop on a same-value store

`watch` reports value changes, not every store. In [R3](RC3_API_R3.md), the CPU
stored the previous checksum: write-watch continued to the sentinel while
access-watch stopped. `awatch` also catches reads: inspect the instruction and
context to prove a write. An application counter with a watch predicate bounds
progress but cannot replace the external host timeout when execution hangs.

## Repeated stepi in an infinite loop: target not halted

In [R4](RC3_API_R4.md), F411/OpenOCD native DAP completed `jump` and the first
`stepi` in a Thumb self-loop; the next step reported `target not halted` and hit
the external timeout. Preserve the ERROR and logs; verify host recovery/restore.
HLA passed4/4 with the same ELF. This is a limited comparison, not an established
root cause: native DAP watchpoint support does not prove reliable stepping.
Do not hide the error by increasing the timeout or unconditionally retrying.
