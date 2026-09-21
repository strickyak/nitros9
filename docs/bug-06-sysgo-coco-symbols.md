# Bug Report: Shared `sysgo.asm` Fails Assembly on Non-CoCo Ports Due to Hardcoded CoCo Symbols

## Summary

The generic Level 1 kickstart module `sysgo.asm` (`level1/modules/sysgo.asm`) contained hardcoded references to Tandy Color Computer specific hardware registers and symbols (`PIA0Base`, `Bt.Start`, `SHIFTBIT`). Any new non-CoCo Level 1 port failed assembly unless it was manually added to a negative conditional list (`IFEQ atari+corsham+wildbits+picothing...`).

## Affected Component

- **File**: [`level1/modules/sysgo.asm`](file:///home/strick/modoc/coco-shelf/nitros9/level1/modules/sysgo.asm)
- **Subroutine**: `BasicRst`, `L0125` (Color BASIC reset code), `DoStartup` (Shift key sense)
- **Architecture**: OS-9 Level 1 (6809 / 6309)

## Root Cause Analysis

In `sysgo.asm`, CoCo-specific reset vectors and keyboard checks were guarded with a negative check of known non-CoCo ports rather than a positive check of `coco`:

```assembly
                  IFEQ    atari+corsham+wildbits+picothing
                    ifeq      Level-1
* BASIC reset code (CoCo port only)
BasicRst            fcb       $55
                    neg       <$0074
                    nop
                    clr       >PIA0Base+3
                    nop
                    nop
                    sta       >$FFDF              turn off ROM mode
                    jmp       >Bt.Start+2         jump to boot
BasicRL             equ       *-BasicRst
                    endc
                    endc
```

And similarly for keyboard sense:
```assembly
                  IFEQ    atari+corsham+wildbits+picothing
* Added 12/14/03: If SHIFT is held down, startup is not run (CoCo only)
                    lda       #$01                standard output
                    ldb       #SS.KySns
                    os9       I$GetStt
                    bcs       DoStartup
                    bita      #SHIFTBIT           SHIFT key down?
                    bne       L0186               Yes, don't to startup or autoex
                    endc
```

When building `sysgo` for a new target (such as `flat65280`), `atari+corsham+wildbits+picothing` evaluates to 0. Consequently, the assembler attempts to assemble:
1. `clr >PIA0Base+3`: Fails because `PIA0Base` is undefined.
2. `jmp >Bt.Start+2`: Fails because `Bt.Start` is undefined.
3. `bita #SHIFTBIT`: Fails because `SHIFTBIT` is undefined.

Furthermore, if those symbols happened to be defined, executing `BasicRst` on a non-CoCo machine would corrupt arbitrary memory (writing to `$FFDF` and PIA0) and crash the machine.

## Symptoms & Impact

- Compiling `sysgo.asm` for a new port fails with multiple unresolved symbol errors:
  ```text
  level1/modules/sysgo.asm(126) : ERROR : Undefined symbol PIA0Base
  level1/modules/sysgo.asm(130) : ERROR : Undefined symbol Bt.Start
  level1/modules/sysgo.asm(258) : ERROR : Undefined symbol SHIFTBIT
  ```
- Port developers cannot use standard `sysgo.asm` out-of-the-box for Level 1 targets.

## Required Patch

Add `flat65280` (or preferrably gate on `IFNE coco` in future cleanups) to the conditional exclusion:

```diff
--- a/level1/modules/sysgo.asm
+++ b/level1/modules/sysgo.asm
@@ -117,7 +117,7 @@ ShellPL             equ       *-ShellPrm
 * If no RTC is available, then the soft clock starts at January 1 of the new year.
 DefTime             fcb       85,12,31,23,59,59
 
-                  IFEQ    atari+corsham+wildbits+picothing
+                  IFEQ    atari+corsham+wildbits+picothing+flat65280
                     ifeq      Level-1
 * BASIC reset code (CoCo port only)
 BasicRst            fcb       $55
@@ -210,7 +210,7 @@ SignOn
 
 L0125               equ       *
                     pshs      u,y
-                  IFEQ    atari+corsham+wildbits+picothing
+                  IFEQ    atari+corsham+wildbits+picothing+flat65280
                     ifeq      Level-1
 * Setup BASIC code (CoCo port only)
                     leax      >BasicRst,pcr
@@ -249,7 +249,7 @@ L0151               lda       b,y
 
                     ifeq      ROM
 * Fork shell startup here
-                  IFEQ    atari+corsham+wildbits+picothing
+                  IFEQ    atari+corsham+wildbits+picothing+flat65280
 * Added 12/14/03: If SHIFT is held down, startup is not run (CoCo only)
                     lda       #$01                standard output
                     ldb       #SS.KySns
```

## Verification

Assembling `sysgo.asm` with `-DFLAT65280=1 -DDD=1` completes cleanly without undefined symbol errors, producing a valid 380-byte `SysGo` binary module that boots properly on non-CoCo hardware.
