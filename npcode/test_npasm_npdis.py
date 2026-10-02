#!/usr/bin/env python3
"""
test_npasm_npdis.py - Verification test suite for npasm.py and npdis.py.
Tests assembly, disassembly, expression parsing, and byte-for-byte round-tripping.
"""

import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NPASM = os.path.join(SCRIPT_DIR, "npasm.py")
NPDIS = os.path.join(SCRIPT_DIR, "npdis.py")

TEST_ASM_SOURCE = """; ====================================================================
; NPCode Comprehensive Test Program
; ====================================================================

; Equates and calculated expressions
BUFFER_SIZE = 128
MAX_ITEMS   = (BUFFER_SIZE / 2) + 4 * 2
HEX_VAL     = $2000
BIN_VAL     = %10101010
CHAR_VAL    = 'Z'

; Globals
.global g_counter: scalar
.global g_buffer:  scalar
.global g_symtab:  slice

; Function: split_asm_line
; Demonstrates parameters, locals, string slicing, and forward branching
.function split_asm_line
    .param line: slice
    .local s: slice
    .local s_strip: slice
    .local code_part: slice
    .local comment_part: slice

    ; s = line.rstrip("\\r\\n")
    LOAD_LOCAL line
    PUSH_STR "\\r\\n"
    STR_RSTRIP
    STORE_LOCAL s

    ; s_strip = s.lstrip()
    LOAD_LOCAL s
    PUSH_NIL_SLICE
    STR_LSTRIP
    STORE_LOCAL s_strip

    ; if s == "": return ("", line)
    LOAD_LOCAL s
    PUSH_STR ""
    STR_CMP
    NOT
    JUMP_IF_TRUE .L_ret_empty

    ; or s_strip.startswith("*"):
    LOAD_LOCAL s_strip
    PUSH_STR "*"
    STR_STARTSWITH
    JUMP_IF_TRUE .L_ret_empty

    ; or s_strip.startswith(";"):
    LOAD_LOCAL s_strip
    PUSH_STR ";"
    STR_STARTSWITH
    JUMP_IF_FALSE .L_proceed

.L_ret_empty:
    PUSH_STR ""
    LOAD_LOCAL line
    RET_SLICE

.L_proceed:
    PUSH_STR "CODE"
    PUSH_STR "COMMENT"
    RET_SLICE
.endfunction

; Function: test_dict_and_math
; Demonstrates linear dict operations, fixed buffers, expressions, and loops
.function test_dict_and_math
    .param count: scalar
    .local d: slice
    .local buf: scalar
    .local idx: scalar
    .local ok: scalar
    .local val: scalar

    ; Allocate a fixed-size buffer
    PUSH_I16 BUFFER_SIZE
    BUF_ALLOC
    STORE_LOCAL buf

    ; Create a dictionary preallocated for 8 entries (16 words)
    DICT_NEW 8
    STORE_LOCAL d

    ; Store key-value pair: d["LDA"] = $00A6
    LOAD_LOCAL d
    PUSH_STR "LDA"
    PUSH_I16 $00A6
    DICT_SET
    STORE_LOCAL d

    ; Store key-value pair: d["STA"] = $00B7
    LOAD_LOCAL d
    PUSH_STR "STA"
    PUSH_I16 $00B7
    DICT_SET
    STORE_LOCAL d

    ; Lookup "LDA"
    LOAD_LOCAL d
    PUSH_STR "LDA"
    DICT_GET
    STORE_LOCAL ok
    STORE_LOCAL val

    ; Loop test: backward branch
    PUSH_0
    STORE_LOCAL idx

.L_loop_top:
    LOAD_LOCAL idx
    LOAD_LOCAL count
    CMP_LT
    JUMP_IF_FALSE .L_loop_end

    ; idx = idx + 1
    LOAD_LOCAL idx
    PUSH_1
    ADD
    STORE_LOCAL idx
    JUMP .L_loop_top

.L_loop_end:
    ; Free buffer
    LOAD_LOCAL buf
    BUF_FREE

    LOAD_LOCAL val
    RET
.endfunction

; Function: main
; Entry point function
; Function: test_all_opcodes
; Exercises all opcodes across groups 1 through 8
.function test_all_opcodes
    .param p0: scalar
    .local l0: scalar
    .local l1: scalar
    .local l2: scalar
    .local l3: scalar
    .local l4: slice

    NOP
    PUSH_NIL
    PUSH_NIL_SLICE
    PUSH_TRUE
    PUSH_FALSE
    PUSH_0
    PUSH_1
    PUSH_NEG1
    PUSH_I8 -42
    PUSH_U8 200
    PUSH_I16 $1234
    POP
    POP_SLICE
    DUP
    SWAP

    LOAD_LOCAL_0
    LOAD_LOCAL_1
    LOAD_LOCAL_2
    LOAD_LOCAL_3
    STORE_LOCAL_0
    STORE_LOCAL_1
    STORE_LOCAL_2
    STORE_LOCAL_3
    LOAD_LOCAL 4
    STORE_LOCAL 4
    LOAD_GLOBAL g_counter
    STORE_GLOBAL g_counter
    BUF_ALLOC
    BUF_FREE
    LOAD_FIELD 2
    STORE_FIELD 2
    ADDR_OF_GLOBAL g_counter
    PEEK2
    POKE2
    PEEK1
    POKE1
    ADDR_OF_LOCAL 0
    SHL1_ADD

    ADD
    SUB
    MUL
    DIV
    MOD
    NEG
    BIT_AND
    BIT_OR
    BIT_XOR
    BIT_NOT
    SHL
    SHR
    CMP_EQ
    CMP_NE
    CMP_LT
    CMP_LE
    CMP_GT
    CMP_GE
    NOT
    MIN
    MAX
    PARSE_INT

    SLICE_NEW
    SLICE_LEN
    SLICE_CAP
    SLICE_SUB
    SLICE_GET_BYTE
    SLICE_GET_WORD
    SLICE_SET_WORD
    STR_CMP
    STR_STARTSWITH
    STR_ENDSWITH
    STR_FIND
    STR_LSTRIP
    STR_RSTRIP
    STR_STRIP
    STR_SPLITLINES
    STR_REPLACE_IDENT

    DICT_NEW 4
    DICT_GET
    DICT_SET
    DICT_HAS
    DICT_KEYS
    DICT_LEN
    LIST_NEW 10
    LIST_APPEND
    LIST_POP
    LIST_SORT_BY_LEN

    REG_MATCH 0
    REG_SEARCH 1
    REG_GROUP
    REG_GROUP_END

    FILE_OPEN_READ
    FILE_OPEN_WRITE
    FILE_READLINE
    FILE_WRITE
    FILE_CLOSE
    OS_ISFILE
    OS_MAKEDIRS
    SYS_ARGS
    SYS_EXIT
    IO_PRINT
    PRINT
    PRINTLN

    RET_VOID
.endfunction

; Function: main
; Entry point function
.function main entry
    .local test_line: slice
    .local res_code: slice
    .local res_comm: slice
    .local res_val: scalar

    PUSH_STR "  LDA #$20 ; load accumulator\\r\\n"
    STORE_LOCAL test_line

    LOAD_LOCAL test_line
    CALL split_asm_line
    STORE_LOCAL res_comm
    STORE_LOCAL res_code

    LOAD_LOCAL res_code
    IO_PRINT

    PUSH_I16 10
    CALL test_dict_and_math
    STORE_LOCAL res_val

    LOAD_LOCAL res_val
    STORE_GLOBAL g_counter

    PUSH_0
    SYS_EXIT
.endfunction
"""


def run():
    print("=== Running NPCode Assembler & Disassembler Test Suite ===")

    tmp_asm1 = "/tmp/test_source1.npasm"
    tmp_npc1 = "/tmp/test_bin1.npc"
    tmp_asm2 = "/tmp/test_source2.npasm"
    tmp_npc2 = "/tmp/test_bin2.npc"

    with open(tmp_asm1, "w", encoding="utf-8") as f:
        f.write(TEST_ASM_SOURCE)

    # 1. Assemble tmp_asm1 -> tmp_npc1
    print("\n1. Assembling initial source...")
    res = subprocess.run([sys.executable, NPASM, tmp_asm1, "-o", tmp_npc1, "--listing"], capture_output=True, text=True)
    if res.returncode != 0:
        print("npasm failed stdout:\n", res.stdout)
        print("npasm failed stderr:\n", res.stderr)
        sys.exit(1)
    print("npasm succeeded. Listing:")
    print(res.stdout)

    size1 = os.path.getsize(tmp_npc1)
    print(f"Generated NPC binary size: {size1} bytes.")

    # 2. Run npdis details on tmp_npc1
    print("\n2. Inspecting NPC binary details with npdis.py --details...")
    res = subprocess.run([sys.executable, NPDIS, tmp_npc1, "--details"], capture_output=True, text=True)
    if res.returncode != 0:
        print("npdis failed:\n", res.stderr)
        sys.exit(1)
    print(res.stdout)

    # 3. Disassemble to formatted listing
    print("\n3. Disassembling NPC to human-readable listing...")
    res = subprocess.run([sys.executable, NPDIS, tmp_npc1], capture_output=True, text=True)
    if res.returncode != 0:
        print("npdis failed:\n", res.stderr)
        sys.exit(1)
    print(res.stdout)

    # 4. Generate re-assemblable source code with npdis.py --asm
    print("\n4. Generating re-assemblable source with npdis.py --asm...")
    res = subprocess.run([sys.executable, NPDIS, tmp_npc1, "--asm", "-o", tmp_asm2], capture_output=True, text=True)
    if res.returncode != 0:
        print("npdis --asm failed:\n", res.stderr)
        sys.exit(1)

    with open(tmp_asm2, "r", encoding="utf-8") as f:
        disasm_source = f.read()
    print("Disassembled source preview (first 40 lines):")
    for line in disasm_source.splitlines()[:40]:
        print("  ", line)

    # 5. Re-assemble tmp_asm2 -> tmp_npc2
    print("\n5. Re-assembling disassembled source...")
    res = subprocess.run([sys.executable, NPASM, tmp_asm2, "-o", tmp_npc2], capture_output=True, text=True)
    if res.returncode != 0:
        print("npasm re-assembly failed stdout:\n", res.stdout)
        print("npasm re-assembly failed stderr:\n", res.stderr)
        sys.exit(1)

    size2 = os.path.getsize(tmp_npc2)
    print(f"Re-assembled NPC binary size: {size2} bytes.")

    # 6. Compare binaries byte-for-byte
    print("\n6. Comparing original and re-assembled binaries byte-for-byte...")
    with open(tmp_npc1, "rb") as f1, open(tmp_npc2, "rb") as f2:
        b1 = f1.read()
        b2 = f2.read()

    if b1 == b2:
        print(f"SUCCESS: Binaries match identically ({len(b1)} bytes)! Round-trip verified 100%.")
    else:
        print(f"MISMATCH: Binary 1 has {len(b1)} bytes, Binary 2 has {len(b2)} bytes.")
        diffs = 0
        min_len = min(len(b1), len(b2))
        for i in range(min_len):
            if b1[i] != b2[i]:
                print(f"  Diff at offset 0x{i:04X}: orig 0x{b1[i]:02X} != re 0x{b2[i]:02X}")
                diffs += 1
                if diffs > 20:
                    break
        sys.exit(1)

    print("\n=== All Tests Passed Successfully! ===")


if __name__ == "__main__":
    run()
