"""
NPCode Opcode and Binary Format Definitions
Shared between npasm.py, npdis.py, and VM runtimes.
"""

# Binary Format Constants
MAGIC = b"NPC\x01"
FORMAT_VER = 1
HEADER_SIZE = 16
FUNC_ENTRY_SIZE = 10

# Flag Bits
FLAG_6309_NATIVE = 0x01
FLAG_MMU_BANKED  = 0x02

# Operand Types:
#   "none": 0 argument bytes
#   "imm8_s": 1 byte signed immediate (-128..127)
#   "imm8_u": 1 byte unsigned immediate (0..255)
#   "imm16": 2 bytes signed or unsigned 16-bit integer
#   "rel16": 2 bytes signed relative branch offset (-32768..32767)
#   "str16": 2 bytes string pool offset (uint16)
#   "func16": 2 bytes function index (uint16)
#   "local8": 1 byte local variable slot index (uint8)
#   "global16": 2 bytes global variable slot index (uint16)
#   "field8": 1 byte struct field offset (uint8)

OPCODE_TABLE = {
    # Group 1: Stack & Literals (0x00 .. 0x1F)
    0x00: ("NOP", 0, "none", "No operation"),
    0x01: ("PUSH_NIL", 0, "none", "Push scalar nil ($0000)"),
    0x02: ("PUSH_NIL_SLICE", 0, "none", "Push nil slice ($0000, $0000, $0000)"),
    0x03: ("PUSH_TRUE", 0, "none", "Push canonical Boolean true ($0001)"),
    0x04: ("PUSH_FALSE", 0, "none", "Push Boolean false ($0000)"),
    0x05: ("PUSH_0", 0, "none", "Fast push integer 0 ($0000)"),
    0x06: ("PUSH_1", 0, "none", "Fast push integer 1 ($0001)"),
    0x07: ("PUSH_NEG1", 0, "none", "Fast push integer -1 ($FFFF)"),
    0x08: ("PUSH_I8", 1, "imm8_s", "Push sign-extended 8-bit integer"),
    0x09: ("PUSH_U8", 1, "imm8_u", "Push zero-extended 8-bit unsigned integer"),
    0x0A: ("PUSH_I16", 2, "imm16", "Push 16-bit big-endian integer"),
    0x0B: ("PUSH_STR", 2, "str16", "Push 3-word string slice referencing String Pool"),
    0x0C: ("POP", 0, "none", "Discard top 16-bit word from stack"),
    0x0D: ("POP_SLICE", 0, "none", "Discard top 3-word slice from stack"),
    0x0E: ("DUP", 0, "none", "Duplicate top 16-bit word"),
    0x0F: ("SWAP", 0, "none", "Swap top two 16-bit words"),

    # Group 2: Variables & Buffers (0x20 .. 0x3F)
    0x20: ("LOAD_LOCAL_0", 0, "none", "Load variable from local slot 0"),
    0x21: ("LOAD_LOCAL_1", 0, "none", "Load variable from local slot 1"),
    0x22: ("LOAD_LOCAL_2", 0, "none", "Load variable from local slot 2"),
    0x23: ("LOAD_LOCAL_3", 0, "none", "Load variable from local slot 3"),
    0x24: ("STORE_LOCAL_0", 0, "none", "Store variable into local slot 0"),
    0x25: ("STORE_LOCAL_1", 0, "none", "Store variable into local slot 1"),
    0x26: ("STORE_LOCAL_2", 0, "none", "Store variable into local slot 2"),
    0x27: ("STORE_LOCAL_3", 0, "none", "Store variable into local slot 3"),
    0x28: ("LOAD_LOCAL", 1, "local8", "Load variable from local slot imm8"),
    0x29: ("STORE_LOCAL", 1, "local8", "Store variable into local slot imm8"),
    0x2A: ("LOAD_GLOBAL", 2, "global16", "Load variable from global slot imm16"),
    0x2B: ("STORE_GLOBAL", 2, "global16", "Store variable into global slot imm16"),
    0x2C: ("BUF_ALLOC", 0, "none", "Allocate fixed-size buffer from heap"),
    0x2D: ("BUF_FREE", 0, "none", "Free fixed-size buffer to heap"),
    0x2E: ("LOAD_FIELD", 1, "field8", "Load word from struct field at offset imm8"),
    0x2F: ("STORE_FIELD", 1, "field8", "Store word into struct field at offset imm8"),
    0x30: ("ADDR_OF_GLOBAL", 2, "global16", "Push 16-bit memory address of global variable slot imm16"),
    0x31: ("PEEK2", 0, "none", "Load 16-bit word from memory at addr"),
    0x32: ("POKE2", 0, "none", "Store 16-bit word to memory at addr"),
    0x33: ("PEEK1", 0, "none", "Load 8-bit unsigned byte from memory at addr"),
    0x34: ("POKE1", 0, "none", "Store 8-bit byte to memory at addr"),
    0x35: ("ADDR_OF_LOCAL", 1, "local8", "Push 16-bit memory address of local variable slot imm8"),
    0x36: ("SHL1_ADD", 0, "none", "Shift index left 1 bit and add to base address: base + (index << 1)"),
    0x37: ("ZALLOC", 0, "none", "Allocate zeroed buffer from heap"),

    # Group 3: Arithmetic, Logic & Comparisons (0x40 .. 0x5F)
    0x40: ("ADD", 0, "none", "16-bit integer addition"),
    0x41: ("SUB", 0, "none", "16-bit integer subtraction"),
    0x42: ("MUL", 0, "none", "16-bit unsigned integer multiplication"),
    0x43: ("DIV", 0, "none", "16-bit unsigned integer division"),
    0x44: ("MOD", 0, "none", "16-bit unsigned integer modulo"),
    0x45: ("NEG", 0, "none", "16-bit integer negation"),
    0x46: ("BIT_AND", 0, "none", "16-bit bitwise AND"),
    0x47: ("BIT_OR", 0, "none", "16-bit bitwise OR"),
    0x48: ("BIT_XOR", 0, "none", "16-bit bitwise XOR"),
    0x49: ("BIT_NOT", 0, "none", "16-bit bitwise NOT"),
    0x4A: ("SHL", 0, "none", "16-bit logical shift left"),
    0x4B: ("SHR", 0, "none", "16-bit logical shift right"),
    0x4C: ("CMP_EQ", 0, "none", "Equal (==)"),
    0x4D: ("CMP_NE", 0, "none", "Not equal (!=)"),
    0x4E: ("CMP_LT", 0, "none", "Unsigned less than (<)"),
    0x4F: ("CMP_LE", 0, "none", "Unsigned less than or equal (<=)"),
    0x50: ("CMP_GT", 0, "none", "Unsigned greater than (>)"),
    0x51: ("CMP_GE", 0, "none", "Unsigned greater than or equal (>=)"),
    0x52: ("NOT", 0, "none", "Logical NOT (pushes $0001 if zero, else $0000)"),
    0x53: ("MIN", 0, "none", "Signed integer minimum"),
    0x54: ("MAX", 0, "none", "Signed integer maximum"),
    0x55: ("PARSE_INT", 0, "none", "Parse integer from string slice"),

    # Group 4: Control Flow & Function Calls (0x60 .. 0x6F)
    0x60: ("JUMP", 2, "rel16", "Unconditional relative branch"),
    0x61: ("JUMP_IF_TRUE", 2, "rel16", "Relative branch if cond != $0000"),
    0x62: ("JUMP_IF_FALSE", 2, "rel16", "Relative branch if cond == $0000"),
    0x63: ("CALL", 2, "func16", "Call function index imm16"),
    0x64: ("RET", 0, "none", "Return 16-bit scalar word to caller"),
    0x65: ("RET_SLICE", 0, "none", "Return 3-word slice to caller"),
    0x66: ("RET_VOID", 0, "none", "Return nil ($0000) to caller"),
    0x67: ("HALT", 0, "none", "Terminate VM execution cleanly"),

    # Group 5: Slices & Strings (0x70 .. 0x8F)
    0x70: ("SLICE_NEW", 0, "none", "Construct 3-word slice from raw components"),
    0x71: ("SLICE_LEN", 0, "none", "Extract 16-bit length from slice"),
    0x72: ("SLICE_CAP", 0, "none", "Extract 16-bit capacity from slice"),
    0x73: ("SLICE_SUB", 0, "none", "Return sub-slice view (ptr+start, cap-start, end-start)"),
    0x74: ("SLICE_GET_BYTE", 0, "none", "Fetch byte at idx in string slice"),
    0x75: ("SLICE_GET_WORD", 0, "none", "Fetch 16-bit word at idx in word slice"),
    0x76: ("SLICE_SET_WORD", 0, "none", "Store 16-bit word at idx in word slice"),
    0x77: ("STR_CMP", 0, "none", "Lexicographical string slice comparison"),
    0x78: ("STR_STARTSWITH", 0, "none", "String prefix check"),
    0x79: ("STR_ENDSWITH", 0, "none", "String suffix check"),
    0x7A: ("STR_FIND", 0, "none", "Linear substring search"),
    0x7B: ("STR_LSTRIP", 0, "none", "Strip leading characters (returns view)"),
    0x7C: ("STR_RSTRIP", 0, "none", "Strip trailing characters (returns view)"),
    0x7D: ("STR_STRIP", 0, "none", "Strip leading and trailing characters (returns view)"),
    0x7E: ("STR_SPLITLINES", 0, "none", "Split text into list of string slice views"),
    0x7F: ("STR_REPLACE_IDENT", 0, "none", "Word-boundary identifier replacement"),

    # Group 6: Collections (Dicts as Linear Alternating Lists) (0x90 .. 0xAF)
    0x90: ("DICT_NEW", 2, "imm16", "Allocate dict buffer for imm16 entries"),
    0x91: ("DICT_GET", 0, "none", "Linear scan dict lookup"),
    0x92: ("DICT_SET", 0, "none", "Linear scan dict insertion/update"),
    0x93: ("DICT_HAS", 0, "none", "Linear scan key membership test"),
    0x94: ("DICT_KEYS", 0, "none", "Return list slice of dict key pointers"),
    0x95: ("DICT_LEN", 0, "none", "Return dict entry count (length / 2)"),
    0x96: ("LIST_NEW", 2, "imm16", "Allocate list buffer for imm16 words"),
    0x97: ("LIST_APPEND", 0, "none", "Append 16-bit word to list slice"),
    0x98: ("LIST_POP", 0, "none", "Pop and return last 16-bit word"),
    0x99: ("LIST_SORT_BY_LEN", 0, "none", "Sort list of string slices by length"),
    0x9A: ("STR_APPEND", 0, "none", "Append 1-byte char to string slice"),
    0x9B: ("SLICE_APPEND_STR", 0, "none", "Append 6-byte string slice to slice[string]"),

    # Group 7: Regular Expressions (0xB0 .. 0xBF)
    0xB0: ("REG_MATCH", 2, "imm16", "Anchored regex match"),
    0xB1: ("REG_SEARCH", 2, "imm16", "Unanchored regex search"),
    0xB2: ("REG_GROUP", 0, "none", "Extract captured group string slice view"),
    0xB3: ("REG_GROUP_END", 0, "none", "Return ending character index of capture"),

    # Group 8: File System & OS System Calls (0xC0 .. 0xCF)
    0xC0: ("FILE_OPEN_READ", 0, "none", "Open file for reading"),
    0xC1: ("FILE_OPEN_WRITE", 0, "none", "Create/truncate file for writing"),
    0xC2: ("FILE_READLINE", 0, "none", "Read line into string slice"),
    0xC3: ("FILE_WRITE", 0, "none", "Write string slice to file"),
    0xC4: ("FILE_CLOSE", 0, "none", "Close file handle"),
    0xC5: ("OS_ISFILE", 0, "none", "Test file existence"),
    0xC6: ("OS_MAKEDIRS", 0, "none", "Recursively create directories"),
    0xC7: ("SYS_ARGS", 0, "none", "Push CLI argument string slice list"),
    0xC8: ("SYS_EXIT", 0, "none", "Exit process with status code"),
    0xC9: ("IO_PRINT", 0, "none", "Print string slice followed by newline"),
    0xCA: ("PRINT", 0, "none", "Print Slice[any] arguments without newline"),
    0xCB: ("PRINTLN", 0, "none", "Print Slice[any] arguments with newline"),
}

# Inverse mapping: Mnemonic -> (opcode_byte, arg_bytes, arg_type)
MNEMONIC_TO_OPCODE = {
    info[0]: (op, info[1], info[2])
    for op, info in OPCODE_TABLE.items()
}

# Aliases
MNEMONIC_TO_OPCODE["PEEK"] = MNEMONIC_TO_OPCODE["PEEK2"]
MNEMONIC_TO_OPCODE["PEEK_WORD"] = MNEMONIC_TO_OPCODE["PEEK2"]
MNEMONIC_TO_OPCODE["PEEKW"] = MNEMONIC_TO_OPCODE["PEEK2"]
MNEMONIC_TO_OPCODE["GET_WORD_FIELD"] = MNEMONIC_TO_OPCODE["PEEK2"]
MNEMONIC_TO_OPCODE["GETWORDFIELD"] = MNEMONIC_TO_OPCODE["PEEK2"]

MNEMONIC_TO_OPCODE["POKE"] = MNEMONIC_TO_OPCODE["POKE2"]
MNEMONIC_TO_OPCODE["POKE_WORD"] = MNEMONIC_TO_OPCODE["POKE2"]
MNEMONIC_TO_OPCODE["POKEW"] = MNEMONIC_TO_OPCODE["POKE2"]
MNEMONIC_TO_OPCODE["SET_WORD_FIELD"] = MNEMONIC_TO_OPCODE["POKE2"]
MNEMONIC_TO_OPCODE["SETWORDFIELD"] = MNEMONIC_TO_OPCODE["POKE2"]

MNEMONIC_TO_OPCODE["PEEKB"] = MNEMONIC_TO_OPCODE["PEEK1"]
MNEMONIC_TO_OPCODE["PEEK_BYTE"] = MNEMONIC_TO_OPCODE["PEEK1"]
MNEMONIC_TO_OPCODE["GET_CHAR_FIELD"] = MNEMONIC_TO_OPCODE["PEEK1"]
MNEMONIC_TO_OPCODE["GETCHARFIELD"] = MNEMONIC_TO_OPCODE["PEEK1"]

MNEMONIC_TO_OPCODE["POKEB"] = MNEMONIC_TO_OPCODE["POKE1"]
MNEMONIC_TO_OPCODE["POKE_BYTE"] = MNEMONIC_TO_OPCODE["POKE1"]
MNEMONIC_TO_OPCODE["SET_CHAR_FIELD"] = MNEMONIC_TO_OPCODE["POKE1"]
MNEMONIC_TO_OPCODE["SETCHARFIELD"] = MNEMONIC_TO_OPCODE["POKE1"]

MNEMONIC_TO_OPCODE["ADDROFLOCAL"] = MNEMONIC_TO_OPCODE["ADDR_OF_LOCAL"]
MNEMONIC_TO_OPCODE["SHL1ADD"] = MNEMONIC_TO_OPCODE["SHL1_ADD"]
MNEMONIC_TO_OPCODE["INDEX2"] = MNEMONIC_TO_OPCODE["SHL1_ADD"]

