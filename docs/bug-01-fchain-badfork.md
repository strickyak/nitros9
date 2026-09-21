# Bug Report: `F$Chain` Always Fails with `E$IForkP` Due to Missing Branch in `SetupPrc`

## Summary

In NitrOS-9 Level 1, the `F$Chain` system call (`level1/modules/kernel/fchain.asm`) failed unconditionally with error 218 (`E$IForkP`, "Illegal Fork Parameter"), even when all parameters, module headers, and memory allocations were completely valid.

## Affected Component

- **File**: [`level1/modules/kernel/fchain.asm`](file:///home/strick/modoc/coco-shelf/nitros9/level1/modules/kernel/fchain.asm)
- **Subroutine**: `SetupPrc` / `setregs@`
- **Architecture**: OS-9 Level 1 (6809 / 6309)

## Root Cause Analysis

When a process executes `os9 F$Chain`, the kernel unlinks the existing module, allocates memory for the new module, copies parameters, and prepares the caller's stack frame in `SetupPrc`.

In the `setregs@` label of `SetupPrc`, the kernel completes register setup:
```assembly
setregs@            ldx       <D.Proc   ; get pointer to current process descriptor
                    leau      d,u       ; point U to that
                    stu       R$PC,y    ; put that offset in the caller's PC
                    clrb                ; B = 0
badfork@            ldb       #E$IForkP ; illegal fork parameter
ex@                 puls      pc,u,x    ; return to caller
```

Notice that after `clrb` (clearing error code in B to indicate success), there was **no branch to `ex@`**.

Execution fell straight through into `badfork@`, which immediately executed:
```assembly
badfork@            ldb       #E$IForkP ; illegal fork parameter ($DA = 218)
```

Because `B` was overwritten with `E$IForkP`, the routine returned with `B != 0` and carry flag set, aborting the chain and causing `F$Chain` to fail 100% of the time.

## Symptoms & Impact

- Any call to `F$Chain` immediately aborted with error 218 (`ERROR #218`).
- Process chaining was completely non-functional in Level 1.
- Initial boot chaining (e.g., kernel chaining to `Shell` or `SysGo`) failed or panicked.

## Required Patch

```diff
--- a/level1/modules/kernel/fchain.asm
+++ b/level1/modules/kernel/fchain.asm
@@ -124,5 +124,6 @@ setregs@            ldx       <D.Proc   ; get pointer to current process descrip
                     leau      d,u       ; point U to that
                     stu       R$PC,y    ; put that offset in the caller's PC
                     clrb                ; B = 0
+                    bra       ex@       ; branch to success return
 badfork@            ldb       #E$IForkP ; illegal fork parameter
 ex@                 puls      pc,u,x    ; return to caller
```

## Verification

After applying `bra ex@`, `F$Chain` returned with carry clear and `B = 0`. Chained executions in Level 1 (such as `SysGo` chaining or user command chaining) succeeded without generating `E$IForkP`.
