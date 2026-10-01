# R1 consumer experiment requirements

## HW_R1_VALUES
Typed initialized structure, integer/float/enum/array and bounded string; reject expressions, invalid indices and absent symbols.

## HW_R1_FRAMES
Natural nested calls, arguments and materialized backtrace; reject stale frame after resume.

## HW_R1_RAM
Bounded consumer-owned RAM reads and patches, canaries, rollback on success/body exception, reject invalid ranges before access.

## HW_R1_STOPS
Function/address/source locations, duplicate PC, external point preservation, fault guards and actual location budget.

## HW_R1_RECORD
Bounded immutable JSON evidence, duplicate/oversize/nonserializable input, namespace isolation.

## HW_R1_CONTROL
Independent arithmetic oracle and monotonic completed cycle on the normal application path.
