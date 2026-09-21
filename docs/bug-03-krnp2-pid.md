# Bug Report: Process 1 PID Uninitialized in Root Process Descriptor (`krnp2.asm`)

## Summary

In NitrOS-9 Level 1 (`level1/modules/kernel/krnp2.asm`), the root process initialization routine allocated the process descriptor for Process 1 but never stored the returned process ID into `P$ID,y`. Because `F$All64` zeroes allocated blocks, Process 1 ran with `P$ID = 0` rather than `P$ID = 1`, corrupting the process hierarchy and system accounting.

## Affected Component

- **File**: [`level1/modules/kernel/krnp2.asm`](file:///home/strick/modoc/coco-shelf/nitros9/level1/modules/kernel/krnp2.asm)
- **Subroutine**: `start` (Root Process Setup)
- **Architecture**: OS-9 Level 1 (6809 / 6309)

## Root Cause Analysis

During cold boot in `krnp2.asm`, the kernel creates the initial process descriptor by calling `os9 F$All64`:

```assembly
start               equ       *         ; define assembler symbol
* Install system calls.
                    leay      SvcTbl,pcr ; point to the system call table
                    os9       F$SSvc    ; install the system calls
* Allocate a process descriptor for the initial process.
                    ldx       <D.PrcDBT ; get process descriptor table in X
                    os9       F$All64   ; allocate a new 64 byte page
                    bcs       FatalErr  ; failed to allocate
                    stx       <D.PrcDBT ; save off
                    sty       <D.Proc   ; save off new process descriptor pointer
```

According to OS-9 specifications, `F$All64`:
- Allocates a 64-byte block from the table pointed to by `X` (`D.PrcDBT`).
- Zeroes out the 64-byte memory area.
- Returns the allocated entry/block number in **`A`** (which corresponds to Process ID 1).
- Returns the address of the descriptor in **`Y`**.

Notice that `krnp2.asm` stored `D.PrcDBT` and `D.Proc`, but **never saved register `A` into `P$ID,y`** (`P$ID` is offset 0 in the process descriptor).

Because `F$All64` zeroes the block, `P$ID` remained `$00`.

### Consequence:
In OS-9, Process ID 0 is strictly reserved for the system / idle process (`SysPrc`). User processes must have non-zero PIDs starting at 1. Having the initial process report PID 0 caused:
1. `os9 F$ID` returned `A = 0`.
2. `procs` utility reported PID 0 for the root shell/sysgo.
3. Child process fork and wait accounting (`P$PID`, `P$CID`) was corrupted because child processes saw parent PID 0.

## Symptoms & Impact

- The initial process (Process 1) reported PID 0.
- Running `procs` showed `Usr # id pty state mem primary module` with `id 0` instead of `id 1`.
- Process tracking and signal routing between parent and child processes malfunctioned.

## Required Patch

Store register `A` (returned by `F$All64`) into `P$ID,y` immediately upon allocation:

```diff
--- a/level1/modules/kernel/krnp2.asm
+++ b/level1/modules/kernel/krnp2.asm
@@ -69,6 +69,7 @@ start               equ       *         ; define assembler symbol
                     ldx       <D.PrcDBT ; get process descriptor table in X
                     os9       F$All64   ; allocate a new 64 byte page
                     bcs       FatalErr  ; failed to allocate
+                    sta       P$ID,y    ; set process ID (1)
                     stx       <D.PrcDBT ; save off
                     sty       <D.Proc   ; save off new process descriptor pointer
```

## Verification

After applying the fix, running `procs` in `gep9` confirms Process 1 has PID 1:
```text
OS9:procs

Usr #  id pty  state   mem primary module
----- --- --- -------- --- --------------
    0   2 128  active    3 Shell <Term
    0   1 128  waiting   1 SysGo <Term
```
`SysGo` is properly registered as PID 1, and child processes (such as `Shell`) receive PID 2.
