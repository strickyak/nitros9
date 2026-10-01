# NP Language & NPCode Virtual Machine Specification

**Version:** 0.3  
**Date:** October 2026  
**Document:** `npcode/design.md`  
**Source Language:** NP (`*.np`)  
**Bytecode Target:** NPCode (`*.npc`)  
**Virtual Machine Interpreter:** `npcode`  

---

## 1. Introduction & Design Philosophy

The **NP** language and **NPCode** Virtual Machine provide a compact, deterministic, and easily portable programming environment tailored for 8-bit and 16-bit architectures—specifically Motorola 6809 and Hitachi 6309 systems running NitrOS-9 Level 1 and Level 2, as well as embedded microcontrollers (such as the RP2350 on the TFR911h board) and Unix host systems.

The primary motivating workload is the native self-generation and source transformation pipeline for NitrOS-9 (e.g. [`recipes/deep65280/selfgen_preprocess.py`](file:///home/strick/modoc/coco-shelf/nitros9/recipes/deep65280/selfgen_preprocess.py)), which translates modern assembly source into native assembler dialects.

### 1.1 Core Directives: Strongly-Typed, Untagged Words, 1-Byte Opcodes

NP and NPCode are fundamentally designed around static typing and raw 16-bit words:

1. **Strongly-Typed (A Go-Like Machine, Not Python)**:
   - NP is a **statically, strongly-typed language**. Every variable, function parameter, return value, struct field, and collection element type is checked and known at compile time.
   - The VM does **not** perform dynamic type checking or inspect runtime type tags.
   - A 16-bit word on the operand stack represents an `int16_t`, a `uint16_t`, or a pointer to a `List`, `Dict`, `String`, or `Struct`.
   - In the rare case that 32-bit functionality is needed (e.g. for filesystem size or sector APIs), the program codes it explicitly using two `uint16_t` variables in the host language rather than introducing a 32-bit VM type.
   - When looking up an element in a dictionary (`DICT_GET`), the VM extracts a raw 16-bit word. The compiler and generated code already know whether that word is an integer, boolean, or a pointer to a specific structure or list.
2. **Simplified Nil: No Nil Object**:
   - Pointers to `Dict`, `List`, `String`, or `Struct` can be `$0000`, which is a **nil pointer** (`NULL`).
   - There is **no nil object** on the heap. Nil is literally the numeric 16-bit zero word `$0000`.
3. **Simplified Booleans & The Zero-Test `if`**:
   - For Booleans: `$0000` is `false`. Anything else (`!= $0000`) is `true`.
   - The canonical Boolean constant `true` is `$0001`.
   - The `if` construct (and `while`, `JUMP_IF_FALSE`, `JUMP_IF_TRUE`) simply tests whether a 16-bit word is `$0000` (false / nil / zero) or non-zero (true / valid pointer / non-zero integer). This single instruction uniformly handles boolean checks, null pointer tests, and integer zero tests without special cases.
4. **Strict 1-Byte Opcodes**:
   - Every opcode is exactly 1 byte (`0x00` .. `0xFF`).
   - The opcode itself completely defines how many argument bytes follow it in the instruction stream (0, 1, or 2 bytes) and what format they take.
   - There are **no argument type tags** in the bytecode stream.
5. **Zero-Byte Arguments for Frequent Operations**:
   - Frequent instructions require **0 argument bytes**: `PUSH_NIL`, `RET`, `RET_VOID`, `PUSH_0`, `PUSH_1`, `PUSH_TRUE`, `PUSH_FALSE`, `ADD`, `SUB`, `DUP`, `POP`, and fast local accesses (`LOAD_LOCAL_0` .. `LOAD_LOCAL_3`).
6. **Elimination of Complex Runtime Features**:
   - **No Closures**: Functions are static; stateful callbacks receive an explicit context pointer.
   - **No Exceptions**: Replaced with multi-value status returns (`val, ok = parse_int(s)`).
   - **No RAII / Context Managers**: Explicit `f = open(...); ...; f.close()`.
   - **No Lookaround Regex**: Replaced with a fast, dedicated word-boundary replacer opcode (`STR_REPLACE_IDENT`).

---

## 2. The NP Source Language (`*.np`)

NP features a Go-inspired, statically typed syntax with explicit error handling and built-in text processing primitives.

### 2.1 Types
- **`int` / `int16`**: 16-bit signed integer ($-32,768 \dots +32,767$).
- **`uint` / `uint16`**: 16-bit unsigned integer ($0 \dots 65,535$).
- **`bool`**: Boolean value (`false` = `$0000`, `true` = `$0001`).
- **`str`**: Pointer to immutable sequence of bytes. Slices produce lightweight views (`string_view`) referencing parent memory without allocation.
- **`List[T]`**: Dynamic array of 16-bit values of type `T`. Pointers can be `$0000` (`nil`).
- **`Dict[str, T]`**: Hash table mapping string pointers to 16-bit values of type `T`. Pointers can be `$0000` (`nil`).
- **`Set[str]`**: Hash set of unique string pointers.
- **`struct Name { ... }`**: Named record with fixed-offset 16-bit fields.
- **`file`**: System I/O file path descriptor (0..255).

### 2.2 Control Flow & Truthiness
- **Uniform Zero-Test**:
  In NP, the `if` and `while` statements test whether the expression evaluates to non-zero:
  ```python
  if ptr:          # true if ptr != nil ($0000)
      ...
  if ok:           # true if ok != false ($0000)
      ...
  if count:        # true if count != 0 ($0000)
      ...
  ```
- **Function Definitions**:
  ```python
  fn split_asm_line(line: str) -> (str, str):
      let s: str = line.rstrip("\r\n")
      let s_strip: str = s.lstrip("")
      if s == "" or s_strip.startswith("*") or s_strip.startswith(";"):
          return ("", line)
      # ...
      return (code_part, comment_part)
  ```
- **Error Handling by Convention (No Exceptions)**:
  Functions that can fail return an explicit status Boolean:
  ```python
  let val: int, ok: bool = parse_int(count, 0)
  if ok:
      # use numeric count
  else:
      # handle symbolic count
  ```

---

## 3. NPCode Virtual Machine Architecture

NPCode is a **stack-based virtual machine** with explicit operand and call stacks.

```mermaid
flowchart TD
    subgraph VMRegisters ["Virtual Machine Registers"]
        PC["PC: Program Counter (16-bit)"]
        SP["SP: Operand Stack Pointer (16-bit, register U)"]
        FP["FP: Frame Pointer (16-bit, register Y)"]
        CP["CP: Constant String Pool Base (16-bit)"]
        HP["HP: Heap / Arena Base Pointer (16-bit)"]
    end

    subgraph StackLayout ["Untagged 16-Bit Word Operand Stack (Register U)"]
        S0["Top of Stack: 16-bit Word (uint16_t / int16_t / ptr)"]
        S1["Stack Slot 1:  16-bit Word (uint16_t / int16_t / ptr)"]
        S2["Stack Slot 2:  16-bit Word (uint16_t / int16_t / ptr)"]
    end

    subgraph MemoryModel ["Process Memory (64 KB)"]
        Hdr["NPC Header (16 bytes)"]
        SPool["Raw String Pool (Consecutive text bytes, no tags)"]
        Globals["Global Variables (16-bit word slots)"]
        Code["Bytecode Stream: [1-byte opcode][0, 1, or 2 arg bytes]"]
        Heap["Dynamic Heap / Line Arena"]
    end

    VMRegisters --> StackLayout
    VMRegisters --> MemoryModel
```

### 3.1 Untagged 16-Bit Word Operand Stack
Every slot on the operand stack is a uniform **16-bit word (`uint16_t`)**.
- **No type tags on the stack**. The static typing of the language guarantees that the instruction stream operates on the correct type.
- On a 6809 CPU, the user stack pointer `U` is used directly as `SP`:
  - Push 16-bit word in `D`: `pshu d` (2 bytes, 5 cycles).
  - Pop 16-bit word into `D`: `pulu d` (2 bytes, 5 cycles).
  - Peek top of stack: `ldd ,u`.

### 3.2 Elimination of 32-Bit Types
To keep the virtual machine minimal, fast, and simple on 8-bit CPUs like the 6809:
- There are no 32-bit integer types (`int32`, `uint32`) or 32-bit math opcodes in the VM.
- In the rare instances where 32-bit arithmetic or offsets are needed (such as file positions or sector numbers in OS-9 filesystem APIs), the source code represents and manipulates them explicitly as two 16-bit variables (`hi: uint16, lo: uint16`) in the host language.

### 3.3 Call Frame Structure (Call Stack)
The hardware stack `S` (or dedicated call stack) tracks function activation:
1. `Return PC` (16 bits): Where execution resumes upon `RET`.
2. `Old FP` (16 bits): Saved caller frame pointer.
3. `Arg Count` (8 bits): Number of arguments passed.

Function parameters and local variables are indexed relative to `FP` (`Y` register):
- `FP[0] .. FP[N-1]`: Parameters (pushed by caller).
- `FP[N] .. FP[N+M-1]`: Local variables (initialized to `$0000`).

---

## 4. Binary File Format (`*.npc`)

NPCode binary files are compiled bytecode executables. Multi-byte integers are stored in **Big-Endian** format (matching 6809/6309 native order).

### 4.1 File Layout

```text
+-----------------------------------------------------------+
| 1. Header (16 bytes)                                      |
+-----------------------------------------------------------+
| 2. String Pool (Raw bytes, length-prefixed, no tags)       |
+-----------------------------------------------------------+
| 3. Function Table (ArgCount, LocalCount, EntryOffset)     |
+-----------------------------------------------------------+
| 4. Bytecode Section: Pure stream of opcodes and args       |
+-----------------------------------------------------------+
```

### 4.2 Header Specification (16 Bytes)

| Offset | Size | Field Name | Description |
| :--- | :--- | :--- | :--- |
| `0x00` | 4 | `Magic` | Byte sequence `0x4E 0x50 0x43 0x01` (`"NPC\x01"`) |
| `0x04` | 1 | `FormatVer` | Format version (currently `1`) |
| `0x05` | 1 | `Flags` | Execution flags (Bit 0 = 6309 native, Bit 1 = MMU banked) |
| `0x06` | 2 | `StringPoolSize` | Total byte size of the raw String Pool section |
| `0x08` | 2 | `GlobalsCount`| Number of 16-bit global variable slots to reserve |
| `0x0A` | 2 | `FuncCount` | Number of functions in the Function Table |
| `0x0C` | 2 | `EntryFunc` | Function index of the entry point (`main`) |
| `0x0E` | 2 | `CodeSize` | Total byte size of the Bytecode Section |

### 4.3 String Pool (No Type Tags)
- Contains all string literals from the source program packed contiguously.
- Each string is stored as:
  - `Length` (16-bit big-endian unsigned integer).
  - `Bytes` (`Length` bytes of UTF-8 / ASCII data).
  - `0x00` (null-terminator byte for zero-copy OS-9 system call interoperability).
- Any string constant in the code is referenced by its 16-bit byte offset from the start of the String Pool via `PUSH_STR <offset16>`.

---

## 5. Instruction Set Architecture (ISA)

Every instruction starts with a **1-byte opcode**. The opcode explicitly defines whether it takes **0, 1, or 2 argument bytes**. There are no dynamic type tags in the bytecode stream.

### 5.1 Immediate Argument Encoding Formats
- **None (0 bytes)**: Opcode is completely standalone.
- **`<imm8>` (1 byte)**: 8-bit immediate value (slot index, small integer, or width).
- **`<imm16>` (2 bytes)**: 16-bit big-endian immediate value (string offset, global slot, capacity, function index).
- **`<rel16>` (2 bytes)**: 16-bit big-endian signed relative branch offset.

---

### 5.2 Complete Opcode Table

#### Group 1: Stack & Literals (`0x00 .. 0x1F`)

| Opcode | Mnemonic | Arg Bytes | Operand Format | Stack Effect | Description |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `0x00` | `NOP` | **0** | None | `[] -> []` | No operation. |
| `0x01` | `PUSH_NIL` | **0** | None | `[] -> [$0000]` | Push `nil` pointer / zero word (`$0000`). |
| `0x02` | `PUSH_TRUE` | **0** | None | `[] -> [$0001]` | Push canonical Boolean `true` (`$0001`). |
| `0x03` | `PUSH_FALSE` | **0** | None | `[] -> [$0000]` | Push Boolean `false` (`$0000`). |
| `0x04` | `PUSH_0` | **0** | None | `[] -> [$0000]` | Fast push of integer 0 (`$0000`). |
| `0x05` | `PUSH_1` | **0** | None | `[] -> [$0001]` | Fast push of integer 1 (`$0001`). |
| `0x06` | `PUSH_NEG1` | **0** | None | `[] -> [$FFFF]` | Fast push of integer -1 (`$FFFF`). |
| `0x07` | `PUSH_I8` | **1** | `<imm8>` | `[] -> [val]` | Push sign-extended 8-bit integer (-128..127). |
| `0x08` | `PUSH_U8` | **1** | `<imm8>` | `[] -> [val]` | Push zero-extended 8-bit unsigned integer (0..255). |
| `0x09` | `PUSH_I16` | **2** | `<imm16>` | `[] -> [val]` | Push 16-bit big-endian integer. |
| `0x0A` | `PUSH_STR` | **2** | `<imm16>` | `[] -> [str_ptr]`| Push pointer to string in String Pool at offset. |
| `0x0B` | `POP` | **0** | None | `[a] -> []` | Discard top 16-bit word from stack. |
| `0x0C` | `DUP` | **0** | None | `[a] -> [a, a]` | Duplicate top 16-bit word. |
| `0x0D` | `SWAP` | **0** | None | `[a, b] -> [b, a]`| Swap top two 16-bit words. |

#### Group 2: Variables & Structs (`0x20 .. 0x3F`)

| Opcode | Mnemonic | Arg Bytes | Operand Format | Stack Effect | Description |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `0x20` | `LOAD_LOCAL_0` | **0** | None | `[] -> [val]` | Fast load 16-bit word from local slot 0 (`FP[0]`). |
| `0x21` | `LOAD_LOCAL_1` | **0** | None | `[] -> [val]` | Fast load 16-bit word from local slot 1 (`FP[1]`). |
| `0x22` | `LOAD_LOCAL_2` | **0** | None | `[] -> [val]` | Fast load 16-bit word from local slot 2 (`FP[2]`). |
| `0x23` | `LOAD_LOCAL_3` | **0** | None | `[] -> [val]` | Fast load 16-bit word from local slot 3 (`FP[3]`). |
| `0x24` | `STORE_LOCAL_0`| **0** | None | `[val] -> []` | Fast store 16-bit word into local slot 0 (`FP[0]`). |
| `0x25` | `STORE_LOCAL_1`| **0** | None | `[val] -> []` | Fast store 16-bit word into local slot 1 (`FP[1]`). |
| `0x26` | `STORE_LOCAL_2`| **0** | None | `[val] -> []` | Fast store 16-bit word into local slot 2 (`FP[2]`). |
| `0x27` | `STORE_LOCAL_3`| **0** | None | `[val] -> []` | Fast store 16-bit word into local slot 3 (`FP[3]`). |
| `0x28` | `LOAD_LOCAL` | **1** | `<imm8>` | `[] -> [val]` | Load 16-bit word from local slot `FP[imm8]`. |
| `0x29` | `STORE_LOCAL`| **1** | `<imm8>` | `[val] -> []` | Store 16-bit word into local slot `FP[imm8]`. |
| `0x2A` | `LOAD_GLOBAL` | **2** | `<imm16>` | `[] -> [val]` | Load 16-bit word from global slot `Globals[imm16]`. |
| `0x2B` | `STORE_GLOBAL`| **2** | `<imm16>` | `[val] -> []` | Store 16-bit word into global slot `Globals[imm16]`. |
| `0x2C` | `LOAD_FIELD` | **1** | `<imm8>` | `[obj_ptr] -> [val]`| Load 16-bit word from struct field at byte offset `imm8`. |
| `0x2D` | `STORE_FIELD`| **1** | `<imm8>` | `[obj_ptr, val] -> []`| Store 16-bit word into struct field at offset `imm8`. |
| `0x2E` | `LOAD_INDEX` | **0** | None | `[coll_ptr, idx] -> [val]`| Subscript load: 16-bit word at `coll[idx]`. |
| `0x2F` | `STORE_INDEX`| **0** | None | `[coll_ptr, idx, val] -> []`| Subscript store: `coll[idx] = val`. |

#### Group 3: Arithmetic, Logic & Comparisons (`0x40 .. 0x5F`)

*All standard arithmetic and comparison opcodes take 0 argument bytes.*

| Opcode | Mnemonic | Arg Bytes | Operand Format | Stack Effect | Description |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `0x40` | `ADD` | **0** | None | `[a, b] -> [a + b]` | 16-bit integer addition. |
| `0x41` | `SUB` | **0** | None | `[a, b] -> [a - b]` | 16-bit integer subtraction. |
| `0x42` | `MUL` | **0** | None | `[a, b] -> [a * b]` | 16-bit signed integer multiplication. |
| `0x43` | `DIV` | **0** | None | `[a, b] -> [a / b]` | 16-bit signed integer division. |
| `0x44` | `MOD` | **0** | None | `[a, b] -> [a % b]` | 16-bit integer modulo. |
| `0x45` | `NEG` | **0** | None | `[a] -> [-a]` | 16-bit integer negation. |
| `0x46` | `BIT_AND` | **0** | None | `[a, b] -> [a & b]` | 16-bit bitwise AND. |
| `0x47` | `BIT_OR` | **0** | None | `[a, b] -> [a \| b]` | 16-bit bitwise OR. |
| `0x48` | `BIT_XOR` | **0** | None | `[a, b] -> [a ^ b]` | 16-bit bitwise XOR. |
| `0x49` | `BIT_NOT` | **0** | None | `[a] -> [~a]` | 16-bit bitwise NOT. |
| `0x4A` | `SHL` | **0** | None | `[a, b] -> [a << b]` | 16-bit logical shift left. |
| `0x4B` | `SHR` | **0** | None | `[a, b] -> [a >> b]` | 16-bit arithmetic shift right. |
| `0x4C` | `CMP_EQ` | **0** | None | `[a, b] -> [bool]` | Equal (`==`). Pushes `$0001` (true) or `$0000` (false). |
| `0x4D` | `CMP_NE` | **0** | None | `[a, b] -> [bool]` | Not equal (`!=`). Pushes `$0001` or `$0000`. |
| `0x4E` | `CMP_LT` | **0** | None | `[a, b] -> [bool]` | Signed less than (`<`). |
| `0x4F` | `CMP_LE` | **0** | None | `[a, b] -> [bool]` | Signed less than or equal (`<=`). |
| `0x50` | `CMP_GT` | **0** | None | `[a, b] -> [bool]` | Signed greater than (`>`). |
| `0x51` | `CMP_GE` | **0** | None | `[a, b] -> [bool]` | Signed greater than or equal (`>=`). |
| `0x52` | `NOT` | **0** | None | `[a] -> [bool]` | Logical NOT: pushes `$0001` if `a == $0000`, else `$0000`. |
| `0x53` | `MIN` | **0** | None | `[a, b] -> [min(a,b)]`| Signed integer minimum. |
| `0x54` | `MAX` | **0** | None | `[a, b] -> [max(a,b)]`| Signed integer maximum. |
| `0x55` | `PARSE_INT`| **0** | None | `[str, radix] -> [val, ok]`| Parse integer from string with radix autodetection. Pushes parsed value and success Boolean (`$0001` or `$0000`). |

#### Group 4: Control Flow & Function Calls (`0x60 .. 0x6F`)

| Opcode | Mnemonic | Arg Bytes | Operand Format | Stack Effect | Description |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `0x60` | `JUMP` | **2** | `<rel16>` | `[] -> []` | Relative unconditional branch. |
| `0x61` | `JUMP_IF_TRUE`| **2** | `<rel16>` | `[cond] -> []` | Pop 16-bit word; branch if `cond != $0000`. |
| `0x62` | `JUMP_IF_FALSE`| **2**| `<rel16>` | `[cond] -> []` | Pop 16-bit word; branch if `cond == $0000`. |
| `0x63` | `CALL` | **2** | `<imm16>` | `[args...] -> [res]` | Call function index `imm16` (parameter count defined in Function Table). |
| `0x64` | `RET` | **0** | None | `[res] -> [...]` | Return top 16-bit word to caller. |
| `0x65` | `RET_VOID` | **0** | None | `[] -> [...]` | Return `nil` (`$0000`) to caller. |
| `0x66` | `HALT` | **0** | None | `[] -> []` | Terminate VM execution cleanly (exit 0). |

#### Group 5: String & Text Processing (`0x70 .. 0x8F`)

| Opcode | Mnemonic | Arg Bytes | Operand Format | Stack Effect | Description |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `0x70` | `STR_LEN` | **0** | None | `[str] -> [len]` | Length of string in bytes. |
| `0x71` | `STR_SLICE` | **0** | None | `[str, start, end] -> [view]`| Substring view without copying memory. |
| `0x72` | `STR_CHAR_AT`| **0** | None | `[str, idx] -> [char]` | Byte value at index (or -1 if out of bounds). |
| `0x73` | `STR_LSTRIP` | **0** | None | `[str, chars] -> [view]`| Strip leading characters (`chars=0` for whitespace). |
| `0x74` | `STR_RSTRIP` | **0** | None | `[str, chars] -> [view]`| Strip trailing characters. |
| `0x75` | `STR_STRIP` | **0** | None | `[str, chars] -> [view]`| Strip leading and trailing characters. |
| `0x76` | `STR_UPPER` | **0** | None | `[str] -> [new_str]` | Returns uppercase ASCII copy. |
| `0x77` | `STR_FIND` | **0** | None | `[str, sub, start] -> [idx]`| Linear search; returns character index or -1. |
| `0x78` | `STR_STARTSWITH`| **0**| None | `[str, pfx] -> [bool]`| Prefix check: pushes `$0001` or `$0000`. |
| `0x79` | `STR_ENDSWITH`| **0** | None | `[str, sfx] -> [bool]`| Suffix check: pushes `$0001` or `$0000`. |
| `0x7A` | `STR_REPLACE` | **0** | None | `[str, old, new] -> [res]`| Global substring replacement. |
| `0x7B` | `STR_SPLITLINES`| **0**| None | `[str] -> [list]` | Splits text by `\n` or `\r\n` into line views. |
| `0x7C` | `STR_JOIN` | **0** | None | `[delim, list] -> [str]`| Joins list of strings using delimiter. |
| `0x7D` | `STR_FORMAT_INT`| **1**| `<imm8>` | `[val] -> [str]` | Format integer with zero-padding (width `imm8`, e.g. 4 for `%04d`). |
| `0x7E` | `STR_ISSPACE` | **0** | None | `[str] -> [bool]` | True (`$0001`) if string is empty or whitespace only. |
| `0x7F` | `STR_REPLACE_IDENT`| **0**| None | `[str, old, new] -> [res]`| **Word-Boundary Replacer**: Replaces `old` with `new` only when neither preceded nor followed by `[A-Za-z0-9_.]`. (Replaces lookaround regex!). |

#### Group 6: Collections (Lists, Dicts, Sets) (`0x90 .. 0xAF`)

*All collection containers store uniform 16-bit words. A pointer to a List or Dict can be `$0000` (`nil`).*

| Opcode | Mnemonic | Arg Bytes | Operand Format | Stack Effect | Description |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `0x90` | `LIST_NEW` | **2** | `<imm16>` | `[] -> [list_ptr]` | Allocate list preallocated for `imm16` 16-bit words. |
| `0x91` | `LIST_APPEND`| **0** | None | `[list_ptr, val] -> []` | Append 16-bit word to list. |
| `0x92` | `LIST_LEN` | **0** | None | `[list_ptr] -> [len]` | Count of 16-bit elements in list. |
| `0x93` | `LIST_POP` | **0** | None | `[list_ptr] -> [val]` | Pop and return last 16-bit element. |
| `0x94` | `LIST_INDEX_OF`| **0**| None | `[list_ptr, val] -> [idx, ok]`| Search for 16-bit word; pushes index and Boolean (`$0001`/`$0000`). |
| `0x95` | `LIST_REMOVE_AT`| **0**| None | `[list_ptr, idx] -> []` | Remove element at index, shifting tail left. |
| `0x96` | `LIST_SORT_BY_LEN`| **0**| None | `[list_ptr, reverse] -> []`| Sorts list of strings in-place by string length. |
| `0x97` | `DICT_NEW` | **2** | `<imm16>` | `[] -> [dict_ptr]` | Allocate hash table with bucket capacity `imm16`. |
| `0x98` | `DICT_GET` | **0** | None | `[dict_ptr, key_str] -> [val, ok]`| Lookup string key; pushes 16-bit word and Boolean (`$0001`/`$0000`). |
| `0x99` | `DICT_SET` | **0** | None | `[dict_ptr, key_str, val] -> []`| Store 16-bit word for string key. |
| `0x9A` | `DICT_HAS` | **0** | None | `[dict_ptr, key_str] -> [bool]`| Test key membership in dictionary. |
| `0x9B` | `DICT_KEYS` | **0** | None | `[dict_ptr] -> [list_ptr]` | Returns list of string key pointers. |
| `0x9C` | `DICT_ITEMS` | **0** | None | `[dict_ptr] -> [list_ptr]` | Returns list of `(key, value)` 16-bit word pairs. |
| `0x9D` | `SET_NEW` | **2** | `<imm16>` | `[] -> [set_ptr]` | Allocate string hash set with capacity `imm16`. |
| `0x9E` | `SET_ADD` | **0** | None | `[set_ptr, str] -> []` | Add string pointer to set. |
| `0x9F` | `SET_HAS` | **0** | None | `[set_ptr, str] -> [bool]` | Test if string pointer exists in set (`$0001`/`$0000`). |

#### Group 7: Regular Expressions (`0xB0 .. 0xBF`)

| Opcode | Mnemonic | Arg Bytes | Operand Format | Stack Effect | Description |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `0xB0` | `REG_MATCH` | **2** | `<imm16>` | `[str] -> [match_ptr, ok]`| Anchored match against regex at index `imm16`. |
| `0xB1` | `REG_SEARCH`| **2** | `<imm16>` | `[str] -> [match_ptr, ok]`| Unanchored search against regex at index `imm16`. |
| `0xB2` | `REG_GROUP` | **0** | None | `[match_ptr, grp_idx] -> [str]`| Extract captured group string view. |
| `0xB3` | `REG_GROUP_END`| **0**| None | `[match_ptr, grp_idx] -> [pos]`| Return ending character index of capture. |
| `0xB4` | `REG_SUB` | **2** | `<imm16>` | `[str, repl] -> [res]` | Replace all occurrences with literal string `repl`. |

#### Group 8: File System & OS System Calls (`0xC0 .. 0xCF`)

| Opcode | Mnemonic | Arg Bytes | Operand Format | Stack Effect | Description |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `0xC0` | `FILE_OPEN_READ`| **0**| None | `[path] -> [handle, ok]`| Open file for reading (`os9 I$Open`). |
| `0xC1` | `FILE_OPEN_WRITE`| **0**| None | `[path] -> [handle, ok]`| Create/truncate file for writing (`os9 I$Create`). |
| `0xC2` | `FILE_READLINE`| **0**| None | `[handle] -> [line, eof]`| Read line via `os9 I$ReadLn`. |
| `0xC3` | `FILE_WRITE` | **0** | None | `[handle, str] -> [ok]` | Write string buffer via `os9 I$Write`. |
| `0xC4` | `FILE_CLOSE` | **0** | None | `[handle] -> []` | Close path via `os9 I$Close`. |
| `0xC5` | `OS_ISFILE` | **0** | None | `[path] -> [bool]` | Test file existence. |
| `0xC6` | `OS_MAKEDIRS` | **0** | None | `[path] -> [ok]` | Recursively create directory path (`os9 I$MakDir`). |
| `0xC7` | `SYS_ARGS` | **0** | None | `[] -> [list_ptr]` | Push command line argument string list. |
| `0xC8` | `SYS_EXIT` | **0** | None | `[code] -> []` | Exit process with status code (`os9 F$Exit`). |
| `0xC9` | `IO_PRINT` | **0** | None | `[str] -> []` | Print string followed by newline to stdout (`I$WriteLn`). |

---

## 6. Fast 6809 / 6309 Interpreter Implementation

Because every opcode is 1 byte with a fixed, known argument length, the instruction dispatch loop on a Motorola 6809 or Hitachi 6309 CPU is fast and compact.

### 6.1 Register Allocation in 6809 Assembly
- **`X`**: Program Counter (`PC`) pointing to the current bytecode instruction.
- **`U`**: Operand Stack Pointer (`SP`), growing downward.
- **`Y`**: Frame Pointer (`FP`) pointing to the base of local variables.
- **`S`**: Hardware Call Stack (storing return addresses and saved `FP`s).
- **`D`**: Work accumulator (`A` and `B`).

### 6.2 The Core Dispatch Loop (12 CPU Cycles)

```assembly
; ====================================================================
; NextInst: Fetch 1-byte opcode and dispatch via jump table
; Cycles on 6809: ldb (5) + clra (2) + aslb (2) + rola (2) + jmp (6) = 17 cycles
; Cycles on 6309: clra (1) + ldb ,x+ (5) + lsld (1) + jmp [d,v] (4) = 11 cycles
; ====================================================================
NextInst:
            ldb       ,x+                 ; Fetch 1-byte opcode, advance PC
            clra
            aslb                          ; Multiply by 2 for word-table offset
            rola
            ldu       #OpcodeTable        ; Base of handler address table
            jmp       [d,u]               ; Indirect jump to opcode handler
```

### 6.3 Handlers for Frequent Zero-Byte Opcodes

```assembly
; --- 0x01: PUSH_NIL (0 arg bytes) ---
Op_PUSH_NIL:
            clra
            clrb                          ; D = $0000 (nil / false)
            pshu      d                   ; Push onto operand stack
            bra       NextInst

; --- 0x02: PUSH_TRUE (0 arg bytes) ---
Op_PUSH_TRUE:
            ldd       #$0001              ; Canonical true
            pshu      d
            bra       NextInst

; --- 0x05: PUSH_1 (0 arg bytes) ---
Op_PUSH_1:
            ldd       #$0001
            pshu      d
            bra       NextInst

; --- 0x20: LOAD_LOCAL_0 (0 arg bytes) ---
Op_LOAD_LOCAL_0:
            ldd       ,y                  ; Load 16-bit word from FP[0]
            pshu      d                   ; Push onto operand stack
            bra       NextInst

; --- 0x24: STORE_LOCAL_0 (0 arg bytes) ---
Op_STORE_LOCAL_0:
            pulu      d                   ; Pop 16-bit word from stack
            std       ,y                  ; Store into FP[0]
            bra       NextInst

; --- 0x40: ADD (0 arg bytes) ---
Op_ADD:
            pulu      d                   ; Pop second operand (B)
            addd      ,u                  ; Add to first operand on stack (A + B)
            std       ,u                  ; Replace top of stack
            bra       NextInst

; --- 0x61: JUMP_IF_TRUE (2 arg bytes) ---
Op_JUMP_IF_TRUE:
            pulu      d                   ; Pop 16-bit condition word
            cmpd      #$0000
            bne       Op_JUMP             ; Non-zero -> true -> take branch!
            leax      2,x                 ; False -> skip 2-byte branch offset
            bra       NextInst

; --- 0x62: JUMP_IF_FALSE (2 arg bytes) ---
Op_JUMP_IF_FALSE:
            pulu      d                   ; Pop 16-bit condition word
            cmpd      #$0000
            beq       Op_JUMP             ; $0000 -> false / nil / zero -> take branch!
            leax      2,x                 ; Non-zero -> skip 2-byte branch offset
            bra       NextInst

; --- 0x64: RET (0 arg bytes) ---
Op_RET:
            pulu      d                   ; Pop return value from stack into D
            puls      x,y                 ; Restore caller PC into X, caller FP into Y
            pshu      d                   ; Push return value onto caller's stack
            bra       NextInst

; --- 0x65: RET_VOID (0 arg bytes) ---
Op_RET_VOID:
            puls      x,y                 ; Restore caller PC and FP
            clra
            clrb                          ; D = $0000 (nil)
            pshu      d                   ; Push nil return value
            bra       NextInst
```

### 6.4 Handlers for Immediate Opcodes (1 and 2 Bytes)

```assembly
; --- 0x07: PUSH_I8 (1 arg byte) ---
Op_PUSH_I8:
            ldb       ,x+                 ; Fetch 1-byte immediate operand
            sex                           ; Sign-extend B into D
            pshu      d                   ; Push 16-bit word
            bra       NextInst

; --- 0x09: PUSH_I16 (2 arg bytes) ---
Op_PUSH_I16:
            ldd       ,x++                ; Fetch 2-byte big-endian immediate
            pshu      d                   ; Push 16-bit word
            bra       NextInst

; --- 0x28: LOAD_LOCAL (1 arg byte) ---
Op_LOAD_LOCAL:
            ldb       ,x+                 ; Slot index (0..255)
            clra
            aslb
            rola                          ; Slot * 2
            ldd       d,y                 ; Load 16-bit word from FP[slot]
            pshu      d
            bra       NextInst

; --- 0x60: JUMP (2 arg bytes) ---
Op_JUMP:
            ldd       ,x                  ; Fetch 16-bit relative branch offset
            leax      d,x                 ; PC = PC + offset
            bra       NextInst
```

---

## 7. Concrete Example: Compiling `selfgen_preprocess` to NPCode

Here is how lines 53–63 of `selfgen_preprocess.py` look in NP source code and how they assemble into NPCode:

### 7.1 NP Source Code
```python
fn split_asm_line(line: str) -> (str, str):
    let s: str = line.rstrip("\r\n")
    let s_strip: str = s.lstrip("")
    if s == "" or s_strip.startswith("*") or s_strip.startswith(";"):
        return ("", line)
    # ...
```

### 7.2 Bytecode Disassembly with Argument Bytes

```text
Offset   Opcode  ArgBytes  Operands       Assembly Mnemonic          Description
-------------------------------------------------------------------------------------------------
0x0020   0x20    0         None           LOAD_LOCAL_0               Push line (FP[0])
0x0021   0x0A    2         0x0012         PUSH_STR 0x0012            Push "\r\n" from String Pool
0x0024   0x74    0         None           STR_RSTRIP                 s = line.rstrip("\r\n")
0x0025   0x25    0         None           STORE_LOCAL_1              Store into s (FP[1])

0x0026   0x21    0         None           LOAD_LOCAL_1               Push s (FP[1])
0x0027   0x01    0         None           PUSH_NIL                   Nil ($0000) = default whitespace
0x0028   0x73    0         None           STR_LSTRIP                 s_strip = s.lstrip()
0x0029   0x26    0         None           STORE_LOCAL_2              Store into s_strip (FP[2])

; if s == "":
0x002A   0x21    0         None           LOAD_LOCAL_1               Push s
0x002B   0x0A    2         0x0000         PUSH_STR 0x0000            Push "" (empty string)
0x002E   0x4C    0         None           CMP_EQ                     s == "" -> $0001 or $0000
0x002F   0x61    2         0x001C         JUMP_IF_TRUE +28 (L_RET)   If != 0 -> return ("", line)

; or s_strip.startswith("*"):
0x0032   0x22    0         None           LOAD_LOCAL_2               Push s_strip
0x0033   0x0A    2         0x0018         PUSH_STR 0x0018            Push "*"
0x0036   0x78    0         None           STR_STARTSWITH             s_strip.startswith("*")
0x0037   0x61    2         0x0014         JUMP_IF_TRUE +20 (L_RET)   If != 0 -> return ("", line)

; or s_strip.startswith(";"):
0x003A   0x22    0         None           LOAD_LOCAL_2               Push s_strip
0x003B   0x0A    2         0x001C         PUSH_STR 0x001C            Push ";"
0x003E   0x78    0         None           STR_STARTSWITH             s_strip.startswith(";")
0x003F   0x62    2         0x000E         JUMP_IF_FALSE +14          If == 0 -> proceed to pos=0

; L_RET: return ("", line)
0x0042   0x0A    2         0x0000         PUSH_STR 0x0000            Push ""
0x0045   0x20    0         None           LOAD_LOCAL_0               Push line
0x0046   0x64    0         None           RET                        Return 2-tuple on stack
```

---

## 8. Summary of Benefits

1. **Pure 16-Bit Word Engine**: Like Go, every stack item, local variable, and collection element is a raw 16-bit word (`uint16_t`). No type tag storage on the stack.
2. **Simplified Nil & Booleans**:
   - `nil` is strictly the 16-bit zero word `$0000`. No heap-allocated nil object.
   - Booleans are `$0000` (false) and non-zero (true), with `$0001` as canonical true.
   - The conditional branch (`if`) tests for `$0000`, unifying boolean, pointer nil, and numeric zero checks into one fast CPU operation.
3. **Ultra-Compact Instruction Stream**: Frequent operations (`PUSH_NIL`, `RET`, `ADD`, `SUB`, `LOAD_LOCAL_0..3`) take only **1 single byte** in memory.
4. **Deterministic Argument Parsing**: The VM decoder reads exactly the number of immediate bytes specified by the opcode without inspecting dynamic tags.
5. **No Regex Backtracking**: The specialized `STR_REPLACE_IDENT` opcode replaces lookahead and lookbehind regexes with an $O(N)$ single-pass boundary check.
