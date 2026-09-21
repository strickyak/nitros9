# Bug Report: Missing Path Number in `AllcPDsc` Causes `E$BPNum` on File Operations (`ioman.asm`)

## Summary

In NitrOS-9 Level 1 (`level1/modules/ioman.asm`), the path descriptor allocation subroutine `AllcPDsc` called `os9 F$All64` to allocate a 64-byte path descriptor block, but neglected to store the returned path number into `PD.PD,y` (offset 0). Subsequent path validation routines in `S2UPath` checked `PD.PD` and failed with `E$BPNum` (Error 205, "Bad Path Number"), breaking filesystem and device access.

## Affected Component

- **File**: [`level1/modules/ioman.asm`](file:///home/strick/modoc/coco-shelf/nitros9/level1/modules/ioman.asm)
- **Subroutine**: `AllcPDsc`
- **Architecture**: OS-9 Level 1 (6809 / 6309)

## Root Cause Analysis

When a file or device is opened (`I$Open`, `I$Create`), `IOMan` invokes `AllcPDsc` to allocate a system path descriptor:

```assembly
AllcPDsc            ldx       <D.Proc   ; get pointer to curr proc in X
                    pshs      u,x       ; save U/X
                    ldx       <D.PthDBT ; get ptr to path desc base table
                    os9       F$All64   ; allocate 64 byte page
                    bcs       AllocPathReturn ; branch if error
                    inc       PD.CNT,y  ; set path count
                    stb       PD.MOD,y  ; save mode byte
```

`F$All64`:
- Allocates a 64-byte block in `D.PthDBT`.
- Zeroes the entire 64-byte memory area.
- Returns the allocated 64-byte block index (1, 2, 3...) in **`A`**.
- Returns the pointer to the descriptor block in **`Y`**.

In OS-9 path descriptors, offset 0 is `PD.PD`, which must hold the descriptor's own path number.

Notice that `AllcPDsc` incremented `PD.CNT,y` and stored mode `PD.MOD,y`, but **never saved register `A` into `PD.PD,y`**. As a result, `PD.PD` remained `$00`.

### Consequence in Path Validation (`S2UPath`):
Whenever a user process later passed its path number to an I/O system call (`I$Read`, `I$Write`, `I$GetStt`, `I$SetStt`, `I$Close`, `I$ChgDir`), the I/O manager called `S2UPath` to convert and validate the user path against the descriptor:
- `S2UPath` obtains the path descriptor pointer from the process's `P$Path` table.
- It compares the requested path number against `PD.PD,y`.
- Because `PD.PD,y` contained `$00` instead of the allocated path number, the comparison failed and `S2UPath` returned `E$BPNum` ($CD = 205: "Bad Path Number").

## Symptoms & Impact

- Directory changes (`I$ChgDir`) and file opens (`I$Open`) failed immediately or on subsequent reads/writes with error 205 (`ERROR #205`).
- Any attempt by `krnp2` or `SysGo` to open `/DD` or `/Term` could not validate paths.

## Required Patch

Store the allocated path number in `A` into `PD.PD,y` immediately following `os9 F$All64`:

```diff
--- a/level1/modules/ioman.asm
+++ b/level1/modules/ioman.asm
@@ -1080,6 +1080,7 @@ AllcPDsc            ldx       <D.Proc   ; get pointer to curr proc in X
                     ldx       <D.PthDBT ; get ptr to path desc base table
                     os9       F$All64   ; allocate 64 byte page
                     bcs       AllocPathReturn ; branch if error
+                    sta       PD.PD,y   ; set path number in descriptor
                     inc       PD.CNT,y  ; set path count
                     stb       PD.MOD,y  ; save mode byte
                   IFGT    Level-1
```

## Verification

With `sta PD.PD,y` in place, all allocated path descriptors have their matching path numbers recorded in `PD.PD`. `S2UPath` correctly validates user paths against `P$Path`, allowing directory navigation (`dir`, `pwd`, `pxd`), file creation, reading, and writing to function properly.
