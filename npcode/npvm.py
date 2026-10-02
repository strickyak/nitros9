#!/usr/bin/env python3
"""
npvm.py - Virtual Machine Emulator for NPCode Bytecode (.npc).

Faithfully executes NPCode binaries with:
  - 16-bit untagged word operand stack.
  - 3-word slices { pointer, capacity, length } for strings, lists, and dicts.
  - Linear unhashed dictionary operations.
  - Explicit heap management for fixed-size buffers (BUF_ALLOC, BUF_FREE).
  - Variable-table-driven local and global variable loads/stores.
  - Built-in OS and filesystem calls.
  - Verbose execution tracing (-v) printing executed instructions and stored values.
"""

import sys
import os
import struct
from typing import List, Dict, Optional, Tuple, Any

from opcodes import (
    MAGIC, FORMAT_VER, HEADER_SIZE, FUNC_ENTRY_SIZE,
    OPCODE_TABLE, FLAG_6309_NATIVE, FLAG_MMU_BANKED
)


class VMError(Exception):
    def __init__(self, message: str, pc: Optional[int] = None, func_name: Optional[str] = None):
        self.message = message
        self.pc = pc
        self.func_name = func_name
        super().__init__(self.__str__())

    def __str__(self) -> str:
        ctx = ""
        if self.func_name:
            ctx += f" in function '{self.func_name}'"
        if self.pc is not None:
            ctx += f" at PC 0x{self.pc:04X}"
        return f"VM Error{ctx}: {self.message}"


class FunctionMetadata:
    def __init__(self, index: int, is_entry: bool, arg_count: int, local_count: int,
                 frame_size: int, code_offset: int, code_size: int,
                 var_sizes: List[int]):
        self.index = index
        self.name = "main" if is_entry else f"fn_{index}"
        self.is_entry = is_entry
        self.arg_count = arg_count
        self.local_count = local_count
        self.frame_size = frame_size
        self.code_offset = code_offset
        self.code_size = code_size
        self.var_sizes = var_sizes


class CallFrame:
    def __init__(self, func: FunctionMetadata, return_pc: int, return_func: Optional[FunctionMetadata], frame_addr: int = 0):
        self.func = func
        self.return_pc = return_pc
        self.return_func = return_func
        self.frame_addr = frame_addr
        # Local variable storage by slot index (slot -> list of 16-bit words)
        self.slots: List[List[int]] = []
        for sz in func.var_sizes:
            word_count = (sz + 1) // 2
            self.slots.append([0] * word_count)


class HeapManager:
    """Manages dynamic fixed-size buffer allocations in the VM memory space."""
    def __init__(self, memory: bytearray, heap_start: int, heap_end: int):
        self.memory = memory
        self.heap_start = (heap_start + 3) & ~3  # align 4 bytes
        self.heap_end = heap_end
        # Simple block allocator: block = [size: uint16, is_free: uint16, data...]
        self.allocations: Dict[int, int] = {}  # addr -> size
        self._init_heap()

    def _init_heap(self):
        # Format initial free block covering the entire heap
        total_size = self.heap_end - self.heap_start
        if total_size < 8:
            return
        struct.pack_into(">HH", self.memory, self.heap_start, total_size, 1)  # size, is_free=1

    def alloc(self, size: int) -> int:
        if size <= 0:
            size = 2
        # Align size to 2 bytes, add 4 bytes header [size: uint16, is_free: uint16]
        req_size = ((size + 1) & ~1) + 4
        curr = self.heap_start

        while curr + 4 <= self.heap_end:
            blk_size, is_free = struct.unpack_from(">HH", self.memory, curr)
            if blk_size == 0 or blk_size > (self.heap_end - curr):
                break
            if is_free == 1 and blk_size >= req_size:
                # Split block if remaining space is at least 8 bytes
                rem = blk_size - req_size
                if rem >= 8:
                    struct.pack_into(">HH", self.memory, curr, req_size, 0)
                    struct.pack_into(">HH", self.memory, curr + req_size, rem, 1)
                else:
                    struct.pack_into(">HH", self.memory, curr, blk_size, 0)

                data_addr = curr + 4
                self.allocations[data_addr] = req_size - 4
                return data_addr

            curr += blk_size

        # Out of memory
        return 0

    def free(self, data_addr: int):
        if data_addr not in self.allocations:
            return  # invalid or double free
        blk_addr = data_addr - 4
        del self.allocations[data_addr]
        # Mark free
        blk_size = struct.unpack_from(">H", self.memory, blk_addr)[0]
        struct.pack_into(">H", self.memory, blk_addr + 2, 1)

        # Coalesce adjacent free blocks
        self._coalesce()

    def _coalesce(self):
        curr = self.heap_start
        while curr + 4 <= self.heap_end:
            blk_size, is_free = struct.unpack_from(">HH", self.memory, curr)
            if blk_size == 0 or curr + blk_size >= self.heap_end:
                break
            next_blk = curr + blk_size
            next_size, next_free = struct.unpack_from(">HH", self.memory, next_blk)
            if is_free == 1 and next_free == 1:
                # Merge
                merged_size = blk_size + next_size
                struct.pack_into(">H", self.memory, curr, merged_size)
            else:
                curr = next_blk


class NPVM:
    def __init__(self, binary_data: bytes, verbose: bool = False, cli_args: Optional[List[str]] = None):
        self.raw_binary = binary_data
        self.verbose = verbose
        self.cli_args = cli_args or []

        # 64 KB VM address space
        self.memory = bytearray(65536)

        # Header metadata
        self.format_ver = 0
        self.flags = 0
        self.string_pool_size = 0
        self.globals_count = 0
        self.func_count = 0
        self.entry_func_index = 0
        self.code_size = 0

        # Memory layout offsets
        self.spool_base = 0
        self.code_base = 0
        self.heap_base = 0

        # Variable tables & functions
        self.global_sizes: List[int] = []
        self.global_addrs: List[int] = []
        self.global_slots: List[List[int]] = []  # slot -> list of 16-bit words
        self.functions: List[FunctionMetadata] = []
        self.string_pool_entries: Dict[int, str] = {}

        # Execution state
        self.stack: List[int] = []  # 16-bit words
        self.call_stack: List[CallFrame] = []
        self.current_frame: Optional[CallFrame] = None
        self.pc = 0  # relative to Bytecode Section start
        self.running = False
        self.exit_code = 0
        self.instruction_count = 0

        # File I/O descriptors
        self.open_files: Dict[int, Any] = {
            0: sys.stdin,
            1: sys.stdout,
            2: sys.stderr
        }
        self.next_file_handle = 3

        self._load_binary()
        self.heap = HeapManager(self.memory, self.heap_base, 0xFFFF)

    def _load_binary(self):
        if len(self.raw_binary) < HEADER_SIZE:
            raise VMError("Binary smaller than header")

        magic = self.raw_binary[0:4]
        if magic != MAGIC:
            raise VMError(f"Invalid NPC magic: {magic!r}")

        self.format_ver = self.raw_binary[4]
        self.flags = self.raw_binary[5]
        (
            self.string_pool_size,
            self.globals_count,
            self.func_count,
            self.entry_func_index,
            self.code_size
        ) = struct.unpack(">HHHHH", self.raw_binary[6:16])

        # Calculate section offsets in binary
        gvar_off = HEADER_SIZE
        gvar_size = self.globals_count * 2
        spool_off = gvar_off + gvar_size
        ftab_off = spool_off + self.string_pool_size
        ftab_size = self.func_count * FUNC_ENTRY_SIZE

        # Global Variable Table (16-bit size per global)
        self.global_sizes = [
            struct.unpack_from(">H", self.raw_binary, gvar_off + i * 2)[0]
            for i in range(self.globals_count)
        ]

        # Copy String Pool into VM memory
        self.spool_base = 0x0100  # Start string pool at 256
        self.memory[self.spool_base : self.spool_base + self.string_pool_size] = self.raw_binary[spool_off : spool_off + self.string_pool_size]

        # Globals Data Section in VM memory
        self.globals_base = self.spool_base + self.string_pool_size
        self.global_addrs = []
        curr_g = self.globals_base
        for sz in self.global_sizes:
            self.global_addrs.append(curr_g)
            curr_g += sz
        self.globals_end = curr_g

        # Parse string pool entries for disassembly/tracing
        self._parse_string_pool(self.spool_base, self.string_pool_size)

        # Parse Function Table
        raw_func_entries = []
        total_var_bytes = 0
        for i in range(self.func_count):
            entry_bytes = self.raw_binary[ftab_off + i * FUNC_ENTRY_SIZE : ftab_off + (i + 1) * FUNC_ENTRY_SIZE]
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

        # Local Variable Tables
        ltab_off = ftab_off + ftab_size
        ltab_bytes = self.raw_binary[ltab_off : ltab_off + total_var_bytes]

        for i, (arg_count, local_count, frame_size, code_offset, f_code_size, v_off) in enumerate(raw_func_entries):
            var_count = arg_count + local_count
            v_sizes = list(ltab_bytes[v_off : v_off + var_count])
            is_entry = (i == self.entry_func_index)
            f = FunctionMetadata(i, is_entry, arg_count, local_count, frame_size, code_offset, f_code_size, v_sizes)
            self.functions.append(f)

        # Copy Bytecode Section into VM memory (after globals)
        code_src_off = ltab_off + total_var_bytes
        self.code_base = (self.globals_end + 15) & ~15
        self.memory[self.code_base : self.code_base + self.code_size] = self.raw_binary[code_src_off : code_src_off + self.code_size]

        # Heap starts right after bytecode
        self.heap_base = (self.code_base + self.code_size + 15) & ~15

    def _parse_string_pool(self, base: int, size: int):
        idx = 0
        while idx + 2 <= size:
            length = struct.unpack_from(">H", self.memory, base + idx)[0]
            if idx + 2 + length > size:
                break
            text_bytes = bytes(self.memory[base + idx + 2 : base + idx + 2 + length])
            try:
                s = text_bytes.decode("utf-8")
            except UnicodeDecodeError:
                s = text_bytes.decode("latin-1")
            self.string_pool_entries[idx] = s
            idx += 2 + length + 1

    def run(self, max_instructions: Optional[int] = None) -> int:
        """Starts VM execution from entry function."""
        if not self.functions:
            return 0

        self.frame_sp = 0xE000
        entry_func = self.functions[self.entry_func_index]
        self.frame_sp -= entry_func.frame_size
        self.memory[self.frame_sp : self.frame_sp + entry_func.frame_size] = b"\x00" * entry_func.frame_size
        self.current_frame = CallFrame(entry_func, return_pc=-1, return_func=None, frame_addr=self.frame_sp)
        self.call_stack.append(self.current_frame)
        self.pc = entry_func.code_offset
        self.running = True

        while self.running:
            if max_instructions and self.instruction_count >= max_instructions:
                raise VMError(f"Instruction limit reached: {max_instructions}", self.pc, self.current_frame.func.name)

            self.step()

        return self.exit_code

    def step(self):
        """Fetches, decodes, and executes a single instruction."""
        if not self.current_frame:
            self.running = False
            return

        inst_pc = self.pc
        if inst_pc >= self.code_size:
            self.running = False
            return

        # Fetch opcode
        opcode = self.memory[self.code_base + self.pc]
        self.pc += 1

        if opcode not in OPCODE_TABLE:
            raise VMError(f"Illegal opcode: 0x{opcode:02X}", inst_pc, self.current_frame.func.name)

        mnemonic, arg_bytes, arg_type, desc = OPCODE_TABLE[opcode]

        # Fetch immediate arguments
        arg_val = None
        if arg_bytes == 1:
            raw_b = self.memory[self.code_base + self.pc]
            self.pc += 1
            if arg_type == "imm8_s":
                arg_val = struct.unpack(">b", bytes([raw_b]))[0]
            else:
                arg_val = raw_b
        elif arg_bytes == 2:
            raw_w = self.memory[self.code_base + self.pc : self.code_base + self.pc + 2]
            self.pc += 2
            if arg_type == "rel16":
                arg_val = struct.unpack(">h", raw_w)[0]
            else:
                arg_val = struct.unpack(">H", raw_w)[0]

        self.instruction_count += 1

        # Trace instruction in verbose mode
        if self.verbose:
            self._trace_inst(inst_pc, mnemonic, arg_val, arg_type)

        # Execute instruction
        self._dispatch(opcode, mnemonic, arg_val, inst_pc)

    def _trace_inst(self, inst_pc: int, mnemonic: str, arg_val: Optional[int], arg_type: str):
        fn_name = self.current_frame.func.name
        rel_pc = inst_pc - self.current_frame.func.code_offset
        arg_str = ""
        if arg_val is not None:
            if arg_type == "rel16":
                target = rel_pc + 3 + arg_val
                arg_str = f".L_{target:04X} ({arg_val:+d})"
            elif arg_type == "str16":
                s = self.string_pool_entries.get(arg_val, "")
                arg_str = f'"{s}"'
            elif arg_type == "func16":
                target_fn = self.functions[arg_val].name if arg_val < len(self.functions) else str(arg_val)
                arg_str = target_fn
            else:
                arg_str = f"${arg_val:04X}" if arg_val >= 10 else str(arg_val)

        stack_preview = ", ".join(f"${w:04X}" for w in self.stack[-3:]) if self.stack else "empty"
        print(f"[{fn_name}+{rel_pc:04X}] {mnemonic:<16} {arg_str:<16} | Stack: [{stack_preview}]")

    def _push(self, val: int):
        self.stack.append(val & 0xFFFF)

    def _pop(self) -> int:
        if not self.stack:
            raise VMError("Operand stack underflow", self.pc, self.current_frame.func.name)
        return self.stack.pop()

    def _push_slice(self, ptr: int, cap: int, length: int):
        self._push(ptr)
        self._push(cap)
        self._push(length)

    def _pop_slice(self) -> Tuple[int, int, int]:
        length = self._pop()
        cap = self._pop()
        ptr = self._pop()
        return ptr, cap, length

    def _format_value(self, words: List[int]) -> str:
        """Formats words for verbose store output."""
        if len(words) == 1:
            u16 = words[0]
            s16 = struct.unpack(">h", struct.pack(">H", u16))[0]
            return f"0x{u16:04X} ({s16})"
        elif len(words) == 3:
            ptr, cap, length = words
            # Try inspecting as string
            str_repr = ""
            if ptr != 0 and length > 0 and (ptr + length <= len(self.memory)):
                text = bytes(self.memory[ptr : ptr + length])
                try:
                    str_repr = f': "{text.decode()}"'
                except UnicodeDecodeError:
                    str_repr = f": bytes({length})"
            return f"slice(ptr=0x{ptr:04X}, cap={cap}, len={length}{str_repr})"
        return "[" + ", ".join(f"0x{w:04X}" for w in words) + "]"

    def _dispatch(self, opcode: int, mnemonic: str, arg: Optional[int], inst_pc: int):
        # -------------------------------------------------------------
        # Group 1: Stack & Literals (0x00 .. 0x1F)
        # -------------------------------------------------------------
        if opcode == 0x00:  # NOP
            pass
        elif opcode == 0x01:  # PUSH_NIL
            self._push(0x0000)
        elif opcode == 0x02:  # PUSH_NIL_SLICE
            self._push_slice(0, 0, 0)
        elif opcode == 0x03:  # PUSH_TRUE
            self._push(0x0001)
        elif opcode == 0x04:  # PUSH_FALSE
            self._push(0x0000)
        elif opcode == 0x05:  # PUSH_0
            self._push(0x0000)
        elif opcode == 0x06:  # PUSH_1
            self._push(0x0001)
        elif opcode == 0x07:  # PUSH_NEG1
            self._push(0xFFFF)
        elif opcode in (0x08, 0x09, 0x0A):  # PUSH_I8, PUSH_U8, PUSH_I16
            self._push(arg)
        elif opcode == 0x0B:  # PUSH_STR
            str_off = arg
            entry_addr = self.spool_base + str_off
            length = struct.unpack_from(">H", self.memory, entry_addr)[0]
            text_addr = entry_addr + 2
            self._push_slice(text_addr, length, length)
        elif opcode == 0x0C:  # POP
            self._pop()
        elif opcode == 0x0D:  # POP_SLICE
            self._pop_slice()
        elif opcode == 0x0E:  # DUP
            w = self._pop()
            self._push(w)
            self._push(w)
        elif opcode == 0x0F:  # SWAP
            b = self._pop()
            a = self._pop()
            self._push(b)
            self._push(a)

        # -------------------------------------------------------------
        # Group 2: Variables & Buffers (0x20 .. 0x3F)
        # -------------------------------------------------------------
        elif 0x20 <= opcode <= 0x23:  # LOAD_LOCAL_0..3
            slot = opcode - 0x20
            self._load_local(slot)
        elif 0x24 <= opcode <= 0x27:  # STORE_LOCAL_0..3
            slot = opcode - 0x24
            self._store_local(slot)
        elif opcode == 0x28:  # LOAD_LOCAL
            self._load_local(arg)
        elif opcode == 0x29:  # STORE_LOCAL
            self._store_local(arg)
        elif opcode == 0x2A:  # LOAD_GLOBAL
            self._load_global(arg)
        elif opcode == 0x2B:  # STORE_GLOBAL
            self._store_global(arg)
        elif opcode == 0x2C:  # BUF_ALLOC
            size = self._pop()
            addr = self.heap.alloc(size)
            self._push(addr)
        elif opcode == 0x2D:  # BUF_FREE
            addr = self._pop()
            self.heap.free(addr)
        elif opcode == 0x2E:  # LOAD_FIELD
            obj_ptr = self._pop()
            val = struct.unpack_from(">H", self.memory, obj_ptr + arg)[0]
            self._push(val)
        elif opcode == 0x2F:  # STORE_FIELD
            val = self._pop()
            obj_ptr = self._pop()
            struct.pack_into(">H", self.memory, obj_ptr + arg, val)
            if self.verbose:
                print(f"       -> STORE_FIELD offset {arg} at 0x{obj_ptr:04X} <- 0x{val:04X}")
        elif opcode == 0x30:  # ADDR_OF_GLOBAL
            addr = self.global_addrs[arg]
            self._push(addr)
            if self.verbose:
                print(f"       -> ADDR_OF_GLOBAL slot {arg} => 0x{addr:04X}")
        elif opcode == 0x31:  # PEEK2
            addr = self._pop()
            val = struct.unpack_from(">H", self.memory, addr)[0]
            self._push(val)
            if self.verbose:
                print(f"       -> PEEK2 at 0x{addr:04X} => 0x{val:04X}")
        elif opcode == 0x32:  # POKE2
            val = self._pop()
            addr = self._pop()
            struct.pack_into(">H", self.memory, addr, val)
            if self.verbose:
                print(f"       -> POKE2 at 0x{addr:04X} <- 0x{val:04X}")
        elif opcode == 0x33:  # PEEK1
            addr = self._pop()
            val = self.memory[addr]
            self._push(val)
            if self.verbose:
                print(f"       -> PEEK1 at 0x{addr:04X} => 0x{val:02X}")
        elif opcode == 0x34:  # POKE1
            val = self._pop()
            addr = self._pop()
            self.memory[addr] = val & 0xFF
            if self.verbose:
                print(f"       -> POKE1 at 0x{addr:04X} <- 0x{val & 0xFF:02X}")
        elif opcode == 0x35:  # ADDR_OF_LOCAL
            offset = sum(self.current_frame.func.var_sizes[:arg])
            addr = self.current_frame.frame_addr + offset
            self._push(addr)
            if self.verbose:
                print(f"       -> ADDR_OF_LOCAL slot {arg} => 0x{addr:04X}")
        elif opcode == 0x36:  # SHL1_ADD
            index = self._pop()
            base = self._pop()
            res = (base + (index << 1)) & 0xFFFF
            self._push(res)
            if self.verbose:
                print(f"       -> SHL1_ADD base 0x{base:04X} + (index {index} << 1) => 0x{res:04X}")
        elif opcode == 0x37:  # ZALLOC
            size = self._pop()
            addr = self.heap.alloc(size)
            if addr != 0:
                self.memory[addr : addr + size] = b"\x00" * size
            self._push(addr)
            if self.verbose:
                print(f"       -> ZALLOC size {size} => 0x{addr:04X}")

        # -------------------------------------------------------------
        # Group 3: Arithmetic, Logic & Comparisons (0x40 .. 0x5F)
        # -------------------------------------------------------------
        elif opcode == 0x40:  # ADD
            b = self._pop()
            a = self._pop()
            self._push((a + b) & 0xFFFF)
        elif opcode == 0x41:  # SUB
            b = self._pop()
            a = self._pop()
            self._push((a - b) & 0xFFFF)
        elif opcode == 0x42:  # MUL
            b = self._pop()
            a = self._pop()
            self._push((a * b) & 0xFFFF)
        elif opcode == 0x43:  # DIV
            b = self._pop()
            a = self._pop()
            if b == 0:
                raise VMError("Division by zero", inst_pc, self.current_frame.func.name)
            self._push(a // b)
        elif opcode == 0x44:  # MOD
            b = self._pop()
            a = self._pop()
            if b == 0:
                raise VMError("Modulo by zero", inst_pc, self.current_frame.func.name)
            self._push(a % b)
        elif opcode == 0x45:  # NEG
            a = self._pop()
            self._push((-a) & 0xFFFF)
        elif opcode == 0x46:  # BIT_AND
            b = self._pop()
            a = self._pop()
            self._push(a & b)
        elif opcode == 0x47:  # BIT_OR
            b = self._pop()
            a = self._pop()
            self._push(a | b)
        elif opcode == 0x48:  # BIT_XOR
            b = self._pop()
            a = self._pop()
            self._push(a ^ b)
        elif opcode == 0x49:  # BIT_NOT
            a = self._pop()
            self._push((~a) & 0xFFFF)
        elif opcode == 0x4A:  # SHL
            b = self._pop() & 15
            a = self._pop()
            self._push((a << b) & 0xFFFF)
        elif opcode == 0x4B:  # SHR
            b = self._pop() & 15
            a = self._pop()
            self._push((a & 0xFFFF) >> b)
        elif opcode == 0x4C:  # CMP_EQ
            b = self._pop()
            a = self._pop()
            self._push(1 if a == b else 0)
        elif opcode == 0x4D:  # CMP_NE
            b = self._pop()
            a = self._pop()
            self._push(1 if a != b else 0)
        elif opcode == 0x4E:  # CMP_LT
            b = self._pop()
            a = self._pop()
            self._push(1 if a < b else 0)
        elif opcode == 0x4F:  # CMP_LE
            b = self._pop()
            a = self._pop()
            self._push(1 if a <= b else 0)
        elif opcode == 0x50:  # CMP_GT
            b = self._pop()
            a = self._pop()
            self._push(1 if a > b else 0)
        elif opcode == 0x51:  # CMP_GE
            b = self._pop()
            a = self._pop()
            self._push(1 if a >= b else 0)
        elif opcode == 0x52:  # NOT
            a = self._pop()
            self._push(1 if a == 0 else 0)
        elif opcode == 0x53:  # MIN
            b = self._pop()
            a = self._pop()
            self._push(min(a, b))
        elif opcode == 0x54:  # MAX
            b = self._pop()
            a = self._pop()
            self._push(max(a, b))
        elif opcode == 0x55:  # PARSE_INT
            radix = self._pop()
            kptr, kcap, klen = self._pop_slice()
            s = self._read_string(kptr, klen)
            try:
                val = int(s, radix if radix != 0 else 0)
                self._push(val)
                self._push(1)  # ok = true
            except ValueError:
                self._push(0)
                self._push(0)  # ok = false

        # -------------------------------------------------------------
        # Group 4: Control Flow & Function Calls (0x60 .. 0x6F)
        # -------------------------------------------------------------
        elif opcode == 0x60:  # JUMP
            rel = arg
            self.pc = (inst_pc + 3) + rel
        elif opcode == 0x61:  # JUMP_IF_TRUE
            cond = self._pop()
            if cond != 0:
                self.pc = (inst_pc + 3) + arg
        elif opcode == 0x62:  # JUMP_IF_FALSE
            cond = self._pop()
            if cond == 0:
                self.pc = (inst_pc + 3) + arg
        elif opcode == 0x63:  # CALL
            func_idx = arg
            if func_idx >= len(self.functions):
                raise VMError(f"Call to invalid function index: {func_idx}", inst_pc, self.current_frame.func.name)
            target_fn = self.functions[func_idx]
            self.frame_sp -= target_fn.frame_size
            self.memory[self.frame_sp : self.frame_sp + target_fn.frame_size] = b"\x00" * target_fn.frame_size
            new_frame = CallFrame(target_fn, return_pc=self.pc, return_func=self.current_frame.func, frame_addr=self.frame_sp)
            # Pop arguments into parameter slots in reverse order
            for p_idx in reversed(range(target_fn.arg_count)):
                sz = target_fn.var_sizes[p_idx]
                offset = sum(target_fn.var_sizes[:p_idx])
                addr = new_frame.frame_addr + offset
                if sz == 1:
                    val = self._pop()
                    self.memory[addr] = val & 0xFF
                    new_frame.slots[p_idx] = [val & 0xFF]
                else:
                    word_count = sz // 2
                    words = []
                    for _ in range(word_count):
                        words.insert(0, self._pop())
                    new_frame.slots[p_idx] = words
                    for i, w in enumerate(words):
                        struct.pack_into(">H", self.memory, addr + i * 2, w)

            self.call_stack.append(new_frame)
            self.current_frame = new_frame
            self.pc = target_fn.code_offset

        elif opcode == 0x64:  # RET
            self._return_from_func([])
        elif opcode == 0x65:  # RET_SLICE
            self._return_from_func([])
        elif opcode == 0x66:  # RET_VOID
            self._return_from_func([])
        elif opcode == 0x67:  # HALT
            self.running = False
            self.exit_code = 0

        # -------------------------------------------------------------
        # Group 5: Slices & Strings (0x70 .. 0x8F)
        # -------------------------------------------------------------
        elif opcode == 0x70:  # SLICE_NEW
            length = self._pop()
            cap = self._pop()
            ptr = self._pop()
            self._push_slice(ptr, cap, length)
        elif opcode == 0x71:  # SLICE_LEN
            ptr, cap, length = self._pop_slice()
            self._push(length)
        elif opcode == 0x72:  # SLICE_CAP
            ptr, cap, length = self._pop_slice()
            self._push(cap)
        elif opcode == 0x73:  # SLICE_SUB
            end = self._pop()
            start = self._pop()
            ptr, cap, length = self._pop_slice()
            start = max(0, min(start, length))
            end = max(start, min(end, length))
            new_ptr = ptr + start
            new_cap = cap - start
            new_len = end - start
            self._push_slice(new_ptr, new_cap, new_len)
        elif opcode == 0x74:  # SLICE_GET_BYTE
            idx = self._pop()
            ptr, cap, length = self._pop_slice()
            if 0 <= idx < length:
                self._push(self.memory[ptr + idx])
            else:
                self._push(0xFFFF)  # -1
        elif opcode == 0x75:  # SLICE_GET_WORD
            idx = self._pop()
            ptr, cap, length = self._pop_slice()
            if 0 <= idx < length:
                val = struct.unpack_from(">H", self.memory, ptr + idx * 2)[0]
                self._push(val)
            else:
                self._push(0x0000)
        elif opcode == 0x76:  # SLICE_SET_WORD
            val = self._pop()
            idx = self._pop()
            ptr, cap, length = self._pop_slice()
            if 0 <= idx < cap:
                struct.pack_into(">H", self.memory, ptr + idx * 2, val)
                if self.verbose:
                    print(f"       -> SLICE_SET_WORD idx {idx} at 0x{ptr:04X} <- 0x{val:04X}")
        elif opcode == 0x77:  # STR_CMP
            b_ptr, b_cap, b_len = self._pop_slice()
            a_ptr, a_cap, a_len = self._pop_slice()
            a_bytes = bytes(self.memory[a_ptr : a_ptr + a_len])
            b_bytes = bytes(self.memory[b_ptr : b_ptr + b_len])
            if self.verbose:
                print(f"       -> STR_CMP {a_bytes!r} vs {b_bytes!r}")
            if a_bytes == b_bytes:
                self._push(0)
            elif a_bytes < b_bytes:
                self._push(0xFFFF)  # -1
            else:
                self._push(1)
        elif opcode == 0x78:  # STR_STARTSWITH
            pfx_ptr, pfx_cap, pfx_len = self._pop_slice()
            str_ptr, str_cap, str_len = self._pop_slice()
            if str_len >= pfx_len:
                match = (self.memory[str_ptr : str_ptr + pfx_len] == self.memory[pfx_ptr : pfx_ptr + pfx_len])
                self._push(1 if match else 0)
            else:
                self._push(0)
        elif opcode == 0x79:  # STR_ENDSWITH
            sfx_ptr, sfx_cap, sfx_len = self._pop_slice()
            str_ptr, str_cap, str_len = self._pop_slice()
            if str_len >= sfx_len:
                start = str_ptr + str_len - sfx_len
                match = (self.memory[start : start + sfx_len] == self.memory[sfx_ptr : sfx_ptr + sfx_len])
                self._push(1 if match else 0)
            else:
                self._push(0)
        elif opcode == 0x7A:  # STR_FIND
            start = self._pop()
            sub_ptr, sub_cap, sub_len = self._pop_slice()
            str_ptr, str_cap, str_len = self._pop_slice()
            haystack = bytes(self.memory[str_ptr : str_ptr + str_len])
            needle = bytes(self.memory[sub_ptr : sub_ptr + sub_len])
            pos = haystack.find(needle, start)
            self._push(pos if pos >= 0 else 0xFFFF)
        elif opcode == 0x7B:  # STR_LSTRIP
            c_ptr, c_cap, c_len = self._pop_slice()
            s_ptr, s_cap, s_len = self._pop_slice()
            chars = bytes(self.memory[c_ptr : c_ptr + c_len]) if c_ptr != 0 else b" \t\r\n"
            i = 0
            while i < s_len and self.memory[s_ptr + i] in chars:
                i += 1
            self._push_slice(s_ptr + i, s_cap - i, s_len - i)
        elif opcode == 0x7C:  # STR_RSTRIP
            c_ptr, c_cap, c_len = self._pop_slice()
            s_ptr, s_cap, s_len = self._pop_slice()
            chars = bytes(self.memory[c_ptr : c_ptr + c_len]) if c_ptr != 0 else b" \t\r\n"
            new_len = s_len
            while new_len > 0 and self.memory[s_ptr + new_len - 1] in chars:
                new_len -= 1
            self._push_slice(s_ptr, s_cap, new_len)
        elif opcode == 0x7D:  # STR_STRIP
            c_ptr, c_cap, c_len = self._pop_slice()
            s_ptr, s_cap, s_len = self._pop_slice()
            chars = bytes(self.memory[c_ptr : c_ptr + c_len]) if c_ptr != 0 else b" \t\r\n"
            start = 0
            while start < s_len and self.memory[s_ptr + start] in chars:
                start += 1
            end = s_len
            while end > start and self.memory[s_ptr + end - 1] in chars:
                end -= 1
            self._push_slice(s_ptr + start, s_cap - start, end - start)
        elif opcode == 0x7E:  # STR_SPLITLINES
            s_ptr, s_cap, s_len = self._pop_slice()
            text = bytes(self.memory[s_ptr : s_ptr + s_len])
            # Split lines
            lines = text.splitlines(keepends=False)
            # Allocate list of string slices
            # Each entry in list is 3 words: ptr, cap, len
            # Wait, for a list of string slices, each element is 3 words?
            # Or list of string pointers?
            # Standard list elements are 16-bit words. A list of pointers to strings:
            list_buf = self.heap.alloc(len(lines) * 2)
            cur = s_ptr
            for i, line in enumerate(lines):
                # Sub-slice or string alloc
                s_alloc = self._alloc_string_slice(line.decode(errors="replace"))
                struct.pack_into(">H", self.memory, list_buf + i * 2, s_alloc[0])
            self._push_slice(list_buf, len(lines), len(lines))
        elif opcode == 0x7F:  # STR_REPLACE_IDENT
            new_ptr, new_cap, new_len = self._pop_slice()
            old_ptr, old_cap, old_len = self._pop_slice()
            src_ptr, src_cap, src_len = self._pop_slice()
            src_str = self._read_string(src_ptr, src_len)
            old_str = self._read_string(old_ptr, old_len)
            new_str = self._read_string(new_ptr, new_len)

            # Word boundary replace: (?<![A-Za-z0-9_.])OLD(?![A-Za-z0-9_.])
            import re
            pattern = re.compile(r"(?<![A-Za-z0-9_.])" + re.escape(old_str) + r"(?![A-Za-z0-9_.])")
            res_str = pattern.sub(new_str, src_str)
            res_ptr, res_cap, res_len = self._alloc_string_slice(res_str)
            self._push_slice(res_ptr, res_cap, res_len)

        # -------------------------------------------------------------
        # Group 6: Collections (Dicts as Linear Alternating Lists) (0x90 .. 0xAF)
        # -------------------------------------------------------------
        elif opcode == 0x90:  # DICT_NEW
            entry_cap = arg
            word_cap = entry_cap * 2
            buf_addr = self.heap.alloc(word_cap * 2)
            self._push_slice(buf_addr, word_cap, 0)
        elif opcode == 0x91:  # DICT_GET
            kptr, kcap, klen = self._pop_slice()
            dptr, dcap, dlen = self._pop_slice()
            key_bytes = bytes(self.memory[kptr : kptr + klen])
            found = False
            found_val = 0
            # Linear scan over alternating pairs [key_ptr, val]
            for i in range(0, dlen, 2):
                curr_kptr = struct.unpack_from(">H", self.memory, dptr + i * 2)[0]
                # Compare null-terminated string at curr_kptr with key_bytes
                if self._cmp_cstring(curr_kptr, key_bytes):
                    found_val = struct.unpack_from(">H", self.memory, dptr + (i + 1) * 2)[0]
                    found = True
                    break
            if found:
                self._push(found_val)
                self._push(1)  # ok = true
            else:
                self._push(0)
                self._push(0)  # ok = false
        elif opcode == 0x92:  # DICT_SET
            val = self._pop()
            kptr, kcap, klen = self._pop_slice()
            dptr, dcap, dlen = self._pop_slice()
            key_bytes = bytes(self.memory[kptr : kptr + klen])
            found = False
            for i in range(0, dlen, 2):
                curr_kptr = struct.unpack_from(">H", self.memory, dptr + i * 2)[0]
                if self._cmp_cstring(curr_kptr, key_bytes):
                    struct.pack_into(">H", self.memory, dptr + (i + 1) * 2, val)
                    found = True
                    if self.verbose:
                        print(f"       -> DICT_SET update key \"{key_bytes.decode(errors='replace')}\" <- 0x{val:04X}")
                    break

            if not found:
                # Append to dictionary
                if dlen + 2 > dcap:
                    # Grow buffer
                    new_cap = dcap + 16
                    new_buf = self.heap.alloc(new_cap * 2)
                    self.memory[new_buf : new_buf + dlen * 2] = self.memory[dptr : dptr + dlen * 2]
                    self.heap.free(dptr)
                    dptr = new_buf
                    dcap = new_cap

                # Allocate null-terminated string for key
                k_addr = self.heap.alloc(len(key_bytes) + 1)
                self.memory[k_addr : k_addr + len(key_bytes)] = key_bytes
                self.memory[k_addr + len(key_bytes)] = 0  # null terminator

                struct.pack_into(">H", self.memory, dptr + dlen * 2, k_addr)
                struct.pack_into(">H", self.memory, dptr + (dlen + 1) * 2, val)
                dlen += 2
                if self.verbose:
                    print(f"       -> DICT_SET insert key \"{key_bytes.decode(errors='replace')}\" <- 0x{val:04X} (dict len {dlen // 2})")

            self._push_slice(dptr, dcap, dlen)

        elif opcode == 0x93:  # DICT_HAS
            kptr, kcap, klen = self._pop_slice()
            dptr, dcap, dlen = self._pop_slice()
            key_bytes = bytes(self.memory[kptr : kptr + klen])
            found = False
            for i in range(0, dlen, 2):
                curr_kptr = struct.unpack_from(">H", self.memory, dptr + i * 2)[0]
                if self._cmp_cstring(curr_kptr, key_bytes):
                    found = True
                    break
            self._push(1 if found else 0)
        elif opcode == 0x94:  # DICT_KEYS
            dptr, dcap, dlen = self._pop_slice()
            count = dlen // 2
            list_buf = self.heap.alloc(count * 2)
            for i in range(count):
                kptr = struct.unpack_from(">H", self.memory, dptr + (i * 2) * 2)[0]
                struct.pack_into(">H", self.memory, list_buf + i * 2, kptr)
            self._push_slice(list_buf, count, count)
        elif opcode == 0x95:  # DICT_LEN
            dptr, dcap, dlen = self._pop_slice()
            self._push(dlen // 2)
        elif opcode == 0x96:  # LIST_NEW
            word_cap = arg
            buf_addr = self.heap.alloc(word_cap * 2)
            self._push_slice(buf_addr, word_cap, 0)
        elif opcode == 0x97:  # LIST_APPEND
            val = self._pop()
            lptr, lcap, llen = self._pop_slice()
            if llen >= lcap:
                new_cap = max(lcap * 2, 8)
                new_buf = self.heap.alloc(new_cap * 2)
                self.memory[new_buf : new_buf + llen * 2] = self.memory[lptr : lptr + llen * 2]
                self.heap.free(lptr)
                lptr = new_buf
                lcap = new_cap
            struct.pack_into(">H", self.memory, lptr + llen * 2, val)
            llen += 1
            self._push_slice(lptr, lcap, llen)
        elif opcode == 0x98:  # LIST_POP
            lptr, lcap, llen = self._pop_slice()
            if llen == 0:
                raise VMError("Pop from empty list", inst_pc, self.current_frame.func.name)
            llen -= 1
            val = struct.unpack_from(">H", self.memory, lptr + llen * 2)[0]
            self._push_slice(lptr, lcap, llen)
            self._push(val)
        elif opcode == 0x99:  # LIST_SORT_BY_LEN
            reverse = self._pop()
            lptr, lcap, llen = self._pop_slice()
            # Array of string pointers: sort in place
            ptrs = [struct.unpack_from(">H", self.memory, lptr + i * 2)[0] for i in range(llen)]
            ptrs.sort(key=lambda p: self._cstrlen(p), reverse=bool(reverse))
            for i, p in enumerate(ptrs):
                struct.pack_into(">H", self.memory, lptr + i * 2, p)
            self._push_slice(lptr, lcap, llen)
        elif opcode == 0x9A:  # STR_APPEND
            char_code = self._pop() & 0xFF
            ptr, cap, length = self._pop_slice()
            if length >= cap:
                new_cap = max(cap * 2, 8)
                new_buf = self.heap.alloc(new_cap)
                if ptr != 0 and length > 0:
                    self.memory[new_buf : new_buf + length] = self.memory[ptr : ptr + length]
                    self.heap.free(ptr)
                ptr = new_buf
                cap = new_cap
            self.memory[ptr + length] = char_code
            length += 1
            self._push_slice(ptr, cap, length)
        elif opcode == 0x9B:  # SLICE_APPEND_STR
            s_ptr, s_cap, s_len = self._pop_slice()
            l_ptr, l_cap, l_len = self._pop_slice()
            if l_len >= l_cap:
                new_cap = max(l_cap * 2, 8)
                new_buf = self.heap.alloc(new_cap * 6)
                if l_ptr != 0 and l_len > 0:
                    self.memory[new_buf : new_buf + l_len * 6] = self.memory[l_ptr : l_ptr + l_len * 6]
                    self.heap.free(l_ptr)
                l_ptr = new_buf
                l_cap = new_cap
            struct.pack_into(">HHH", self.memory, l_ptr + l_len * 6, s_ptr, s_cap, s_len)
            l_len += 1
            self._push_slice(l_ptr, l_cap, l_len)

        # -------------------------------------------------------------
        # Group 7: Regular Expressions (0xB0 .. 0xBF)
        # -------------------------------------------------------------
        elif opcode in (0xB0, 0xB1):  # REG_MATCH, REG_SEARCH
            s_ptr, s_cap, s_len = self._pop_slice()
            # Stub/placeholder for basic pattern support
            self._push(0x0000)  # match_ptr
            self._push(0x0000)  # ok = false
        elif opcode == 0xB2:  # REG_GROUP
            grp_idx = self._pop()
            match_ptr = self._pop()
            self._push_slice(0, 0, 0)
        elif opcode == 0xB3:  # REG_GROUP_END
            grp_idx = self._pop()
            match_ptr = self._pop()
            self._push(0)

        # -------------------------------------------------------------
        # Group 8: File System & OS System Calls (0xC0 .. 0xCF)
        # -------------------------------------------------------------
        elif opcode == 0xC0:  # FILE_OPEN_READ
            path_ptr, path_cap, path_len = self._pop_slice()
            path = self._read_string(path_ptr, path_len)
            try:
                f = open(path, "r", encoding="utf-8")
                h = self.next_file_handle
                self.next_file_handle += 1
                self.open_files[h] = f
                self._push(h)
                self._push(1)  # ok = true
            except Exception as e:
                self._push(0)
                self._push(0)
        elif opcode == 0xC1:  # FILE_OPEN_WRITE
            path_ptr, path_cap, path_len = self._pop_slice()
            path = self._read_string(path_ptr, path_len)
            try:
                f = open(path, "w", encoding="utf-8")
                h = self.next_file_handle
                self.next_file_handle += 1
                self.open_files[h] = f
                self._push(h)
                self._push(1)
            except Exception:
                self._push(0)
                self._push(0)
        elif opcode == 0xC2:  # FILE_READLINE
            handle = self._pop()
            f = self.open_files.get(handle)
            if not f:
                self._push_slice(0, 0, 0)
                self._push(1)  # eof
            else:
                line = f.readline()
                if not line:
                    self._push_slice(0, 0, 0)
                    self._push(1)  # eof
                else:
                    ptr, cap, length = self._alloc_string_slice(line)
                    self._push_slice(ptr, cap, length)
                    self._push(0)  # not eof
        elif opcode == 0xC3:  # FILE_WRITE
            s_ptr, s_cap, s_len = self._pop_slice()
            handle = self._pop()
            f = self.open_files.get(handle)
            if f:
                text = self._read_string(s_ptr, s_len)
                f.write(text)
                self._push(1)
            else:
                self._push(0)
        elif opcode == 0xC4:  # FILE_CLOSE
            handle = self._pop()
            if handle in self.open_files:
                f = self.open_files[handle]
                if handle > 2:
                    f.close()
                del self.open_files[handle]
        elif opcode == 0xC5:  # OS_ISFILE
            p_ptr, p_cap, p_len = self._pop_slice()
            path = self._read_string(p_ptr, p_len)
            self._push(1 if os.path.isfile(path) else 0)
        elif opcode == 0xC6:  # OS_MAKEDIRS
            p_ptr, p_cap, p_len = self._pop_slice()
            path = self._read_string(p_ptr, p_len)
            try:
                os.makedirs(path, exist_ok=True)
                self._push(1)
            except Exception:
                self._push(0)
        elif opcode == 0xC7:  # SYS_ARGS
            arg_ptrs = []
            for arg_text in self.cli_args:
                p, c, l = self._alloc_string_slice(arg_text)
                arg_ptrs.append(p)
            list_buf = self.heap.alloc(len(arg_ptrs) * 2)
            for i, p in enumerate(arg_ptrs):
                struct.pack_into(">H", self.memory, list_buf + i * 2, p)
            self._push_slice(list_buf, len(arg_ptrs), len(arg_ptrs))
        elif opcode == 0xC8:  # SYS_EXIT
            code = self._pop()
            self.running = False
            self.exit_code = code
        elif opcode == 0xC9:  # IO_PRINT
            s_ptr, s_cap, s_len = self._pop_slice()
            text = self._read_string(s_ptr, s_len)
            print(text)
        elif opcode in (0xCA, 0xCB):  # PRINT (0xCA), PRINTLN (0xCB)
            is_println = (opcode == 0xCB)
            s_ptr, s_cap, s_len = self._pop_slice()
            formatted_parts = []
            for i in range(s_len):
                entry_addr = s_ptr + i * 4
                val_addr = struct.unpack_from(">H", self.memory, entry_addr)[0]
                type_addr = struct.unpack_from(">H", self.memory, entry_addr + 2)[0]
                type_name = self._read_cstring(type_addr)

                if type_name in ("word", "uint", "uint16", "int", "int16"):
                    val = struct.unpack_from(">H", self.memory, val_addr)[0]
                    formatted_parts.append(str(val))
                elif type_name in ("byte", "uint8"):
                    val = self.memory[val_addr]
                    formatted_parts.append(str(val))
                elif type_name == "bool":
                    val = struct.unpack_from(">H", self.memory, val_addr)[0]
                    formatted_parts.append("true" if val != 0 else "false")
                elif type_name in ("string", "slice_byte", "slice[byte]", "prelude.slice_byte"):
                    str_base, str_cap, str_len = struct.unpack_from(">HHH", self.memory, val_addr)
                    formatted_parts.append(self._read_string(str_base, str_len))
                elif type_name in ("*byte", "cstring"):
                    cptr = struct.unpack_from(">H", self.memory, val_addr)[0]
                    formatted_parts.append(self._read_cstring(cptr))
                else:
                    if val_addr != 0:
                        val = struct.unpack_from(">H", self.memory, val_addr)[0]
                        formatted_parts.append(str(val))
                    else:
                        formatted_parts.append("<nil>")

            out_text = " ".join(formatted_parts)
            if is_println:
                print(out_text)
            else:
                sys.stdout.write(out_text)
                sys.stdout.flush()

    def _load_local(self, slot: int):
        offset = sum(self.current_frame.func.var_sizes[:slot])
        addr = self.current_frame.frame_addr + offset
        sz = self.current_frame.func.var_sizes[slot]
        if sz == 1:
            val = self.memory[addr]
            self.current_frame.slots[slot] = [val]
            self._push(val)
        else:
            word_count = sz // 2
            words = [
                struct.unpack_from(">H", self.memory, addr + i * 2)[0]
                for i in range(word_count)
            ]
            self.current_frame.slots[slot] = words
            for w in words:
                self._push(w)

    def _store_local(self, slot: int):
        sz = self.current_frame.func.var_sizes[slot]
        offset = sum(self.current_frame.func.var_sizes[:slot])
        addr = self.current_frame.frame_addr + offset
        if sz == 1:
            val = self._pop()
            self.memory[addr] = val & 0xFF
            self.current_frame.slots[slot] = [val & 0xFF]
            if self.verbose:
                print(f"       -> STORE_LOCAL slot {slot} <- 0x{val & 0xFF:02X}")
        else:
            word_count = sz // 2
            words = []
            for _ in range(word_count):
                words.insert(0, self._pop())
            self.current_frame.slots[slot] = words
            for i, w in enumerate(words):
                struct.pack_into(">H", self.memory, addr + i * 2, w)
            if self.verbose:
                val_repr = self._format_value(words)
                print(f"       -> STORE_LOCAL slot {slot} <- {val_repr}")

    def _load_global(self, slot: int):
        addr = self.global_addrs[slot]
        sz = self.global_sizes[slot]
        if sz == 1:
            self._push(self.memory[addr])
        else:
            word_count = sz // 2
            for i in range(word_count):
                w = struct.unpack_from(">H", self.memory, addr + i * 2)[0]
                self._push(w)

    def _store_global(self, slot: int):
        addr = self.global_addrs[slot]
        sz = self.global_sizes[slot]
        if sz == 1:
            val = self._pop()
            self.memory[addr] = val & 0xFF
            if self.verbose:
                print(f"       -> STORE_GLOBAL slot {slot} <- 0x{val & 0xFF:02X}")
        else:
            word_count = sz // 2
            words = []
            for _ in range(word_count):
                words.insert(0, self._pop())
            for i, w in enumerate(words):
                struct.pack_into(">H", self.memory, addr + i * 2, w)
            if self.verbose:
                val_repr = self._format_value(words)
                print(f"       -> STORE_GLOBAL slot {slot} <- {val_repr}")

    def _return_from_func(self, return_words: List[int]):
        finished_frame = self.call_stack.pop()
        self.frame_sp += finished_frame.func.frame_size
        if self.call_stack:
            self.current_frame = self.call_stack[-1]
            self.pc = finished_frame.return_pc
            for w in return_words:
                self._push(w)
        else:
            self.current_frame = None
            self.running = False

    def _read_string(self, ptr: int, length: int) -> str:
        if ptr == 0 or length == 0:
            return ""
        raw = bytes(self.memory[ptr : ptr + length])
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1")

    def _alloc_string_slice(self, s: str) -> Tuple[int, int, int]:
        raw = s.encode("utf-8")
        length = len(raw)
        buf = self.heap.alloc(length + 1)
        self.memory[buf : buf + length] = raw
        self.memory[buf + length] = 0  # null terminator
        return buf, length, length

    def _cmp_cstring(self, cptr: int, target_bytes: bytes) -> bool:
        if cptr == 0:
            return len(target_bytes) == 0
        idx = 0
        n = len(target_bytes)
        while idx < n:
            if self.memory[cptr + idx] != target_bytes[idx]:
                return False
            idx += 1
        return self.memory[cptr + idx] == 0

    def _cstrlen(self, cptr: int) -> int:
        if cptr == 0:
            return 0
        idx = 0
        while self.memory[cptr + idx] != 0:
            idx += 1
        return idx

    def _read_cstring(self, cptr: int) -> str:
        if cptr == 0:
            return ""
        length = self._cstrlen(cptr)
        return self._read_string(cptr, length)

    @staticmethod
    def _to_signed(w: int) -> int:
        return struct.unpack(">h", struct.pack(">H", w & 0xFFFF))[0]


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: npvm.py <program.npc> [-v] [--max-cycles N] [-- ARGS...]")
        sys.exit(0)

    input_file = None
    verbose = False
    max_cycles = None
    cli_args = []

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ("-v", "--verbose"):
            verbose = True
            i += 1
        elif arg == "--max-cycles" and i + 1 < len(sys.argv):
            max_cycles = int(sys.argv[i + 1])
            i += 2
        elif arg == "--":
            cli_args = sys.argv[i + 1:]
            break
        elif not input_file and not arg.startswith("-"):
            input_file = arg
            i += 1
        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)

    if not input_file:
        print("Error: No input NPC file specified")
        sys.exit(1)

    try:
        with open(input_file, "rb") as f:
            binary_data = f.read()
    except Exception as e:
        print(f"Error reading '{input_file}': {e}")
        sys.exit(1)

    vm = NPVM(binary_data, verbose=verbose, cli_args=cli_args)
    try:
        exit_code = vm.run(max_instructions=max_cycles)
        sys.exit(exit_code)
    except VMError as e:
        print(f"\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
