# Bug Report: `SFChain` Bypasses User State Transition, Leaving Chained Process in `SysState`

## Summary

In NitrOS-9 Level 1, invoking `F$Chain` from system state via the `SFChain` entry point (`level1/modules/kernel/fchain.asm`) branched directly to rescheduling without clearing the `SysState` flag in the process descriptor. As a result, user processes launched from system state (such as the initial `Shell` or `SysGo` at boot) ran in system state rather than user state, corrupting standard I/O path resolution.

## Affected Component

- **File**: [`level1/modules/kernel/fchain.asm`](file:///home/strick/modoc/coco-shelf/nitros9/level1/modules/kernel/fchain.asm)
- **Subroutine**: `SFChain` / `FChain`
- **Architecture**: OS-9 Level 1 (6809 / 6309)

## Root Cause Analysis

In OS-9 Level 1, `F$Chain` provides two entry points:
1. `FChain`: For calls initiated by user processes.
2. `SFChain`: For calls initiated by system processes (such as `krnp2` during cold boot).

The original code was structured as follows:
```assembly
* F$Chain user state entry point.
FChain              bsr       DoChain   ; do the F$Chain
                    bcs       chainerr@ ; branch if error
                    orcc      #IntMasks ; mask interrupts
                    ldb       P$State,x ; get process state
                    andb      #^SysState ; clear system state
                    stb       P$State,x ; save back to process descriptor
resched@            ldu       <P$PModul,x ; get pointer to the module for the current process
                    os9       F$Unlink  ; unlink it
                    os9       F$AProc   ; add it to active process queue
                    os9       F$NProc   ; activate it
* F$Chain system state entry point.
SFChain             bsr       DoChain   ; do the F$Chain
                    bcc       resched@  ; branch if OK
chainerr@           pshs      b         ; save off B for now
```

When called via `SFChain`:
1. `bsr DoChain` executes successfully.
2. If carry is clear, `bcc resched@` jumped **past** the `andb #^SysState` sequence directly to `resched@`.
3. The process retained `SysState` set in `P$State,x`.

### Consequence in I/O Dispatch:
In NitrOS-9 Level 1, the I/O manager inspects `P$State`:
- **User Processes (`SysState == 0`)**: `UsrIODis` translates path numbers 0, 1, 2 (stdin, stdout, stderr) by indexing into the process descriptor's private path table (`P$Path,u`).
- **System Processes (`SysState != 0`)**: `SysIODis` treats the path number as an index into the global system path table (`D.PthDBT`), completely bypassing `P$Path`.

Because the chained user program ran with `SysState != 0`, reading from path 0 or writing to path 1/2 attempted to look up system paths 0, 1, and 2 instead of the process's inherited terminal paths, breaking interactive I/O.

## Symptoms & Impact

- The initial program booted by the kernel (`Shell` or `SysGo`) failed to perform standard I/O correctly.
- Calls to `I$ReadLn` on stdin (path 0) or `I$WritLn` on stdout/stderr (paths 1 and 2) failed with `E$BPNum` ("Bad Path Number") because system paths 0, 1, and 2 were not valid open system descriptors.

## Required Patch

Unify `SFChain` with `FChain` so that every chained process transitions to user state (`andb #^SysState`) before rescheduling:

```diff
--- a/level1/modules/kernel/fchain.asm
+++ b/level1/modules/kernel/fchain.asm
@@ -27,7 +27,9 @@
                   IFEQ    Level-1 ; begin conditional assembly for Level-1
 
 * F$Chain user state entry point.
-FChain              bsr       DoChain   ; do the F$Chain
+FChain
+* F$Chain system state entry point.
+SFChain             bsr       DoChain   ; do the F$Chain
                     bcs       chainerr@ ; branch if error
                     orcc      #IntMasks ; mask interrupts
                     ldb       P$State,x ; get process state
@@ -37,9 +39,6 @@ resched@            ldu       <P$PModul,x ; get pointer to the module for the cu
                     os9       F$Unlink  ; unlink it
                     os9       F$AProc   ; add it to active process queue
                     os9       F$NProc   ; activate it
-* F$Chain system state entry point.
-SFChain             bsr       DoChain   ; do the F$Chain
-                    bcc       resched@  ; branch if OK
 chainerr@           pshs      b         ; save off B for now
                     stb       <P$Signal,x ; save off error code
                     ldb       P$State,x ; get process state
```

## Verification

With this change, `krnp2` chaining to `SysGo` or `Shell` correctly switches the process from system state to user state. Standard I/O paths 0, 1, and 2 resolve through `P$Path` as expected, enabling terminal prompts and command input.
