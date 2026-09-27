# ELF, BIN and the Flash verification scope

[Documentation](index.md) → Images and CRC · [Русский](../ru/IMAGES.md)

The runner verifies the contents of the **loadable ELF sections** at their load
addresses (LMA). This matches a regular GDB `load`: the `.data` VMA is in RAM while
its initial values are loaded into Flash — the Flash LMA is what gets compared.
Sections without the CONTENTS, ALLOC, LOAD flags (such as `.bss` and debug
information) and empty sections are not compared.

## Load-section mode (default)

Before the server, GNU `arm-none-eabi-objdump -h` from the GDB directory produces the
section list. ERROR before `objcopy`, GDB and the server results from: an empty or
unparsable list, overlaps, unsorted sections, loading outside the profile Flash and a
first section that does not start at `flash_start`. Offset applications and multiple
banks are not supported. After connecting, the factory Flash size is checked; a
larger MCU does not widen the profile bounds ([identity](TARGET_IDENTITY.md)).

The BIN is built with `objcopy -O binary --gap-fill=0xFF` **from the selected
sections only** (`-j` for each); its length must equal the extent of the sections.
Previously an empty section with a RAM address (for example an empty `.data`)
stretched the BIN to hundreds of MiB — now it is left out.

The 0xFF fill defines the gap bytes **in the BIN**, but a GDB `load` of the ELF does
not program them: on the board they may be erased or left from earlier firmware. That
is why the section comparison skips the gaps. A mismatch triggers programming with
`flash = if-different`, followed by a mandatory readback of the same sections; with
`verify-only` a mismatch gives ERROR without programming. A read error is never a
reason to program and is never hidden. Reads use blocks of up to 4096 bytes.

`result.json` and JUnit keep `image_verification`:

- `scope: elf-load-sections`, `bin_gap_fill: 255`;
- `gaps_verified: false`, `full_region_crc_verified: false`;
- `regions`: name, Flash address, size, BIN offset and, after readback, `matches`.

`image_verified: true` means all these sections match — not the whole Flash and not
a full-image CRC. `elf-sections.txt` and `image.bin` are kept in the run directory.

## Full image and CRC (explicit mode)

For a full range pass `run --image-policy path/to/full-image.toml` or an absolute
path in `STM32_GDBTEST_IMAGE_POLICY` (handy for CTest); the CLI wins. If the variable
is set, omitting the flag does **not** disable full mode — remove the variable to go
back to the section check.

```toml
[image]
schema = 1
mode = "full"
start = 0x08000000
end = 0x08004000
fill = 255
crc = "crc32-iso-hdlc"
```

The example describes **16 KiB**, not the whole MCU Flash; `end` is exclusive. The
start must equal the profile `flash_start`, the end must fit the profile and the
factory size read from the MCU. If the ELF grows beyond the policy, the run is
refused. Numbers are integers (not bool), `fill` is 0…255; unknown fields, schemas
and CRC algorithms are rejected. An MCU with another Flash base needs its own file;
the policy is kept by the consumer, independent of the stand.

Preparation before the server:

1. The source ELF, build manifest and load sections are checked.
2. `image.bin` is created: section bytes are kept, gaps and the tail up to `end` are
   filled with `fill`. No CRC field is inserted into the firmware.
3. `program.elf` is created from the BIN with a single `.firmware` section at
   `start`; its bounds and a byte-exact round trip back to the BIN are checked. It is
   a transport container for GDB, not a new build.
4. SHA-256 of the BIN, the container and the source policy are recorded; the agent
   checks them and the padding before connecting.

`run --prepare-only` with a policy performs these steps without hardware and leaves
`image.bin` and `program.elf` in the run directory.

After reset/halt the agent reads the **whole** range in blocks of up to 4096 bytes,
compares every byte with the BIN and computes the CRC of the expected and the read
image. On a mismatch with `if-different` it runs `load program.elf`, restores
`symbol-file firmware.elf` and repeats the full readback. `verify-only` gives ERROR
without programming; a read error is ERROR too, never a reason to program blindly. If
everything matches, nothing is programmed. Then the regular scenario, reset/run and
backend recovery rules follow.

No mass erase is performed. The backend may erase sectors or pages while programming;
data outside the range is not guaranteed to survive. In a real project reserve the
firmware region according to the erase geometry; in the verified F030/F103/F411
examples the 16 KiB boundary matches it. Multiple banks, offset applications and
preservation of neighbouring data are not implemented.

### CRC contract

CRC-32/ISO-HDLC: polynomial `0x04C11DB7`, init/xorout `0xFFFFFFFF`, refin/refout —
true; ASCII `123456789` gives `0xCBF43926`
([RevEng CRC catalogue](https://reveng.sourceforge.io/crc-catalogue/all.htm)).
Bytes are fed in ascending Flash address order, an odd-length tail byte by byte,
without hidden word padding. There is no CRC field: every byte of the range counts.
If the application stores a CRC inside the image, that CRC is part of the calculation too.

The CRC is computed with `binascii.crc32` on the host, inside the GDB agent, over data
read through the debugger. **This does not run CRC code on the MCU and does not test
its CRC peripheral.** A matching CRC does not replace the byte comparison: both
conditions are required.

`image_verification` in full mode: `scope: full-image`, `start`, `end`, `fill`,
`bytes_compared`, `bytes_match`, `first_mismatch` (address or `null`),
`gaps_verified`, `full_region_crc_verified`, CRC parameters and `expected`/`observed`.
`image_before_programming` is saved before programming. `bin_sha256` refers to the
full BIN, `elf_sha256` to the source ELF, `program_elf_sha256` to the container;
`image_policy.source_sha256` links the report to the TOML, and the normalized copy is
`image-policy.json`. The CRC is not a cryptographic check.

### One artifact for programming and debugging

`image.bin` can be written with an external programmer **at the `start` address**,
and `program.elf` loaded under the debugger: their payload is identical. In a
connected GDB after reset/halt:

```gdb
load /path/to/run/program.elf
symbol-file /path/to/run/firmware.elf
```

Then reset/halt and run according to the backend rules. Use both files from the same
run directory and check the manifest, SHA and readback. In VS Code the source ELF
stays the symbol file while the load command points to the container; the consumer's
`launch.json` is not changed automatically. A plain `load firmware.elf` again leaves
the gaps and tail outside the explicit contract. `load` may affect symbol tables, so
they are restored explicitly ([GDB Target Commands](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Target-Commands.html)).

## Verified scope and limits

Full mode is verified on hardware through OpenOCD, J-Link GDB Server and ST-LINK GDB
Server ([status](STATUS.md)). The container is built with `objcopy` for
`elf32-littlearm`; this does not extend RISC-V support. Further topics: a CRC field
and exclusions, other algorithms, comparison with the MCU CRC peripheral.

Reasons for the changes and hardware evidence are in the
[stand project](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill) (Russian):
docs/ELF_LOAD_REGIONS.md, docs/FULL_IMAGE_CRC.md, docs/K1921VG015_POC.md. The RISC-V
experiment motivated the section-based check but does not extend MCU or toolchain support.
