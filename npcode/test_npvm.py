#!/usr/bin/env python3
"""
test_npvm.py - Verification test suite for npvm.py (NPCode VM Emulator).
Tests execution of arithmetic, strings, slices, linear dicts, lists, buffers,
recursion, file I/O, and verbose tracing.
"""

import os
import sys
import tempfile
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NPASM = os.path.join(SCRIPT_DIR, "npasm.py")
NPVM = os.path.join(SCRIPT_DIR, "npvm.py")


def assemble_and_run(source: str, verbose: bool = False, cli_args: list = None) -> tuple[int, str, str]:
    with tempfile.NamedTemporaryFile("w", suffix=".npasm", delete=False) as f_asm:
        f_asm.write(source)
        asm_path = f_asm.name

    npc_path = asm_path[:-6] + ".npc"
    try:
        # Assemble
        res_asm = subprocess.run([sys.executable, NPASM, asm_path, "-o", npc_path], capture_output=True, text=True)
        if res_asm.returncode != 0:
            raise RuntimeError(f"Assembler failed:\n{res_asm.stdout}\n{res_asm.stderr}")

        # Run VM
        cmd = [sys.executable, NPVM, npc_path]
        if verbose:
            cmd.append("-v")
        if cli_args:
            cmd.append("--")
            cmd.extend(cli_args)

        res_vm = subprocess.run(cmd, capture_output=True, text=True)
        return res_vm.returncode, res_vm.stdout, res_vm.stderr
    finally:
        if os.path.exists(asm_path):
            os.remove(asm_path)
        if os.path.exists(npc_path):
            os.remove(npc_path)


def test_basic_arithmetic():
    print("Testing basic arithmetic and logic...")
    src = """
    .global g_res: scalar

    .function main entry
        ; (10 + 20) * 3 - 40 / 4 = 30 * 3 - 10 = 90 - 10 = 80 ($50)
        PUSH_I16 10
        PUSH_I16 20
        ADD
        PUSH_I16 3
        MUL
        PUSH_I16 40
        PUSH_I16 4
        DIV
        SUB
        STORE_GLOBAL g_res
        PUSH_0
        SYS_EXIT
    .endfunction
    """
    rc, out, err = assemble_and_run(src, verbose=True)
    assert rc == 0, f"Failed with rc={rc}, err={err}"
    assert "STORE_GLOBAL slot 0 <- 0x0050 (80)" in out, f"Expected 80, got:\n{out}"
    print("  -> Arithmetic OK.")


def test_recursion_factorial():
    print("Testing recursive function calls (factorial)...")
    src = """
    .global g_fact: scalar

    .function factorial
        .param n: scalar
        .local n_minus_1: scalar
        .local sub_res: scalar

        LOAD_LOCAL n
        PUSH_I16 1
        CMP_LE
        JUMP_IF_FALSE .L_recurse

        PUSH_1
        RET

    .L_recurse:
        LOAD_LOCAL n
        PUSH_1
        SUB
        STORE_LOCAL n_minus_1

        LOAD_LOCAL n_minus_1
        CALL factorial
        STORE_LOCAL sub_res

        LOAD_LOCAL n
        LOAD_LOCAL sub_res
        MUL
        RET
    .endfunction

    .function main entry
        ; 5! = 120 ($0078)
        PUSH_I16 5
        CALL factorial
        STORE_GLOBAL g_fact
        PUSH_0
        SYS_EXIT
    .endfunction
    """
    rc, out, err = assemble_and_run(src, verbose=True)
    assert rc == 0, f"Failed with rc={rc}, err={err}"
    assert "STORE_GLOBAL slot 0 <- 0x0078 (120)" in out, f"Expected 120, got:\n{out}"
    print("  -> Factorial recursion OK.")


def test_linear_dict():
    print("Testing linear unhashed dictionary operations...")
    src = """
    .global g_val1: scalar
    .global g_val2: scalar
    .global g_has:  scalar
    .global g_len:  scalar

    .function main entry
        .local d: slice
        .local val: scalar
        .local ok: scalar

        DICT_NEW 4
        STORE_LOCAL d

        ; Insert "FOO" = $1111
        LOAD_LOCAL d
        PUSH_STR "FOO"
        PUSH_I16 $1111
        DICT_SET
        STORE_LOCAL d

        ; Insert "BAR" = $2222
        LOAD_LOCAL d
        PUSH_STR "BAR"
        PUSH_I16 $2222
        DICT_SET
        STORE_LOCAL d

        ; Update "FOO" = $3333
        LOAD_LOCAL d
        PUSH_STR "FOO"
        PUSH_I16 $3333
        DICT_SET
        STORE_LOCAL d

        ; Lookup "FOO" -> $3333
        LOAD_LOCAL d
        PUSH_STR "FOO"
        DICT_GET
        STORE_LOCAL ok
        STORE_LOCAL val
        LOAD_LOCAL val
        STORE_GLOBAL g_val1

        ; Lookup "BAR" -> $2222
        LOAD_LOCAL d
        PUSH_STR "BAR"
        DICT_GET
        STORE_LOCAL ok
        STORE_LOCAL val
        LOAD_LOCAL val
        STORE_GLOBAL g_val2

        ; Has "FOO" -> 1
        LOAD_LOCAL d
        PUSH_STR "FOO"
        DICT_HAS
        STORE_GLOBAL g_has

        ; Dict len -> 2
        LOAD_LOCAL d
        DICT_LEN
        STORE_GLOBAL g_len

        PUSH_0
        SYS_EXIT
    .endfunction
    """
    rc, out, err = assemble_and_run(src, verbose=True)
    assert rc == 0, f"Failed with rc={rc}, err={err}"
    assert "STORE_GLOBAL slot 0 <- 0x3333 (13107)" in out
    assert "STORE_GLOBAL slot 1 <- 0x2222 (8738)" in out
    assert "STORE_GLOBAL slot 2 <- 0x0001 (1)" in out
    assert "STORE_GLOBAL slot 3 <- 0x0002 (2)" in out
    print("  -> Dict operations OK.")


def test_strings_and_slices():
    print("Testing string slicing, stripping, and word-boundary replacement...")
    src = """
    .function main entry
        .local s: slice
        .local sub: slice
        .local rep: slice

        ; Substring slice: "Hello, World!"[0:5] -> "Hello"
        PUSH_STR "Hello, World!"
        STORE_LOCAL s

        LOAD_LOCAL s
        PUSH_0
        PUSH_I16 5
        SLICE_SUB
        STORE_LOCAL sub

        LOAD_LOCAL sub
        IO_PRINT

        ; Word-boundary replacement: replace DP in "  LDA DP,X ; DP_VAR" with "MY_DP"
        PUSH_STR "  LDA DP,X ; DP_VAR"
        PUSH_STR "DP"
        PUSH_STR "MY_DP"
        STR_REPLACE_IDENT
        STORE_LOCAL rep

        LOAD_LOCAL rep
        IO_PRINT

        PUSH_0
        SYS_EXIT
    .endfunction
    """
    rc, out, err = assemble_and_run(src, verbose=False)
    assert rc == 0, f"Failed with rc={rc}, err={err}"
    lines = out.strip().splitlines()
    assert lines[0] == "Hello", f"Expected 'Hello', got '{lines[0]}'"
    assert lines[1] == "  LDA MY_DP,X ; DP_VAR", f"Expected replaced line, got '{lines[1]}'"
    print("  -> String & slice operations OK.")


def test_file_io():
    print("Testing file I/O system calls...")
    test_txt_path = "/tmp/test_npvm_io.txt"
    if os.path.exists(test_txt_path):
        os.remove(test_txt_path)

    src = f"""
    .function main entry
        .local path: slice
        .local handle: scalar
        .local ok: scalar
        .local line: slice
        .local eof: scalar

        PUSH_STR "{test_txt_path}"
        STORE_LOCAL path

        ; 1. Open for write and write lines
        LOAD_LOCAL path
        FILE_OPEN_WRITE
        STORE_LOCAL ok
        STORE_LOCAL handle

        LOAD_LOCAL handle
        PUSH_STR "Line 1: NitrOS-9\\nLine 2: 6809\\n"
        FILE_WRITE
        STORE_LOCAL ok

        LOAD_LOCAL handle
        FILE_CLOSE

        ; 2. Test OS_ISFILE
        LOAD_LOCAL path
        OS_ISFILE
        NOT
        JUMP_IF_TRUE .L_error

        ; 3. Open for read and read line
        LOAD_LOCAL path
        FILE_OPEN_READ
        STORE_LOCAL ok
        STORE_LOCAL handle

        LOAD_LOCAL handle
        FILE_READLINE
        STORE_LOCAL eof
        STORE_LOCAL line

        LOAD_LOCAL line
        IO_PRINT

        LOAD_LOCAL handle
        FILE_CLOSE

        PUSH_0
        SYS_EXIT

    .L_error:
        PUSH_1
        SYS_EXIT
    .endfunction
    """
    try:
        rc, out, err = assemble_and_run(src, verbose=False)
        assert rc == 0, f"File I/O failed with rc={rc}, err={err}"
        assert "Line 1: NitrOS-9" in out, f"Expected 'Line 1: NitrOS-9', got:\n{out}"
        print("  -> File I/O OK.")
    finally:
        if os.path.exists(test_txt_path):
            os.remove(test_txt_path)


def test_verbose_tracing():
    print("Testing verbose tracing output (-v flag)...")
    src = """
    .global g_out: scalar

    .function main entry
        .local a: scalar
        .local b: scalar

        PUSH_I16 42
        STORE_LOCAL a

        PUSH_I16 58
        STORE_LOCAL b

        LOAD_LOCAL a
        LOAD_LOCAL b
        ADD
        STORE_GLOBAL g_out

        PUSH_0
        SYS_EXIT
    .endfunction
    """
    rc, out, err = assemble_and_run(src, verbose=True)
    assert rc == 0
    # Check that instruction execution is traced
    assert "[main+0000] PUSH_I16" in out or "PUSH_I16" in out
    assert "ADD" in out
    # Check that stores are explicitly printed
    assert "STORE_LOCAL slot 0 <- 0x002A (42)" in out
    assert "STORE_LOCAL slot 1 <- 0x003A (58)" in out
    assert "STORE_GLOBAL slot 0 <- 0x0064 (100)" in out
    print("  -> Verbose tracing OK.")


def test_addr_of_global_and_println():
    print("Testing ADDR_OF_GLOBAL and PRINTLN with Slice[any]...")
    src = """
    .global g_val: scalar
    .global g_buf: 32

    .function main entry
        .local pbuf: scalar
        .local any_buf: scalar

        ; Test ADDR_OF_GLOBAL
        ADDR_OF_GLOBAL g_val
        STORE_LOCAL pbuf

        ; Store 1234 into g_val via STORE_FIELD at pbuf
        LOAD_LOCAL pbuf
        PUSH_I16 1234
        STORE_FIELD 0

        ; Verify LOAD_GLOBAL returns 1234
        LOAD_GLOBAL g_val
        STORE_GLOBAL g_val

        ; Now test PRINTLN with Slice[any]
        ; Allocate 8 bytes for two 'any' entries (entry 0: int, entry 1: string)
        PUSH_I16 8
        BUF_ALLOC
        STORE_LOCAL any_buf

        ; Entry 0: BaseAddr = &g_val, TypeStr = "word"
        LOAD_LOCAL any_buf
        ADDR_OF_GLOBAL g_val
        STORE_FIELD 0

        LOAD_LOCAL any_buf
        PUSH_STR "word"
        POP
        POP
        STORE_FIELD 2

        ; Entry 1: BaseAddr = &g_buf, TypeStr = "string"
        ; Store "Hello" into g_buf as 3-word slice { text_ptr, 5, 5 }
        PUSH_STR "Hello"
        POP
        POP
        STORE_LOCAL pbuf  ; text_ptr
        ADDR_OF_GLOBAL g_buf
        LOAD_LOCAL pbuf
        STORE_FIELD 0     ; slice.base
        ADDR_OF_GLOBAL g_buf
        PUSH_I16 5
        STORE_FIELD 2     ; slice.cap
        ADDR_OF_GLOBAL g_buf
        PUSH_I16 5
        STORE_FIELD 4     ; slice.len

        LOAD_LOCAL any_buf
        ADDR_OF_GLOBAL g_buf
        STORE_FIELD 4     ; any[1].BaseAddr

        LOAD_LOCAL any_buf
        PUSH_STR "string"
        POP
        POP
        STORE_FIELD 6     ; any[1].TypeStr

        ; Push Slice[any] { any_buf, 2, 2 }
        LOAD_LOCAL any_buf
        PUSH_I16 2
        PUSH_I16 2
        PRINTLN

        LOAD_LOCAL any_buf
        BUF_FREE

        PUSH_0
        SYS_EXIT
    .endfunction
    """
    rc, out, err = assemble_and_run(src, verbose=False)
    assert rc == 0, f"Failed with rc={rc}, err={err}"
    assert "1234 Hello\n" in out, f"Expected '1234 Hello', got: {out!r}"
    print("  -> ADDR_OF_GLOBAL & PRINTLN OK.")


def main():
    print("=== Running NPCode VM Emulator Test Suite ===")
    test_basic_arithmetic()
    test_recursion_factorial()
    test_linear_dict()
    test_strings_and_slices()
    test_file_io()
    test_verbose_tracing()
    test_addr_of_global_and_println()
    print("\n=== All NPVM Emulator Tests Passed Successfully! ===")


if __name__ == "__main__":
    main()
