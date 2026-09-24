"""Flash load sections, independent of GDB; BIN gaps are not ELF payload."""
import re


def validate_regions(regions, flash_start, flash_size, image_size=None):
    if not regions:
        raise ValueError("ELF has no Flash load sections")
    end = flash_start
    for region in regions:
        address, size, offset = (region[k] for k in ("address", "size", "offset"))
        if any(type(v) is not int for v in (address, size, offset)):
            raise ValueError("Invalid load section numeric field")
        if size <= 0 or address < flash_start or address + size > flash_start + flash_size:
            raise ValueError("Load section outside profile Flash")
        if offset != address - flash_start or address < end:
            raise ValueError("Overlapping, unsorted or inconsistent load sections")
        end = address + size
    if regions[0]["address"] != flash_start:
        raise ValueError("First load section must start at profile flash_start")
    span = end - flash_start
    if image_size is not None and image_size != span:
        raise ValueError("BIN extent differs from ELF load sections")
    return span


def parse_sections(text, flash_start, flash_size):
    """Parse GNU objdump -h, selecting CONTENTS+ALLOC+LOAD by LMA, not VMA."""
    regions = []
    lines = text.splitlines()
    header = re.compile(r"^\s*\d+\s+(\S+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+"
                        r"([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+2\*\*\d+\s*$")
    for i, line in enumerate(lines):
        if not re.match(r"^\s*\d+\s+", line):
            continue
        match = header.fullmatch(line)
        if match is None or i + 1 >= len(lines):
            raise ValueError("Malformed objdump section header")
        flags_line = lines[i + 1].strip()
        if not re.fullmatch(r"[A-Z_]+(?:,\s*[A-Z_]+)*", flags_line):
            raise ValueError("Malformed objdump section flags")
        flags = {f.strip() for f in flags_line.split(",")}
        if not {"CONTENTS", "ALLOC", "LOAD"} <= flags:
            continue
        name, size, vma, lma, file_offset = match.groups()
        size, address = int(size, 16), int(lma, 16)
        if size:  # Empty sections do not program bytes.
            regions.append(dict(name=name, address=address, size=size, offset=address - flash_start))
    regions.sort(key=lambda r: r["address"])
    validate_regions(regions, flash_start, flash_size)
    return regions


def compare_regions(read_memory, image, regions, flash_start, flash_size):
    """Read only validated ELF payload, in bounded chunks; propagate read errors."""
    validate_regions(regions, flash_start, flash_size, len(image))
    results = []
    for region in regions:
        matches = True
        for offset in range(0, region["size"], 4096):
            size = min(4096, region["size"] - offset)
            actual = bytes(read_memory(region["address"] + offset, size))
            if len(actual) != size:
                raise RuntimeError("Short Flash read")
            start = region["offset"] + offset
            if actual != image[start:start + size]:
                matches = False
        results.append(dict(region, matches=matches))
    return results
