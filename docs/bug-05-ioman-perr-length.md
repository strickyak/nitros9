# Bug Report: Missing Buffer Length in `F$PErr` Silences Error Messages (`ioman.asm`)

## Summary

In NitrOS-9 Level 1 (`level1/modules/ioman.asm`), the error printing subroutine `FPErr` / `MoveErrorToProcess` invoked `os9 I$WritLn` to write formatted error strings (`"ERROR #nnn\r"`) to the standard error path without setting register `Y` (maximum byte count). Because `Y` was 0 (or left with arbitrary values from previous routines), `I$WritLn` wrote zero bytes, completely silencing error message output.

## Affected Component

- **File**: [`level1/modules/ioman.asm`](file:///home/strick/modoc/coco-shelf/nitros9/level1/modules/ioman.asm)
- **Subroutine**: `FPErr` / `MoveErrorToProcess`
- **Architecture**: OS-9 Level 1 (6809 / 6309)

## Root Cause Analysis

When a program or shell calls `os9 F$PErr` to display a decimal error message, `FPErr` in `IOMan` builds the message buffer on the stack:
- Copies `"ERROR #"` header.
- Converts the error number in `B` to 3 ASCII digits.
- Appends carriage return (`C$CR`).
- Total message length is defined by `ErrMessL` (`equ *-ErrHead`, typically 12 bytes).

In Level 1, `MoveErrorToProcess` sends the message to standard error:
```assembly
MoveErrorToProcess  os9       F$Move    ; copy error message into process' buffer
* 6809/6309 - This ldx is useless - X is immediately reloaded, and U gets D.Proc
*         ldx   <D.Proc        Get process descriptor
                    leax      ,s        ; point to error message
                    ldu       <D.Proc   ; get ptr to process descriptor
                    lda       <P$Path+2,u ; get Error path #
                    os9       I$WritLn  ; write message
```

According to the OS-9 Level 1 specification for `I$WritLn`:
- **`A`**: Path number
- **`X`**: Buffer address
- **`Y`**: Maximum number of bytes to write

Notice that `MoveErrorToProcess` loaded `X` (`leax ,s`) and `A` (`lda <P$Path+2,u`), but **never loaded `Y`**.

Earlier instructions in `FPErr` (such as decimal conversion loops) zeroed or corrupted `Y`. When `Y` entered `I$WritLn` as `$0000`, the SCF manager interpreted this as a request to write a maximum of 0 bytes. `I$WritLn` returned immediately without writing any characters.

## Symptoms & Impact

- The shell and utilities produced no visible error output when a command failed.
- Typing a non-existent command name at the `OS9:` prompt printed a blank line instead of `ERROR #216`.
- Diagnostic output was suppressed across the entire operating system for any utility relying on `F$PErr`.

## Required Patch

Load `Y` with `#ErrMessL` prior to invoking `os9 I$WritLn`:

```diff
--- a/level1/modules/ioman.asm
+++ b/level1/modules/ioman.asm
@@ -2065,6 +2065,7 @@ MoveErrorToProcess  os9       F$Move    ; copy error message into process' buffe
 * 6809/6309 - This ldx is useless - X is immediately reloaded, and U gets D.Proc
 *         ldx   <D.Proc        Get process descriptor
                     leax      ,s        ; point to error message
+                    ldy       #ErrMessL ; get length of text
                     ldu       <D.Proc   ; get ptr to process descriptor
                     lda       <P$Path+2,u ; get Error path #
                     os9       I$WritLn  ; write message
```

## Verification

After applying `ldy #ErrMessL`, entering an unknown command in the interactive shell immediately prints the expected OS-9 error string to stderr:
```text
OS9:nonexistentcommand
ERROR #216
```
Error reporting behaves according to standard OS-9 specifications.
