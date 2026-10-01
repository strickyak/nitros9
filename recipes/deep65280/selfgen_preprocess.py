#!/usr/bin/env python3
"""
selfgen_preprocess.py - Preprocess NitrOS-9 assembly sources for native 'asm'

Transforms LWASM-specific syntax into forms compatible with the native
Microware / Curtis Boyle OS-9 assembler ('asm'):
  1. Replaces '@'-local labels with scope-unique labels (e.g. L<id><name>).
     Guarantees the first 8 characters are globally unique to fit asm's 8-char symbol table.
  2. Expands 'fill <val>,<count>' into 'fcb' sequences. Handles symbolic fills with 'equ *'.
  3. Replaces 'IFNDEF' with 'IFNDF'.
  4. Replaces 'ENDIF' with 'ENDC'.
  5. Simplifies 'CLOCK_AND_STOP.' into 'CAS.' to prevent 8-char prefix collisions.
  6. Simplifies bitwise OR expressions like (CAS.R6Hz|CAS.IRQEn|CAS.Tick) into $23.
  7. Converts column-0 comment lines starting with ';' into '*'.
  8. Removes IFP1 wrappers around 'use defsfile' so defs are available on pass 2.
  9. Truncates comment fields so lines never exceed 78 chars (prevents 80-char asm line-wrap).
 10. Automatically detects and resolves 8-character prefix collisions across symbols
     within a file or compilation group, replacing collisions with unique 6-character IDs.
"""

import sys
import os
import re

# Standard 6809/6309 registers and assembler pseudo-ops/keywords
DEFAULT_PROTECTED = {
    "A", "B", "CC", "D", "DP", "E", "F", "W", "X", "Y", "U", "S", "PC", "PCR",
    "EQU", "SET", "RMB", "FCB", "FDB", "FQB", "FCC", "FCS", "USE", "NAM", "TTL",
    "MOD", "EMOD", "END", "ORG", "IFEQ", "IFNE", "IFGT", "IFGE", "IFLT", "IFLE",
    "IFP1", "IFDEF", "IFNDF", "IFNDEF", "ELSE", "ENDC", "ENDIF"
}

def load_protected_from_defs(defs_path):
    protected = set(DEFAULT_PROTECTED)
    if os.path.isfile(defs_path):
        with open(defs_path, "r", errors="ignore") as f:
            for line in f:
                code, _ = split_asm_line(line)
                if not code or code[0].isspace():
                    continue
                m = re.match(r"^([A-Za-z0-9_.]+)", code)
                if m:
                    sym = m.group(1)
                    protected.add(sym)
                    protected.add(sym.upper())
    return protected

def split_asm_line(line):
    """
    Split an assembly line into (code_part, comment_part).
    Preserves column formatting.
    """
    s = line.rstrip('\r\n')
    s_strip = s.lstrip()
    if not s or s_strip.startswith('*') or s_strip.startswith(';'):
        return '', line

    pos = 0
    # Field 1: Label at col 0 (if any)
    if not s[0].isspace():
        m = re.match(r'^\S+', s)
        pos = m.end()

    # Skip whitespace between label and opcode
    m = re.search(r'\S', s[pos:])
    if not m:
        return s, ''
    pos += m.start()

    # Field 2: Opcode
    m = re.match(r'^\S+', s[pos:])
    op = m.group(0).upper()
    pos += m.end()

    # Skip whitespace between opcode and operand
    m = re.search(r'\S', s[pos:])
    if not m:
        return s, ''
    pos += m.start()

    # Field 3: Operand
    if op in ('FCC', 'FCS'):
        delim = s[pos]
        end_pos = s.find(delim, pos + 1)
        if end_pos != -1:
            pos = end_pos + 1
        else:
            pos = len(s)
    else:
        m = re.match(r'^\S+', s[pos:])
        pos += m.end()

    code_part = s[:pos]
    comment_part = s[pos:]
    return code_part, comment_part

class PreprocessorContext:
    def __init__(self):
        self.global_instance_id = 0

    def preprocess_content(self, content):
        lines = content.splitlines()
        out = []
        local_map = {}
        in_ifp1_defsfile = False

        for line_idx, line in enumerate(lines):
            stripped = line.strip()

            # 1. Blank line: resets local label scope in LWASM
            if not stripped:
                local_map = {}
                out.append(line)
                continue

            # 2. Comment conversion: ';' in column 0 -> '*'
            if stripped.startswith(';'):
                comment_line = '*' + stripped.lstrip('; \t')
                out.append(comment_line[:78])
                continue
            if stripped.startswith('*'):
                comment_line = '*' + stripped[1:]
                out.append(comment_line[:78])
                continue

            # Check for dts timestamp directive
            if re.match(r'^\s*dts\b', line, re.IGNORECASE):
                out.append('                    fcc       "Wed Sep 30 22:41:09 2026"')
                continue

            # Map use os9.d/scf.d/rbf.d to use defsfile
            if re.match(r'^\s*use\s+(os9\.d|scf\.d|rbf\.d)\b', line, re.IGNORECASE):
                out.append('                    use       defsfile')
                continue

            # 3. Check for IFP1 wrapping 'use defsfile'
            if re.match(r'^\s*ifp1\b', line, re.IGNORECASE):
                j = line_idx + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines) and re.match(r'^\s*use\s+defsfile\b', lines[j], re.IGNORECASE):
                    out.append('* [selfgen: stripped IFP1 around defsfile]')
                    in_ifp1_defsfile = True
                    continue

            if in_ifp1_defsfile and re.match(r'^\s*endc\b', line, re.IGNORECASE):
                out.append('* [selfgen: stripped ENDC around defsfile]')
                in_ifp1_defsfile = False
                continue

            # 4. IFNDEF -> IFNDF, ENDIF -> ENDC
            line = re.sub(r'\bIFNDEF\b', 'IFNDF', line, flags=re.IGNORECASE)
            line = re.sub(r'^\s*endif\b', ' endc', line, flags=re.IGNORECASE)

            # Strip trailing quote on character literals like #'0' -> #'0
            line = re.sub(r"#'(.)'", r"#'\1", line)

            # 5. Transform ERROR directive into comment for native asm
            if re.match(r'^\s+ERROR\b', line, re.IGNORECASE):
                out.append('* [selfgen: ERROR directive skipped in asm]: ' + line.strip()[:50])
                continue

            # 6. Simplify CLOCK_AND_STOP into CAS to prevent 8-char collisions
            line = re.sub(r'\bCLOCK_AND_STOP\.Exit0\b', 'CAS.Ex0', line)
            line = re.sub(r'\bCLOCK_AND_STOP\.Exit1\b', 'CAS.Ex1', line)
            line = re.sub(r'\bCLOCK_AND_STOP\.', 'CAS.', line)
            if 'CAS.Value' in line:
                line = re.sub(r'\(CAS\.R6Hz\|CAS\.IRQEn\|CAS\.Tick\)', '$23', line)
                line = re.sub(r'\(CLOCK_AND_STOP\.R6Hz\|CLOCK_AND_STOP\.IRQEn\|CLOCK_AND_STOP\.Tick\)', '$23', line)

            # 7. fill <val>,<count>
            m_fill = re.match(r'^(\s*)(\w*)\s+fill\s+([^,]+),([^;]+)(.*)$', line, re.IGNORECASE)
            if m_fill:
                indent, lbl, val, count, comment = m_fill.groups()
                lbl_part = f"{lbl} " if lbl else ""
                val = val.strip()
                count = count.strip()
                try:
                    c = int(count, 0)
                    out.append(f"{lbl_part}* PREPROCESSED FILL: {val}, {count}")
                    while c > 0:
                        chunk = min(c, 16)
                        out.append(f"{indent} fcb " + ",".join([val] * chunk))
                        c -= chunk
                    continue
                except ValueError:
                    # Symbolic fill count (e.g. KrnTail-* in inactive conditional)
                    if lbl_part:
                        out.append(f"{lbl_part}equ *")
                    out.append(f"* [selfgen: symbolic fill skipped in asm]")
                    continue

            # 8. Local label replacement in code part
            code_part, comment_part = split_asm_line(line)

            # Check if definition of local label at start of line
            m_def = re.match(r'^([A-Za-z0-9_.]+?)@(?:\s|$)', code_part)
            if m_def:
                name = m_def.group(1)
                clean_name = name.replace('.', '_')
                if name in local_map and local_map[name]['defined']:
                    self.global_instance_id += 1
                    local_map[name] = {'label': f"L{self.global_instance_id:04d}{clean_name[:2]}", 'defined': True}
                elif name in local_map:
                    local_map[name]['defined'] = True
                else:
                    self.global_instance_id += 1
                    local_map[name] = {'label': f"L{self.global_instance_id:04d}{clean_name[:2]}", 'defined': True}

            def repl_local(m):
                name = m.group(1)
                clean_name = name.replace('.', '_')
                if name not in local_map:
                    self.global_instance_id += 1
                    local_map[name] = {'label': f"L{self.global_instance_id:04d}{clean_name[:2]}", 'defined': False}
                return local_map[name]['label']

            code_part = re.sub(r'\b([A-Za-z0-9_.]+?)@', repl_local, code_part)

            # Convert bitwise OR '|' to '!' in expressions (skip FCC/FCS)
            m_op = re.search(r'\s+([A-Za-z]+)\s*', code_part)
            if m_op and m_op.group(1).upper() not in ('FCC', 'FCS'):
                code_part = code_part.replace('|', '!')

            if len(code_part) + len(comment_part) > 78:
                avail = max(0, 78 - len(code_part))
                comment_part = comment_part[:avail]
            out.append(code_part + comment_part)

        return "\n".join(out) + "\n"

def resolve_group_collisions(files_dict, protected_symbols):
    """
    Takes a dict of {filename: preprocessed_text} and resolves any 8-char
    prefix collisions among defined symbols across all files in the group.
    """
    file_lines = {name: text.splitlines() for name, text in files_dict.items()}

    # 1. Extract defined column-0 labels across all files
    defined = {}
    for bname, lines in file_lines.items():
        for lno, line in enumerate(lines):
            code, _ = split_asm_line(line)
            if not code or code[0].isspace():
                continue
            m = re.match(r"^([A-Za-z0-9_.]+)", code)
            if m:
                lbl = m.group(1)
                if lbl.endswith("@") or re.match(r"^L\d{4}", lbl):
                    continue
                if lbl in protected_symbols or lbl.upper() in protected_symbols:
                    continue
                defined.setdefault(lbl, []).append((bname, lno))

    # 2. Find collisions in first 8 characters
    pfx_map = {}
    for lbl in defined.keys():
        pfx = lbl[:8].upper()
        pfx_map.setdefault(pfx, []).append(lbl)

    rename_map = {}
    counter = 1
    for pfx, sym_list in sorted(pfx_map.items()):
        unique_syms = list(dict.fromkeys(sym_list))
        if len(unique_syms) > 1:
            for i, s in enumerate(unique_syms):
                if i == 0 and len(s) <= 8 and s.upper() == pfx:
                    continue
                while True:
                    new_sym = f"X{counter:05d}"
                    counter += 1
                    if new_sym not in defined and new_sym not in protected_symbols:
                        break
                rename_map[s] = new_sym

    if not rename_map:
        return files_dict

    # 3. Replace symbols in code part of all lines
    sorted_renames = sorted(rename_map.items(), key=lambda x: len(x[0]), reverse=True)
    out_files = {}

    for bname, lines in file_lines.items():
        out_lines = []
        for line in lines:
            code_part, comment_part = split_asm_line(line)
            if code_part:
                for old_sym, new_sym in sorted_renames:
                    if old_sym in code_part:
                        pat = r"(?<![A-Za-z0-9_.])" + re.escape(old_sym) + r"(?![A-Za-z0-9_.])"
                        code_part = re.sub(pat, new_sym, code_part)
            total_len = len(code_part) + len(comment_part)
            if total_len > 78:
                avail = max(0, 78 - len(code_part))
                comment_part = comment_part[:avail]
            out_lines.append(code_part + comment_part)
        out_files[bname] = "\n".join(out_lines) + "\n"

    return out_files

def preprocess_asm(content):
    ctx = PreprocessorContext()
    return ctx.preprocess_content(content)

def main():
    args = sys.argv[1:]
    if not args:
        print("Usage:")
        print("  selfgen_preprocess.py [--defs <defsfile>] <input.asm> [output.asm]")
        print("  selfgen_preprocess.py --group <out_dir> [--defs <defsfile>] <file1.asm> <file2.asm> ...")
        sys.exit(1)

    defs_path = None
    no_collisions = False
    if "--no-collisions" in args:
        args.remove("--no-collisions")
        no_collisions = True
    if "--defs" in args:
        idx = args.index("--defs")
        defs_path = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    protected = load_protected_from_defs(defs_path) if defs_path else set(DEFAULT_PROTECTED)

    if "--group" in args:
        idx = args.index("--group")
        out_dir = args[idx + 1]
        file_paths = args[idx + 2:]
        os.makedirs(out_dir, exist_ok=True)

        ctx = PreprocessorContext()
        files_dict = {}
        for p in file_paths:
            bname = os.path.basename(p)
            with open(p, "r", errors="ignore") as f:
                raw = f.read()
            files_dict[bname] = ctx.preprocess_content(raw)

        resolved_dict = resolve_group_collisions(files_dict, protected)

        for bname, content in resolved_dict.items():
            out_p = os.path.join(out_dir, bname)
            with open(out_p, "w") as f:
                f.write(content)
        return

    # Single-file mode
    in_file = args[0]
    out_file = args[1] if len(args) > 1 else in_file

    with open(in_file, "r", errors="ignore") as f:
        content = f.read()

    ctx = PreprocessorContext()
    p_content = ctx.preprocess_content(content)

    bname = os.path.basename(in_file)
    if no_collisions:
        final_content = p_content
    else:
        single_dict = {bname: p_content}
        resolved_dict = resolve_group_collisions(single_dict, protected)
        final_content = resolved_dict[bname]

    with open(out_file, "w") as f:
        f.write(final_content)

if __name__ == "__main__":
    main()
