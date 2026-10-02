#!/usr/bin/env python3
"""
npasm.py - Assembler for the NPCode Virtual Machine.

Assembles NP assembly source (.npasm) into NPCode bytecode binaries (.npc).
Features:
  - Expressions with arithmetic, bitwise operators, and multi-radix numbers ($hex, %bin, @oct, 0x, 0b).
  - Named labels, relative branch offset calculation (JUMP, JUMP_IF_TRUE, JUMP_IF_FALSE).
  - Variable-table-driven parameters and locals (.param, .local) with auto slot lookup.
  - Automatic fast opcode optimization (LOAD_LOCAL_0..3, STORE_LOCAL_0..3).
  - Inline string literals in PUSH_STR with automatic string pool placement and deduplication.
  - Named function calls (.function, CALL <func_name>).
  - Detailed listing output and error reporting.
"""

import sys
import os
import re
import struct
from typing import List, Dict, Optional, Tuple, Any

from opcodes import (
    MAGIC, FORMAT_VER, HEADER_SIZE, FUNC_ENTRY_SIZE,
    OPCODE_TABLE, MNEMONIC_TO_OPCODE
)


class AssemblerError(Exception):
    def __init__(self, message: str, line_no: Optional[int] = None, line_text: Optional[str] = None):
        self.message = message
        self.line_no = line_no
        self.line_text = line_text
        super().__init__(self.__str__())

    def __str__(self) -> str:
        if self.line_no is not None:
            prefix = f"Line {self.line_no}: "
            if self.line_text:
                prefix += f"'{self.line_text.strip()}' -> "
            return prefix + self.message
        return self.message


class StringPool:
    """Manages the raw string pool with length-prefixed null-terminated entries."""
    def __init__(self):
        self.pool = bytearray()
        self.string_to_offset: Dict[bytes, int] = {}

    def add(self, text_bytes: bytes) -> int:
        if text_bytes in self.string_to_offset:
            return self.string_to_offset[text_bytes]
        offset = len(self.pool)
        length = len(text_bytes)
        if length > 65535:
            raise AssemblerError(f"String exceeds 65535 bytes: {length}")
        entry = struct.pack(">H", length) + text_bytes + b"\x00"
        self.pool.extend(entry)
        self.string_to_offset[text_bytes] = offset
        return offset

    def get_bytes(self) -> bytes:
        return bytes(self.pool)


class ExprParser:
    """Evaluates arithmetic expressions with symbols and multiple radixes."""

    TOKEN_SPEC = [
        ("HEX_PREFIX", r"0[xX][0-9a-fA-F]+|\$[0-9a-fA-F]+"),
        ("BIN_PREFIX", r"0[bB][01]+|%[01]+"),
        ("OCT_PREFIX", r"0[oO][0-7]+|@[0-7]+"),
        ("HEX_SUFFIX", r"[0-9][0-9a-fA-F]*[hH]"),
        ("DEC",        r"[0-9]+"),
        ("CHAR",       r"'(\\.|[^\\'])'"),
        ("IDENT",      r"[A-Za-z_][A-Za-z0-9_.]*"),
        ("OP2",        r"<<|>>|==|!=|<=|>="),
        ("OP1",        r"[+\-*/%&|^~!<>()]"),
        ("SKIP",       r"[ \t]+"),
    ]
    TOKEN_RE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC))

    def __init__(self, expr_str: str, symbols: Dict[str, int], current_pc: int = 0):
        self.expr_str = expr_str
        self.symbols = symbols
        self.current_pc = current_pc
        self.tokens: List[Tuple[str, str, Any]] = []
        self._tokenize()
        self.pos = 0

    def _tokenize(self):
        for m in self.TOKEN_RE.finditer(self.expr_str):
            kind = m.lastgroup
            val = m.group()
            if kind == "SKIP":
                continue
            if kind == "HEX_PREFIX":
                s = val[1:] if val.startswith("$") else val[2:]
                self.tokens.append(("NUM", val, int(s, 16)))
            elif kind == "HEX_SUFFIX":
                self.tokens.append(("NUM", val, int(val[:-1], 16)))
            elif kind == "BIN_PREFIX":
                s = val[1:] if val.startswith("%") else val[2:]
                self.tokens.append(("NUM", val, int(s, 2)))
            elif kind == "OCT_PREFIX":
                s = val[1:] if val.startswith("@") else val[2:]
                self.tokens.append(("NUM", val, int(s, 8)))
            elif kind == "DEC":
                self.tokens.append(("NUM", val, int(val, 10)))
            elif kind == "CHAR":
                char_body = val[1:-1]
                c = self._unescape_char(char_body)
                self.tokens.append(("NUM", val, ord(c)))
            elif kind == "IDENT":
                if val == "$" or val == ".":
                    self.tokens.append(("NUM", val, self.current_pc))
                else:
                    self.tokens.append(("IDENT", val, val))
            else:
                self.tokens.append(("OP", val, val))

    @staticmethod
    def _unescape_char(s: str) -> str:
        if len(s) == 1:
            return s
        if s.startswith("\\"):
            escape_map = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", "'": "'", '"': '"', "0": "\0"}
            esc = s[1:]
            if esc in escape_map:
                return escape_map[esc]
            if esc.startswith("x") and len(esc) == 3:
                return chr(int(esc[1:], 16))
        return s

    def parse(self) -> int:
        if not self.tokens:
            raise AssemblerError(f"Empty expression: '{self.expr_str}'")
        res = self._parse_or()
        if self.pos < len(self.tokens):
            raise AssemblerError(f"Unexpected token '{self.tokens[self.pos][1]}' in expression '{self.expr_str}'")
        return res

    def _peek(self) -> Optional[Tuple[str, str, Any]]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _match_op(self, op: str) -> bool:
        tk = self._peek()
        if tk and tk[0] == "OP" and tk[1] == op:
            self.pos += 1
            return True
        return False

    def _parse_or(self) -> int:
        v = self._parse_xor()
        while self._match_op("|"):
            v = v | self._parse_xor()
        return v

    def _parse_xor(self) -> int:
        v = self._parse_and()
        while self._match_op("^"):
            v = v ^ self._parse_and()
        return v

    def _parse_and(self) -> int:
        v = self._parse_shift()
        while self._match_op("&"):
            v = v & self._parse_shift()
        return v

    def _parse_shift(self) -> int:
        v = self._parse_add()
        while True:
            if self._match_op("<<"):
                v = v << self._parse_add()
            elif self._match_op(">>"):
                v = v >> self._parse_add()
            else:
                break
        return v

    def _parse_add(self) -> int:
        v = self._parse_mul()
        while True:
            if self._match_op("+"):
                v = v + self._parse_mul()
            elif self._match_op("-"):
                v = v - self._parse_mul()
            else:
                break
        return v

    def _parse_mul(self) -> int:
        v = self._parse_unary()
        while True:
            if self._match_op("*"):
                v = v * self._parse_unary()
            elif self._match_op("/"):
                denom = self._parse_unary()
                if denom == 0:
                    raise AssemblerError("Division by zero in expression")
                v = v // denom
            elif self._match_op("%"):
                denom = self._parse_unary()
                if denom == 0:
                    raise AssemblerError("Modulo by zero in expression")
                v = v % denom
            else:
                break
        return v

    def _parse_unary(self) -> int:
        if self._match_op("+"):
            return +self._parse_unary()
        if self._match_op("-"):
            return -self._parse_unary()
        if self._match_op("~"):
            return ~self._parse_unary()
        if self._match_op("!"):
            return 1 if self._parse_unary() == 0 else 0
        return self._parse_primary()

    def _parse_primary(self) -> int:
        tk = self._peek()
        if not tk:
            raise AssemblerError(f"Unexpected end of expression: '{self.expr_str}'")
        self.pos += 1
        kind, text, val = tk
        if kind == "NUM":
            return val
        if kind == "IDENT":
            if val in self.symbols:
                return self.symbols[val]
            raise AssemblerError(f"Undefined symbol: '{val}'")
        if kind == "OP" and text == "(":
            res = self._parse_or()
            if not self._match_op(")"):
                raise AssemblerError(f"Missing closing parenthesis in expression: '{self.expr_str}'")
            return res
        raise AssemblerError(f"Unexpected token in expression: '{text}'")


def unescape_string_literal(lit: str) -> bytes:
    """Parse a quoted string literal into bytes with escape sequence processing."""
    if not ((lit.startswith('"') and lit.endswith('"')) or (lit.startswith("'") and lit.endswith("'"))):
        raise AssemblerError(f"Invalid string literal: {lit}")
    body = lit[1:-1]
    res = bytearray()
    i = 0
    n = len(body)
    while i < n:
        c = body[i]
        if c == "\\" and i + 1 < n:
            nc = body[i + 1]
            if nc == "n":
                res.append(0x0A)
                i += 2
            elif nc == "r":
                res.append(0x0D)
                i += 2
            elif nc == "t":
                res.append(0x09)
                i += 2
            elif nc == "\\":
                res.append(0x5C)
                i += 2
            elif nc == '"':
                res.append(0x22)
                i += 2
            elif nc == "'":
                res.append(0x27)
                i += 2
            elif nc == "0":
                res.append(0x00)
                i += 2
            elif nc == "x" and i + 3 < n:
                hex_val = int(body[i + 2:i + 4], 16)
                res.append(hex_val)
                i += 4
            else:
                res.append(ord(nc))
                i += 2
        else:
            res.extend(c.encode("utf-8"))
            i += 1
    return bytes(res)


class GlobalVar:
    def __init__(self, name: str, index: int, size: int):
        self.name = name
        self.index = index
        self.size = size


class LocalVar:
    def __init__(self, name: str, slot: int, size: int, is_param: bool):
        self.name = name
        self.slot = slot
        self.size = size
        self.is_param = is_param


class ParsedInstruction:
    def __init__(self, line_no: int, line_text: str, mnemonic: str, operand_str: str,
                 offset_in_func: int):
        self.line_no = line_no
        self.line_text = line_text
        self.mnemonic = mnemonic
        self.operand_str = operand_str
        self.offset_in_func = offset_in_func
        self.length = 0
        self.opcode_byte = 0
        self.arg_bytes = 0
        self.arg_type = "none"
        self.assembled_bytes = bytearray()


class FunctionDef:
    def __init__(self, name: str, index: int, is_entry: bool = False):
        self.name = name
        self.index = index
        self.is_entry = is_entry
        self.params: List[LocalVar] = []
        self.locals: List[LocalVar] = []
        self.var_by_name: Dict[str, LocalVar] = {}
        self.labels: Dict[str, int] = {}  # label_name -> offset_in_func
        self.instructions: List[ParsedInstruction] = []
        self.code_offset = 0
        self.code_size = 0
        self.var_table_offset = 0

    @property
    def arg_count(self) -> int:
        return len(self.params)

    @property
    def local_count(self) -> int:
        return len(self.locals)

    @property
    def frame_size(self) -> int:
        return sum(v.size for v in self.params + self.locals)

    @property
    def all_vars(self) -> List[LocalVar]:
        return self.params + self.locals

    def add_var(self, name: str, size: int, is_param: bool) -> LocalVar:
        if name in self.var_by_name:
            raise AssemblerError(f"Duplicate variable name: '{name}' in function '{self.name}'")
        slot = len(self.params) + len(self.locals)
        v = LocalVar(name, slot, size, is_param)
        if is_param:
            self.params.append(v)
        else:
            self.locals.append(v)
        self.var_by_name[name] = v
        return v


def parse_size_descriptor(desc: str) -> int:
    """Parses a type or size descriptor into byte count."""
    desc = desc.strip().lower()
    if desc.startswith(":"):
        desc = desc[1:].strip()
    if desc in ("byte", "uint8", "bool"):
        return 1
    if desc in ("scalar", "word", "int", "int16", "uint", "uint16", "buf"):
        return 2
    if desc in ("slice", "str", "string", "list", "dict"):
        return 6
    try:
        val = int(desc, 0)
        if val <= 0:
            raise ValueError()
        return val
    except ValueError:
        raise AssemblerError(f"Unknown type/size descriptor: '{desc}' (expected scalar, slice, or integer bytes)")


class Assembler:
    def __init__(self):
        self.string_pool = StringPool()
        self.globals: List[GlobalVar] = []
        self.global_by_name: Dict[str, GlobalVar] = {}
        self.functions: List[FunctionDef] = []
        self.func_by_name: Dict[str, FunctionDef] = {}
        self.symbols: Dict[str, int] = {}
        self.current_func: Optional[FunctionDef] = None
        self.entry_func_index = 0

    def assemble_source(self, source_text: str) -> bytes:
        lines = source_text.splitlines()

        # PASS 1: Symbol collection, declarations, instruction sizing, label positions
        self._pass1(lines)

        # PASS 2: Instruction operand evaluation, branch offset calculation, binary generation
        bytecode = self._pass2()

        # Build NPC binary
        return self._build_binary(bytecode)

    def _pass1(self, lines: List[str]):
        line_no = 0
        for raw_line in lines:
            line_no += 1
            line = raw_line.strip()

            # Ignore empty lines and comments
            if not line or line.startswith(";") or line.startswith("#") or line.startswith("*"):
                continue

            # Strip trailing comments (preserving quoted string contents)
            clean_line = self._strip_comment(line)
            if not clean_line:
                continue

            # Handle equates: NAME = EXPR or .equ NAME, EXPR
            if self._handle_equate(clean_line, line_no, raw_line):
                continue

            # Label on its own or with instruction: label: [inst]
            label_name, rest = self._split_label(clean_line)
            if label_name:
                self._define_label(label_name, line_no, raw_line)
                if not rest:
                    continue
                clean_line = rest

            # Directives
            if clean_line.startswith("."):
                self._handle_directive(clean_line, line_no, raw_line)
                continue

            # Instruction
            self._handle_instruction_pass1(clean_line, line_no, raw_line)

        # Finalize entry function if not set
        if not any(f.is_entry for f in self.functions):
            for i, f in enumerate(self.functions):
                if f.name in ("main", "_start", "entry"):
                    f.is_entry = True
                    self.entry_func_index = i
                    break
            else:
                if self.functions:
                    self.functions[0].is_entry = True
                    self.entry_func_index = 0

    @staticmethod
    def _split_label(line: str) -> Tuple[Optional[str], str]:
        in_quote = None
        for i, c in enumerate(line):
            if c in ('"', "'"):
                if in_quote is None:
                    in_quote = c
                elif in_quote == c:
                    in_quote = None
            elif c == ":" and in_quote is None:
                label = line[:i].strip()
                rest = line[i + 1:].strip()
                if label and " " not in label and "\t" not in label:
                    return label, rest
                break
        return None, line

    @staticmethod
    def _strip_comment(line: str) -> str:
        in_quote = None
        for i, c in enumerate(line):
            if c in ('"', "'"):
                if in_quote is None:
                    in_quote = c
                elif in_quote == c:
                    in_quote = None
            elif c in (";", "#") and in_quote is None:
                return line[:i].strip()
        return line.strip()

    def _handle_equate(self, line: str, line_no: int, raw_line: str) -> bool:
        # Check for NAME = EXPR or NAME equ EXPR
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*(?:=|\bEQU\b|\bequ\b)\s*(.+)$", line)
        if m:
            name = m.group(1)
            expr = m.group(2)
            val = ExprParser(expr, self.symbols).parse()
            self.symbols[name] = val
            return True
        return False

    def _define_label(self, name: str, line_no: int, raw_line: str):
        if not self.current_func:
            raise AssemblerError(f"Label '{name}' defined outside of function", line_no, raw_line)
        offset = len(self.current_func.instructions)
        # Compute byte offset in function
        byte_offset = sum(inst.length for inst in self.current_func.instructions)
        if name in self.current_func.labels:
            raise AssemblerError(f"Duplicate label: '{name}' in function '{self.current_func.name}'", line_no, raw_line)
        self.current_func.labels[name] = byte_offset
        self.symbols[f"{self.current_func.name}.{name}"] = byte_offset
        self.symbols[name] = byte_offset

    def _handle_directive(self, line: str, line_no: int, raw_line: str):
        parts = line.split(None, 1)
        directive = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""

        if directive in (".function", ".func"):
            if self.current_func is not None:
                raise AssemblerError(f"Nested function definition in '{self.current_func.name}'", line_no, raw_line)
            tokens = args.split()
            if not tokens:
                raise AssemblerError("Missing function name in .function", line_no, raw_line)
            fn_name = tokens[0]
            is_entry = ("entry" in tokens[1:]) or (fn_name == "main")
            fn_idx = len(self.functions)
            f = FunctionDef(fn_name, fn_idx, is_entry)
            self.functions.append(f)
            self.func_by_name[fn_name] = f
            self.symbols[fn_name] = fn_idx
            self.current_func = f
            if is_entry:
                self.entry_func_index = fn_idx

        elif directive in (".endfunction", ".endfunc", ".end"):
            if self.current_func is None:
                raise AssemblerError(".endfunction without active function", line_no, raw_line)
            self.current_func = None

        elif directive == ".param":
            if self.current_func is None:
                raise AssemblerError(".param directive outside function", line_no, raw_line)
            p_parts = [t for t in re.split(r'[\s,:]+', args) if t]
            if not p_parts:
                raise AssemblerError("Missing parameter name in .param", line_no, raw_line)
            p_name = p_parts[0]
            size = parse_size_descriptor(p_parts[1]) if len(p_parts) > 1 else 2
            self.current_func.add_var(p_name, size, is_param=True)

        elif directive == ".local":
            if self.current_func is None:
                raise AssemblerError(".local directive outside function", line_no, raw_line)
            l_parts = [t for t in re.split(r'[\s,:]+', args) if t]
            if not l_parts:
                raise AssemblerError("Missing local variable name in .local", line_no, raw_line)
            l_name = l_parts[0]
            size = parse_size_descriptor(l_parts[1]) if len(l_parts) > 1 else 2
            self.current_func.add_var(l_name, size, is_param=False)

        elif directive == ".global":
            g_parts = [t for t in re.split(r'[\s,:]+', args) if t]
            if not g_parts:
                raise AssemblerError("Missing global variable name in .global", line_no, raw_line)
            g_name = g_parts[0]
            size = parse_size_descriptor(g_parts[1]) if len(g_parts) > 1 else 2
            g_idx = len(self.globals)
            g = GlobalVar(g_name, g_idx, size)
            self.globals.append(g)
            self.global_by_name[g_name] = g
            self.symbols[g_name] = g_idx

        elif directive == ".string":
            # .string [label] "content"
            s_match = re.match(r'^(?:([A-Za-z_][A-Za-z0-9_.]*)\s+)?(".*"|\'.*\')$', args)
            if not s_match:
                raise AssemblerError(f"Invalid .string directive: {args}", line_no, raw_line)
            label = s_match.group(1)
            lit = s_match.group(2)
            text_bytes = unescape_string_literal(lit)
            offset = self.string_pool.add(text_bytes)
            if label:
                self.symbols[label] = offset

        elif directive == ".equ":
            # .equ NAME, EXPR
            equ_parts = [p.strip() for p in args.split(",", 1)]
            if len(equ_parts) != 2:
                raise AssemblerError(f"Invalid .equ directive: '{args}' (expected .equ NAME, EXPR)", line_no, raw_line)
            val = ExprParser(equ_parts[1], self.symbols).parse()
            self.symbols[equ_parts[0]] = val

        elif directive == ".entry":
            target = args.strip()
            if target in self.func_by_name:
                self.entry_func_index = self.func_by_name[target].index
            else:
                self.symbols["__pending_entry__"] = target

        else:
            raise AssemblerError(f"Unknown directive: '{directive}'", line_no, raw_line)

    def _handle_instruction_pass1(self, line: str, line_no: int, raw_line: str):
        if self.current_func is None:
            raise AssemblerError("Instruction outside function definition", line_no, raw_line)

        parts = line.split(None, 1)
        mnemonic = parts[0].upper()
        operand_str = parts[1].strip() if len(parts) > 1 else ""

        # Determine opcode and length
        # Optimization: convert LOAD_LOCAL <slot 0..3> to LOAD_LOCAL_0..3
        opt_mnemonic = self._try_optimize_mnemonic(mnemonic, operand_str)
        if opt_mnemonic in MNEMONIC_TO_OPCODE:
            target_mnemonic = opt_mnemonic
            if opt_mnemonic != mnemonic:
                operand_str = ""  # argument absorbed into opcode
        elif mnemonic in MNEMONIC_TO_OPCODE:
            target_mnemonic = mnemonic
        else:
            raise AssemblerError(f"Unknown instruction mnemonic: '{mnemonic}'", line_no, raw_line)

        opcode_byte, arg_bytes, arg_type = MNEMONIC_TO_OPCODE[target_mnemonic]

        # Calculate current byte offset in function
        offset_in_func = sum(inst.length for inst in self.current_func.instructions)
        inst = ParsedInstruction(line_no, raw_line, target_mnemonic, operand_str, offset_in_func)
        inst.length = 1 + arg_bytes
        inst.opcode_byte = opcode_byte
        inst.arg_bytes = arg_bytes
        inst.arg_type = arg_type
        self.current_func.instructions.append(inst)

    def _try_optimize_mnemonic(self, mnemonic: str, operand_str: str) -> str:
        """Peephole optimization: LOAD_LOCAL 0 -> LOAD_LOCAL_0, etc."""
        if not operand_str or not self.current_func:
            return mnemonic

        # Check if operand matches a local/param slot 0..3
        slot = None
        if operand_str in self.current_func.var_by_name:
            slot = self.current_func.var_by_name[operand_str].slot
        else:
            try:
                val = int(operand_str, 0)
                slot = val
            except ValueError:
                pass

        if slot is not None and 0 <= slot <= 3:
            if mnemonic == "LOAD_LOCAL":
                return f"LOAD_LOCAL_{slot}"
            if mnemonic == "STORE_LOCAL":
                return f"STORE_LOCAL_{slot}"

        return mnemonic

    def _pass2(self) -> bytearray:
        bytecode = bytearray()

        # Check pending entry
        if "__pending_entry__" in self.symbols:
            target_name = self.symbols["__pending_entry__"]
            if target_name in self.func_by_name:
                self.entry_func_index = self.func_by_name[target_name].index

        # Assemble functions
        for func in self.functions:
            func.code_offset = len(bytecode)
            func_bytes = bytearray()

            for inst in func.instructions:
                inst_start = len(func_bytes)
                func_bytes.append(inst.opcode_byte)

                if inst.arg_bytes > 0:
                    arg_data = self._assemble_operands(func, inst)
                    if len(arg_data) != inst.arg_bytes:
                        raise AssemblerError(
                            f"Internal error: expected {inst.arg_bytes} arg bytes, got {len(arg_data)}",
                            inst.line_no, inst.line_text
                        )
                    func_bytes.extend(arg_data)

            func.code_size = len(func_bytes)
            bytecode.extend(func_bytes)

        return bytecode

    def _assemble_operands(self, func: FunctionDef, inst: ParsedInstruction) -> bytes:
        arg_type = inst.arg_type
        operand_str = inst.operand_str

        if not operand_str:
            raise AssemblerError(f"Instruction '{inst.mnemonic}' requires an operand", inst.line_no, inst.line_text)

        # 1. String literal in PUSH_STR
        if arg_type == "str16":
            if (operand_str.startswith('"') and operand_str.endswith('"')) or \
               (operand_str.startswith("'") and operand_str.endswith("'")):
                text_bytes = unescape_string_literal(operand_str)
                pool_offset = self.string_pool.add(text_bytes)
                return struct.pack(">H", pool_offset)
            # Otherwise, evaluate as integer expression/offset
            val = ExprParser(operand_str, self.symbols, inst.offset_in_func).parse()
            if not (0 <= val <= 65535):
                raise AssemblerError(f"String pool offset out of range (0..65535): {val}", inst.line_no, inst.line_text)
            return struct.pack(">H", val)

        # 2. Relative branch: rel16
        if arg_type == "rel16":
            target_offset = self._resolve_branch_target(func, operand_str, inst)
            # Offset is relative to the address following the 3-byte branch instruction
            current_next_pc = inst.offset_in_func + 3
            rel = target_offset - current_next_pc
            if not (-32768 <= rel <= 32767):
                raise AssemblerError(f"Branch offset out of 16-bit range (-32768..32767): {rel}", inst.line_no, inst.line_text)
            return struct.pack(">h", rel)

        # 3. Function call: func16
        if arg_type == "func16":
            if operand_str in self.func_by_name:
                idx = self.func_by_name[operand_str].index
                return struct.pack(">H", idx)
            val = ExprParser(operand_str, self.symbols, inst.offset_in_func).parse()
            if not (0 <= val <= 65535):
                raise AssemblerError(f"Function index out of range: {val}", inst.line_no, inst.line_text)
            return struct.pack(">H", val)

        # 4. Local slot: local8
        if arg_type == "local8":
            if operand_str in func.var_by_name:
                slot = func.var_by_name[operand_str].slot
                return struct.pack(">B", slot)
            val = ExprParser(operand_str, self.symbols, inst.offset_in_func).parse()
            if not (0 <= val <= 255):
                raise AssemblerError(f"Local slot out of range (0..255): {val}", inst.line_no, inst.line_text)
            return struct.pack(">B", val)

        # 5. Global slot: global16
        if arg_type == "global16":
            if operand_str in self.global_by_name:
                idx = self.global_by_name[operand_str].index
                return struct.pack(">H", idx)
            val = ExprParser(operand_str, self.symbols, inst.offset_in_func).parse()
            if not (0 <= val <= 65535):
                raise AssemblerError(f"Global slot out of range (0..65535): {val}", inst.line_no, inst.line_text)
            return struct.pack(">H", val)

        # 6. Standard immediate numbers
        val = ExprParser(operand_str, self.symbols, inst.offset_in_func).parse()

        if arg_type == "imm8_s":
            if not (-128 <= val <= 127):
                raise AssemblerError(f"Signed 8-bit immediate out of range (-128..127): {val}", inst.line_no, inst.line_text)
            return struct.pack(">b", val)

        if arg_type in ("imm8_u", "field8"):
            if not (0 <= val <= 255):
                raise AssemblerError(f"Unsigned 8-bit immediate out of range (0..255): {val}", inst.line_no, inst.line_text)
            return struct.pack(">B", val)

        if arg_type == "imm16":
            if not (-32768 <= val <= 65535):
                raise AssemblerError(f"16-bit immediate out of range (-32768..65535): {val}", inst.line_no, inst.line_text)
            return struct.pack(">H" if val >= 0 else ">h", val)

        raise AssemblerError(f"Unhandled argument type: {arg_type}", inst.line_no, inst.line_text)

    def _resolve_branch_target(self, func: FunctionDef, operand_str: str, inst: ParsedInstruction) -> int:
        # Check label in current function
        if operand_str in func.labels:
            return func.labels[operand_str]

        # Check scoped label: func.label
        scoped_name = f"{func.name}.{operand_str}"
        if scoped_name in self.symbols:
            return self.symbols[scoped_name]

        # Check global symbol
        if operand_str in self.symbols:
            return self.symbols[operand_str]

        # Check explicit relative offset: +14, -6
        if operand_str.startswith("+") or operand_str.startswith("-"):
            try:
                rel = int(operand_str, 0)
                return (inst.offset_in_func + 3) + rel
            except ValueError:
                pass

        raise AssemblerError(f"Unknown branch label or target: '{operand_str}' in function '{func.name}'", inst.line_no, inst.line_text)

    def _build_binary(self, bytecode: bytearray) -> bytes:
        """Constructs the final .npc binary executable."""
        string_pool_bytes = self.string_pool.get_bytes()

        # Build Global Variable Table (2 bytes per global)
        gvar_table = bytearray()
        for g in self.globals:
            gvar_table.extend(struct.pack(">H", g.size))

        # Build Function Table & Local Variable Tables
        func_table = bytearray()
        local_var_tables = bytearray()

        current_var_offset = 0
        for f in self.functions:
            f.var_table_offset = current_var_offset
            # Function entry (10 bytes):
            # ArgCount (1B), LocalCount (1B), FrameSize (2B), CodeOffset (2B), CodeSize (2B), VarTableOffset (2B)
            entry = struct.pack(
                ">BBHHHH",
                f.arg_count,
                f.local_count,
                f.frame_size,
                f.code_offset,
                f.code_size,
                f.var_table_offset
            )
            func_table.extend(entry)

            # Local Variable Table for this function: 1 byte per variable
            f_var_bytes = bytes(v.size for v in f.all_vars)
            local_var_tables.extend(f_var_bytes)
            current_var_offset += len(f_var_bytes)

        # Build Header (16 bytes):
        # Magic (4B), FormatVer (1B), Flags (1B), StringPoolSize (2B), GlobalsCount (2B), FuncCount (2B), EntryFunc (2B), CodeSize (2B)
        flags = 0
        header = struct.pack(
            ">4sBBHHHHH",
            MAGIC,
            FORMAT_VER,
            flags,
            len(string_pool_bytes),
            len(self.globals),
            len(self.functions),
            self.entry_func_index,
            len(bytecode)
        )

        # Concatenate sections
        binary = bytearray()
        binary.extend(header)
        binary.extend(gvar_table)
        binary.extend(string_pool_bytes)
        binary.extend(func_table)
        binary.extend(local_var_tables)
        binary.extend(bytecode)

        return bytes(binary)

    def print_listing(self):
        """Prints a human-readable assembly listing."""
        print("=" * 80)
        print("NPCode Assembly Listing")
        print("=" * 80)
        print(f"Globals: {len(self.globals)} | Functions: {len(self.functions)} | Entry: {self.entry_func_index}")
        print("-" * 80)
        for g in self.globals:
            type_str = "scalar" if g.size == 2 else ("slice" if g.size == 6 else f"{g.size}B")
            print(f"  .global {g.name:<20} slot={g.index:<3} size={g.size} ({type_str})")
        print("-" * 80)
        for f in self.functions:
            entry_tag = " [ENTRY]" if f.is_entry else ""
            print(f"Function {f.name}{entry_tag}: args={f.arg_count} locals={f.local_count} frame={f.frame_size}B code_size={f.code_size}B")
            for v in f.all_vars:
                role = "param" if v.is_param else "local"
                type_str = "scalar" if v.size == 2 else ("slice" if v.size == 6 else f"{v.size}B")
                print(f"    .{role:<5} {v.name:<18} slot={v.slot:<2} size={v.size} ({type_str})")
            for inst in f.instructions:
                print(f"    {inst.offset_in_func:04X}  {inst.mnemonic:<16} {inst.operand_str}")
        print("=" * 80)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: npasm.py <input.npasm> [-o <output.npc>] [--listing] [-v]")
        sys.exit(0)

    input_file = sys.argv[1]
    output_file = None
    show_listing = False
    verbose = False

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "-o" and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
            i += 2
        elif arg == "--listing":
            show_listing = True
            i += 1
        elif arg in ("-v", "--verbose"):
            verbose = True
            i += 1
        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)

    if output_file is None:
        base, _ = os.path.splitext(input_file)
        output_file = base + ".npc"

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        print(f"Error reading '{input_file}': {e}")
        sys.exit(1)

    asm = Assembler()
    try:
        binary_data = asm.assemble_source(source)
    except AssemblerError as e:
        print(f"Assembly Error: {e}")
        sys.exit(1)

    try:
        with open(output_file, "wb") as f:
            f.write(binary_data)
    except Exception as e:
        print(f"Error writing output to '{output_file}': {e}")
        sys.exit(1)

    if show_listing or verbose:
        asm.print_listing()

    print(f"Assembled '{input_file}' -> '{output_file}' ({len(binary_data)} bytes).")


if __name__ == "__main__":
    main()
