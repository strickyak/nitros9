#!/usr/bin/env python3
"""
npdis.py - Disassembler for the NPCode Virtual Machine.

Disassembles compiled NPCode bytecode (.npc) into human-readable assembly
or generates round-trippable assembly source code (.npasm).
Features:
  - Validates NPC header, magic, version, and section boundaries.
  - Decodes Global Variable Table and Local Variable Tables with type sizes.
  - Decodes and escapes String Pool entries.
  - Labels branch targets within functions (.L_XXXX).
  - Annotates string literals, function calls, local/global slots.
  - Supports `--asm` flag to emit 100% re-assemblable .npasm source code.
  - Supports `--details` to dump executable tables.
"""

import sys
import os
import struct
from typing import List, Dict, Optional, Tuple, Set

from opcodes import (
    MAGIC, FORMAT_VER, HEADER_SIZE, FUNC_ENTRY_SIZE,
    OPCODE_TABLE, FLAG_6309_NATIVE, FLAG_MMU_BANKED
)


class DisasmError(Exception):
    pass


class DisassembledInst:
    def __init__(self, offset_in_func: int, opcode: int, mnemonic: str,
                 arg_bytes: int, arg_type: str, raw_bytes: bytes,
                 operand_val: Optional[int] = None, operand_str: str = "",
                 comment: str = ""):
        self.offset_in_func = offset_in_func
        self.opcode = opcode
        self.mnemonic = mnemonic
        self.arg_bytes = arg_bytes
        self.arg_type = arg_type
        self.raw_bytes = raw_bytes
        self.operand_val = operand_val
        self.operand_str = operand_str
        self.comment = comment


class DisassembledFunc:
    def __init__(self, index: int, is_entry: bool, arg_count: int, local_count: int,
                 frame_size: int, code_offset: int, code_size: int,
                 var_sizes: List[int]):
        self.index = index
        self.name = f"main" if is_entry else f"fn_{index}"
        self.is_entry = is_entry
        self.arg_count = arg_count
        self.local_count = local_count
        self.frame_size = frame_size
        self.code_offset = code_offset
        self.code_size = code_size
        self.var_sizes = var_sizes
        self.instructions: List[DisassembledInst] = []
        self.branch_targets: Set[int] = set()


class Disassembler:
    def __init__(self, data: bytes):
        self.data = data
        self.format_ver = 0
        self.flags = 0
        self.string_pool_size = 0
        self.globals_count = 0
        self.func_count = 0
        self.entry_func_index = 0
        self.code_size = 0

        self.global_sizes: List[int] = []
        self.string_pool: Dict[int, str] = {}
        self.functions: List[DisassembledFunc] = []

        self._parse()

    def _parse(self):
        if len(self.data) < HEADER_SIZE:
            raise DisasmError(f"File too small for NPC header: {len(self.data)} bytes (expected >= {HEADER_SIZE})")

        # 1. Parse Header
        magic = self.data[0:4]
        if magic != MAGIC:
            raise DisasmError(f"Invalid magic: {magic!r} (expected {MAGIC!r})")

        self.format_ver = self.data[4]
        if self.format_ver != FORMAT_VER:
            raise DisasmError(f"Unsupported format version: {self.format_ver} (expected {FORMAT_VER})")

        self.flags = self.data[5]
        (
            self.string_pool_size,
            self.globals_count,
            self.func_count,
            self.entry_func_index,
            self.code_size
        ) = struct.unpack(">HHHHH", self.data[6:16])

        # Section Offsets
        gvar_offset = HEADER_SIZE
        gvar_size = self.globals_count * 2
        spool_offset = gvar_offset + gvar_size
        ftab_offset = spool_offset + self.string_pool_size
        ftab_size = self.func_count * FUNC_ENTRY_SIZE

        # Check bounds for Function Table
        if len(self.data) < ftab_offset + ftab_size:
            raise DisasmError("Truncated binary: unexpected EOF before Function Table end")

        # 2. Global Variable Table
        self.global_sizes = [
            struct.unpack_from(">H", self.data, gvar_offset + i * 2)[0]
            for i in range(self.globals_count)
        ]

        # 3. String Pool
        pool_bytes = self.data[spool_offset : spool_offset + self.string_pool_size]
        self._parse_string_pool(pool_bytes)

        # 4. Function Table
        ftab_bytes = self.data[ftab_offset : ftab_offset + ftab_size]
        raw_func_entries = []
        total_var_bytes = 0
        for i in range(self.func_count):
            entry_bytes = ftab_bytes[i * FUNC_ENTRY_SIZE : (i + 1) * FUNC_ENTRY_SIZE]
            (
                arg_count,
                local_count,
                frame_size,
                code_offset,
                f_code_size,
                var_table_offset
            ) = struct.unpack(">BBHHHH", entry_bytes)
            raw_func_entries.append((arg_count, local_count, frame_size, code_offset, f_code_size, var_table_offset))
            total_var_bytes += (arg_count + local_count)

        # 5. Local Variable Tables
        ltab_offset = ftab_offset + ftab_size
        ltab_bytes = self.data[ltab_offset : ltab_offset + total_var_bytes]

        for i, (arg_count, local_count, frame_size, code_offset, f_code_size, v_off) in enumerate(raw_func_entries):
            var_count = arg_count + local_count
            v_sizes = list(ltab_bytes[v_off : v_off + var_count])
            is_entry = (i == self.entry_func_index)
            f = DisassembledFunc(i, is_entry, arg_count, local_count, frame_size, code_offset, f_code_size, v_sizes)
            self.functions.append(f)

        # 6. Bytecode Section
        code_start_offset = ltab_offset + total_var_bytes
        code_bytes = self.data[code_start_offset : code_start_offset + self.code_size]
        if len(code_bytes) < self.code_size:
            raise DisasmError(f"Truncated bytecode section: got {len(code_bytes)} bytes, expected {self.code_size}")

        # Disassemble each function
        for f in self.functions:
            f_code = code_bytes[f.code_offset : f.code_offset + f.code_size]
            self._disassemble_func(f, f_code)

    def _parse_string_pool(self, pool_bytes: bytes):
        idx = 0
        n = len(pool_bytes)
        while idx + 2 <= n:
            length = struct.unpack(">H", pool_bytes[idx : idx + 2])[0]
            if idx + 2 + length > n:
                break
            text_bytes = pool_bytes[idx + 2 : idx + 2 + length]
            # Try decoding as utf-8, fallback to latin-1
            try:
                s = text_bytes.decode("utf-8")
            except UnicodeDecodeError:
                s = text_bytes.decode("latin-1")
            self.string_pool[idx] = s
            # Skip [len: 2] + [chars: length] + [null_term: 1]
            idx += 2 + length + 1

    def _disassemble_func(self, f: DisassembledFunc, code: bytes):
        pc = 0
        code_len = len(code)

        # Pass 1: Parse instructions and record branch targets
        while pc < code_len:
            inst_offset = pc
            opcode_byte = code[pc]
            pc += 1

            if opcode_byte not in OPCODE_TABLE:
                # Unknown opcode: treat as raw byte
                dinst = DisassembledInst(inst_offset, opcode_byte, f".BYTE", 0, "none",
                                         bytes([opcode_byte]), operand_val=opcode_byte,
                                         operand_str=f"${opcode_byte:02X}")
                f.instructions.append(dinst)
                continue

            mnemonic, arg_bytes, arg_type, desc = OPCODE_TABLE[opcode_byte]

            if pc + arg_bytes > code_len:
                # Truncated instruction
                raw = code[inst_offset:]
                dinst = DisassembledInst(inst_offset, opcode_byte, f".BYTE", 0, "none",
                                         raw, operand_str=f"${opcode_byte:02X}")
                f.instructions.append(dinst)
                break

            raw = code[inst_offset : pc + arg_bytes]
            operand_val = None
            operand_str = ""
            comment = ""

            if arg_bytes == 1:
                b0 = code[pc]
                pc += 1
                if arg_type == "imm8_s":
                    operand_val = struct.unpack(">b", bytes([b0]))[0]
                    operand_str = str(operand_val)
                else:
                    operand_val = b0
                    operand_str = str(b0)
                    if arg_type == "local8":
                        var_size = f.var_sizes[b0] if b0 < len(f.var_sizes) else 2
                        type_str = "scalar" if var_size == 2 else ("slice" if var_size == 6 else f"{var_size}B")
                        comment = f"slot {b0} ({type_str})"

            elif arg_bytes == 2:
                w_bytes = code[pc : pc + 2]
                pc += 2
                if arg_type == "rel16":
                    rel = struct.unpack(">h", w_bytes)[0]
                    operand_val = rel
                    target = (inst_offset + 3) + rel
                    f.branch_targets.add(target)
                    operand_str = f".L_{target:04X}"
                    comment = f"offset {rel:+d}"
                elif arg_type == "str16":
                    str_off = struct.unpack(">H", w_bytes)[0]
                    operand_val = str_off
                    str_val = self.string_pool.get(str_off, None)
                    if str_val is not None:
                        escaped = self._escape_str(str_val)
                        operand_str = f'"{escaped}"'
                        comment = f"str @ ${str_off:04X}"
                    else:
                        operand_str = f"${str_off:04X}"
                elif arg_type == "func16":
                    fn_idx = struct.unpack(">H", w_bytes)[0]
                    operand_val = fn_idx
                    target_name = f"main" if fn_idx == self.entry_func_index else f"fn_{fn_idx}"
                    operand_str = target_name
                    comment = f"func index {fn_idx}"
                elif arg_type == "global16":
                    g_idx = struct.unpack(">H", w_bytes)[0]
                    operand_val = g_idx
                    g_size = self.global_sizes[g_idx] if g_idx < len(self.global_sizes) else 2
                    type_str = "scalar" if g_size == 2 else ("slice" if g_size == 6 else f"{g_size}B")
                    operand_str = f"g_{g_idx}"
                    comment = f"global {g_idx} ({type_str})"
                else:
                    # Generic imm16
                    u16 = struct.unpack(">H", w_bytes)[0]
                    operand_val = u16
                    operand_str = f"${u16:04X}" if u16 >= 10 else str(u16)

            # Annotations for fast local opcodes (LOAD_LOCAL_0..3, STORE_LOCAL_0..3)
            if mnemonic.startswith("LOAD_LOCAL_") or mnemonic.startswith("STORE_LOCAL_"):
                slot_num = int(mnemonic.split("_")[-1])
                var_size = f.var_sizes[slot_num] if slot_num < len(f.var_sizes) else 2
                type_str = "scalar" if var_size == 2 else ("slice" if var_size == 6 else f"{var_size}B")
                comment = f"slot {slot_num} ({type_str})"

            dinst = DisassembledInst(inst_offset, opcode_byte, mnemonic, arg_bytes, arg_type,
                                     raw, operand_val, operand_str, comment)
            f.instructions.append(dinst)

    @staticmethod
    def _escape_str(s: str) -> str:
        res = []
        for c in s:
            if c == "\n":
                res.append("\\n")
            elif c == "\r":
                res.append("\\r")
            elif c == "\t":
                res.append("\\t")
            elif c == "\\":
                res.append("\\\\")
            elif c == '"':
                res.append('\\"')
            elif 32 <= ord(c) <= 126:
                res.append(c)
            else:
                res.append(f"\\x{ord(c):02x}")
        return "".join(res)

    def print_details(self):
        """Prints complete header, string pool, and variable tables information."""
        print("=" * 80)
        print("NPCode Binary Executable Details")
        print("=" * 80)
        print(f"Format Version:    {self.format_ver}")
        print(f"Flags:             ${self.flags:02X} (6309_native={bool(self.flags & FLAG_6309_NATIVE)}, banked={bool(self.flags & FLAG_MMU_BANKED)})")
        print(f"String Pool Size:  {self.string_pool_size} bytes ({len(self.string_pool)} strings)")
        print(f"Globals Count:     {self.globals_count}")
        print(f"Function Count:    {self.func_count}")
        print(f"Entry Function:    {self.entry_func_index}")
        print(f"Bytecode Size:     {self.code_size} bytes")

        print("\n--- Global Variable Table ---")
        for i, sz in enumerate(self.global_sizes):
            type_str = "scalar" if sz == 2 else ("slice" if sz == 6 else f"{sz}B")
            print(f"  Global {i:<3}: size = {sz} bytes ({type_str})")

        print("\n--- String Pool ---")
        for off, s in sorted(self.string_pool.items()):
            escaped = self._escape_str(s)
            print(f"  Offset ${off:04X} (len {len(s)}): \"{escaped}\"")

        print("\n--- Function Table ---")
        for f in self.functions:
            entry_str = " [ENTRY]" if f.is_entry else ""
            print(f"  Function {f.index} '{f.name}'{entry_str}:")
            print(f"    Args: {f.arg_count}, Locals: {f.local_count}, Frame: {f.frame_size}B")
            print(f"    Code Offset: ${f.code_offset:04X}, Code Size: {f.code_size}B")
            for j, sz in enumerate(f.var_sizes):
                role = "param" if j < f.arg_count else "local"
                slot_in_role = j if j < f.arg_count else (j - f.arg_count)
                type_str = "scalar" if sz == 2 else ("slice" if sz == 6 else f"{sz}B")
                print(f"      {role} {slot_in_role} (slot {j}): size = {sz}B ({type_str})")
        print("=" * 80)

    def print_disassembly(self):
        """Prints a rich, formatted disassembly listing with hex and annotations."""
        print("=" * 80)
        print("NPCode Disassembly")
        print("=" * 80)
        for f in self.functions:
            entry_tag = " [ENTRY]" if f.is_entry else ""
            print(f"\n; Function {f.name}{entry_tag} (args={f.arg_count}, locals={f.local_count}, frame={f.frame_size}B)")
            print(f".function {f.name}{' entry' if f.is_entry else ''}")
            for j in range(f.arg_count):
                sz = f.var_sizes[j]
                t_str = "scalar" if sz == 2 else ("slice" if sz == 6 else str(sz))
                print(f"    .param p_{j}: {t_str}")
            for j in range(f.local_count):
                idx = f.arg_count + j
                sz = f.var_sizes[idx]
                t_str = "scalar" if sz == 2 else ("slice" if sz == 6 else str(sz))
                print(f"    .local l_{j}: {t_str}")

            for inst in f.instructions:
                # Check if this offset is a branch target
                if inst.offset_in_func in f.branch_targets:
                    print(f".L_{inst.offset_in_func:04X}:")

                hex_bytes = " ".join(f"{b:02X}" for b in inst.raw_bytes)
                comment_str = f" ; {inst.comment}" if inst.comment else ""
                print(f"  {inst.offset_in_func:04X}  {hex_bytes:<8}  {inst.mnemonic:<18} {inst.operand_str:<16}{comment_str}")

            print(".endfunction")
        print("=" * 80)

    def generate_asm_source(self) -> str:
        """Generates pure, re-assemblable .npasm source code."""
        lines = []
        lines.append("; ====================================================================")
        lines.append("; Disassembled by npdis.py")
        lines.append("; ====================================================================")
        lines.append("")

        # 1. Global declarations
        if self.global_sizes:
            lines.append("; Globals")
            for i, sz in enumerate(self.global_sizes):
                type_str = "scalar" if sz == 2 else ("slice" if sz == 6 else str(sz))
                lines.append(f".global g_{i}: {type_str}")
            lines.append("")

        # 2. Functions
        for f in self.functions:
            entry_attr = " entry" if f.is_entry else ""
            lines.append(f".function {f.name}{entry_attr}")

            # Parameters
            for j in range(f.arg_count):
                sz = f.var_sizes[j]
                type_str = "scalar" if sz == 2 else ("slice" if sz == 6 else str(sz))
                lines.append(f"    .param p_{j}: {type_str}")

            # Locals
            for j in range(f.local_count):
                idx = f.arg_count + j
                sz = f.var_sizes[idx]
                type_str = "scalar" if sz == 2 else ("slice" if sz == 6 else str(sz))
                lines.append(f"    .local l_{j}: {type_str}")

            # Instructions
            for inst in f.instructions:
                if inst.offset_in_func in f.branch_targets:
                    lines.append(f".L_{inst.offset_in_func:04X}:")

                # Map local/global slot operands back to friendly variable names if possible
                op_str = inst.operand_str
                if inst.arg_type == "local8" and inst.operand_val is not None:
                    slot = inst.operand_val
                    if slot < f.arg_count:
                        op_str = f"p_{slot}"
                    elif slot < f.arg_count + f.local_count:
                        op_str = f"l_{slot - f.arg_count}"
                elif inst.arg_type == "global16" and inst.operand_val is not None:
                    op_str = f"g_{inst.operand_val}"

                if op_str:
                    lines.append(f"    {inst.mnemonic:<16} {op_str}")
                else:
                    lines.append(f"    {inst.mnemonic}")

            lines.append(".endfunction")
            lines.append("")

        return "\n".join(lines)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: npdis.py <input.npc> [-o <output.npasm>] [--asm] [--details]")
        sys.exit(0)

    input_file = sys.argv[1]
    output_file = None
    emit_asm = False
    show_details = False

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "-o" and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
            i += 2
        elif arg == "--asm":
            emit_asm = True
            i += 1
        elif arg in ("--details", "-v"):
            show_details = True
            i += 1
        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)

    try:
        with open(input_file, "rb") as f:
            binary_data = f.read()
    except Exception as e:
        print(f"Error reading '{input_file}': {e}")
        sys.exit(1)

    try:
        disasm = Disassembler(binary_data)
    except DisasmError as e:
        print(f"Disassembly Error: {e}")
        sys.exit(1)

    if show_details:
        disasm.print_details()

    if emit_asm:
        asm_code = disasm.generate_asm_source()
        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(asm_code)
                print(f"Wrote assembly source to '{output_file}'.")
            except Exception as e:
                print(f"Error writing to '{output_file}': {e}")
                sys.exit(1)
        else:
            print(asm_code)
    else:
        disasm.print_disassembly()


if __name__ == "__main__":
    main()
