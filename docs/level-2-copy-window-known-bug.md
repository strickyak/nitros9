# NitrOS-9 Level 2 Copy Window Collision Bug

## 1. Executive Summary

This document details the known NitrOS-9 Level 2 kernel bug where **insufficient total size of primordial/preloaded modules** causes dynamic system memory allocations (`F$SRqMem`) to encroach into the kernel's inter-task transfer window (**MMU Slots 5 and 6**, `$A000..$DFFF`).

When process descriptors—which house both the process descriptor data structure and the process's **system stack**—are allocated inside this address range, routines that transfer data between user and system space ([`CpSysStkTo`](file:///home/strick/modoc/coco-shelf/nitros9/level2/modules/kernel/krn.asm#L1089), [`CpUsrStkTo`](file:///home/strick/modoc/coco-shelf/nitros9/level2/modules/kernel/krn.asm#L1079), and [`F$Move`](file:///home/strick/modoc/coco-shelf/nitros9/level2/modules/kernel/fmove.asm#L34)) temporarily remap MMU registers `$FFA5` and `$FFA6`. 

This unmaps the active process descriptor and/or system stack while the CPU is actively accessing them, causing:
1. Register stack corruption during task dispatch (saving frames to one physical block, reading frames from another, or reading all zeroes).
2. Spurious jumps to `PC=$0000` on `RTI`, leading to zero-byte instruction execution crashes (`NEG <$00`...) and stray I/O reads.
3. System DAT image (`D.SysDAT`) corruption when [`F$SRtMem`](file:///home/strick/modoc/coco-shelf/nitros9/level1/modules/kernel/fsrqmem.asm#L257) deallocates Slot 6, and [`F$AllImg`](file:///home/strick/modoc/coco-shelf/nitros9/level2/modules/kernel/fallimg.asm#L14) later reallocates it to arbitrary physical blocks (such as user RAM block 0).

---

## 2. Architectural Background

### 2.1 64 KB Memory Slot Layout (Task 0 / System Space)

In NitrOS-9 Level 2 on a 6809/6309 CPU with an 8-slot MMU (8 KB per slot):

| Slot | Logical Address Range | Purpose in System Task (Task 0) | MMU Register |
|---|---|---|---|
| **0** | `$0000..$1FFF` | Direct Page, System Globals (`D.*`), System Stack, Process 1 Descriptor (`$0600`) | `$FFA0` |
| **1** | `$2000..$3FFF` | Primordial Modules (Kernel P2, Init, IOMan, RBF...) | `$FFA1` |
| **2** | `$4000..$5FFF` | Primordial Modules | `$FFA2` |
| **3** | `$6000..$7FFF` | Primordial Modules | `$FFA3` |
| **4** | `$8000..$9FFF` | Primordial Modules / Free System RAM | `$FFA4` |
| **5** | `$A000..$BFFF` | **Transfer Window (Part 1)** — Temporary map slot | `$FFA5` |
| **6** | `$C000..$DFFF` | **Transfer Window (Part 2)** — Temporary map slot | `$FFA6` |
| **7** | `$E000..$FFFF` | Kernel Part 1 (`$EE00..$FEFF`), Vectors, Hardware I/O (`$FFxx`) | `$FFA7` |

### 2.2 Role of Slots 5 & 6 as Transfer Windows

Because the 6809 cannot simultaneously address more than 64 KB, copying data between two tasks (or between user space and system space) requires mapping the target task's memory into Task 0's address space.

The Level 2 kernel designates **Slot 5 (`$A000..$BFFF`)** and **Slot 6 (`$C000..$DFFF`)** as a 16 KB transfer window via MMU registers `$FFA5` and `$FFA6`:
- [`CpSysStkTo`](file:///home/strick/modoc/coco-shelf/nitros9/level2/modules/kernel/krn.asm#L1089) and [`CpUsrStkTo`](file:///home/strick/modoc/coco-shelf/nitros9/level2/modules/kernel/krn.asm#L1079): Write to `DAT.Regs+5` (`$FFA5` and `$FFA6`) to map the user process's stack block into Slot 5 and the adjacent block into Slot 6.
- [`F$Move`](file:///home/strick/modoc/coco-shelf/nitros9/level2/modules/kernel/fmove.asm#L34): Maps source and destination blocks into Slots 5 and 6 to copy chunks between memory spaces.

---

## 3. Detailed Failure Sequence

### Step 1: Primordial Modules Are Too Small
In `deep65280.img`, the 19 primordial modules occupy only up to `$7960` (Slots 1, 2, and 3). 
At boot initialization in [`krn.asm`](file:///home/strick/modoc/coco-shelf/nitros9/level2/modules/kernel/krn.asm#L700-L715):
- Pages `$20..$7F` (Slots 1..3) are marked as `RAMinUse` in `D.SysMem`.
- Pages `$80..$ED` (Slots 4, 5, and 6) are left marked as **free (0)** for dynamic kernel allocations (`F$SRqMem`).
- Pages `$EE..$FF` (Slot 7) are marked as `RAMinUse` (Kernel and I/O).

### Step 2: System Allocations Grow Downward into Slot 6
[`F$SRqMem`](file:///home/strick/modoc/coco-shelf/nitros9/level1/modules/kernel/fsrqmem.asm#L180) searches the system memory map (`D.SysMem`) from the highest free page **downward**:
- When processes 2, 3, 4, 5, and 6 are created, [`F$AllPrc`](file:///home/strick/modoc/coco-shelf/nitros9/level2/modules/kernel/fallprc.asm#L34) calls `F$SRqMem` to allocate a 512-byte (2-page) process descriptor (`P$Size`).
- Under sufficient load, descriptors land in pages `$DE..$DF` (logical address `$DE00..$DFFF`), which is inside **MMU Slot 6**.
- The second page of each descriptor (`$DF00..$DFFF`) serves as the process's **system stack** (`S = $DFxx`).

### Step 3: `F$SRtMem` Erroneously Deallocates Slot 6
When a process exits and returns memory via [`F$SRtMem`](file:///home/strick/modoc/coco-shelf/nitros9/level1/modules/kernel/fsrqmem.asm#L257):
1. `F$SRtMem` clears the pages in `D.SysMem`.
2. It then iterates through all 8 slots in `D.SysDAT`.
3. If all 32 pages (8 KB) of a slot in `D.SysMem` are currently 0, `F$SRtMem` assumes the slot is no longer needed by the kernel:
   ```assembly
   clr d,u        ; clear physical block in D.BlkMap (e.g. block $3E)
   ldd #DAT.Free  ; $333E
   std ,x         ; store DAT.Free into D.SysDAT for Slot 6
   ```
4. Physical block `$3E` is now freed, and Slot 6 in `D.SysDAT` becomes `$333E`.

### Step 4: `F$AllImg` Reallocates Slot 6 to User RAM (Block 0)
When another process (e.g., PID 6) is subsequently created:
1. `F$AllPrc` calls `F$SRqMem` for its descriptor.
2. `F$SRqMem` selects pages in Slot 6 (`$DE..$DF`).
3. Seeing that Slot 6 in `D.SysDAT` is `DAT.Free`, it invokes [`F$AllImg`](file:///home/strick/modoc/coco-shelf/nitros9/level2/modules/kernel/fallimg.asm#L14) to allocate an 8 KB block.
4. `F$AllImg` grabs the first free physical block in `D.BlkMap`, which is **physical block 0**!
5. Slot 6 of `D.SysDAT` is now set to `00`.
6. Whenever Task 0's MMU registers are restored from `D.SysDAT` (e.g., in `FMoveSystemDAT`), **`$FFA6` is written with `00`**.

### Step 5: Collision During Dispatch ([`CpSysStkTo`](file:///home/strick/modoc/coco-shelf/nitros9/level2/modules/kernel/krn.asm#L1089))
When dispatching PID 6:
```assembly
CpSysStkTo:
    ...
    std   >DAT.Regs+5 ; maps user task stack block into Slot 5 ($FFA5) 
                      ; AND adjacent user block into Slot 6 ($FFA6)
l@  ldu   ,x++        ; X = $DFF4 (source register frame in proc descriptor)
    stu   ,y++        ; Y = $A5F3 (destination user stack in Slot 5)
```
1. Before `std >DAT.Regs+5`, `X = $DFF4` resides in Slot 6.
2. `std >DAT.Regs+5` **overwrites Slot 6** with the user task's memory!
3. `ldu ,x++` does NOT read the process descriptor. It reads whatever data (or zeroes) exists in the foreign user page mapped into Slot 6.
4. Furthermore, because of Step 4, `KrnSave` had previously written the frame into physical block 0, whereas the restore path was reading physical block `$3E`.
5. The user stack receives `CC=$00`, `PC=$0000`.
6. At `PC=$FE45`, `RTI` pulls `PC=$0000` and dispatches into address `0000`.
7. The CPU executes uninitialized zero bytes (`00 00` = `NEG <$00`) until it reaches `$FFB4`, triggering an unmapped I/O panic.

---

## 4. Historical Precedents in NitrOS-9 Codebase

This vulnerability is documented in comments left by previous NitrOS-9 maintainers:

### From [`level2/modules/kernel/fmove.asm`](file:///home/strick/modoc/coco-shelf/nitros9/level2/modules/kernel/fmove.asm#L18-L22):
```assembly
* 2009/12/31 - Modified 6809 version so that it does not use the stack
* while MMU is in used... this addresses a crash that occurred when the
* bootfile was too small, causing the process descriptor to be allocated
* in the $AXXX range, and as a result, the process stack pointer would get
* switched out when $FFA5-$FFA6 was written and the stack would disappear.
```

### From [`level2/modules/kernel/krn.asm`](file:///home/strick/modoc/coco-shelf/nitros9/level2/modules/kernel/krn.asm#L608-L624) (Wildbits port):
```assembly
* Reserve MMU slot 2 ($4000-$5FFF, pages $40-$5F) in the system page map.
* The wildbits device drivers use slot 2 as their temporary map window for
* VKY, flash and RAM-disk blocks (IRQs masked, slot saved and restored
* around each window). F$SRqMem allocates system pages from the top of the
* map DOWNWARD, so under enough load (about 17 pages in use) it grew the
* system map into this slot and process descriptors - whose second page is
* the process's SYSTEM STACK - landed inside the window. A driver's pushes
* and pulls while a VKY or flash block was mapped then hit that block instead
* of the stack: the slot was restored with junk, live descriptors vanished
* and the CPU wandered...
* Marking these 32 pages used keeps the kernel out of slot 2 for good, at
* the cost of 8K of system RAM; the system DAT image entry for slot 2 stays
* free, so the drivers' window never aliases live kernel memory.
```

---

## 5. Potential Solutions

### Strategy 1: Workaround (Protect Slots 5 and 6 in `D.SysMem`)
Similar to the Wildbits port's reservation of Slot 2:
1. **Mark Slots 5 and 6 as Used at Boot:**
   In [`krn.asm`](file:///home/strick/modoc/coco-shelf/nitros9/level2/modules/kernel/krn.asm#L700), mark pages `$A0..$DF` (64 pages = 16 KB) in `D.SysMem` as `RAMinUse` (or a dedicated reserved marker).
   ```assembly
   ldx   <D.SysMem
   leax  $A0,x       ; start of Slot 5
   ldb   #64         ; 64 pages (Slots 5 and 6)
   lda   #RAMinUse
rsv@
   sta   ,x+
   decb
   bne   rsv@
   ```
2. **Result:**
   `F$SRqMem` will never allocate system pages or process descriptors in `$A000..$DFFF`. Descriptors and system stacks will remain safely in Slots 3, 4, or lower, preventing them from ever colliding with the transfer window.
3. **Pad Primordial Modules:**
   Alternatively, add pre-allocated buffer modules or padding in `build_img.py` so that Slots 1 through 6 are fully occupied by statically mapped system modules, ensuring dynamic allocation occurs only in a designated safe area.

### Strategy 2: True Architectural Fix (Hard)
1. **Redesign `CpSysStkTo` and `CpUsrStkTo`:**
   Instead of mapping user stacks into Task 0's Slots 5 & 6, copy the frame through an intermediate buffer in the direct page or low memory (Slot 0), or use an MMU task-to-task copy mechanism if supported by hardware.
2. **Audit and Lock `D.SysDAT`:**
   Prevent `F$SRtMem` from freeing system slots that are statically bound to the system architecture.
3. **Handle Process Descriptor Stack Off-Slot:**
   Relocate process descriptor system stacks to a dedicated non-reprogrammable slot.
