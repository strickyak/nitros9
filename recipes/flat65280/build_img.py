#!/usr/bin/env python3
import sys
import os

IMG_SIZE = 65536
START_ADDR = 0x0800

MOD_PATHS = [
    ("Kernel (part 1)", "recipes/flat65280/.mods/krn"),
    ("Kernel (part 2)", "recipes/flat65280/.mods/krnp2"),
    ("Configuration",   "recipes/flat65280/.mods/init"),
    ("I/O Manager",     "recipes/flat65280/.mods/ioman"),
    ("RBF Manager",     "recipes/flat65280/.mods/rbf"),
    ("SCF Manager",     "recipes/flat65280/.mods/scf"),
    ("ACIA Driver",     "recipes/flat65280/.mods/sc6850"),
    ("Term Descriptor", "recipes/flat65280/.mods/term"),
    ("EmuDsk Driver",   "recipes/flat65280/.mods/emudsk"),
    ("DD Descriptor",   "recipes/flat65280/.mods/dd"),
    ("Shell Command",   "recipes/flat65280/.mods/shell_21"),
    ("mfree Command",   "recipes/flat65280/.mods/mfree"),
    ("free Command",    "recipes/flat65280/.mods/free"),
    ("procs Command",   "recipes/flat65280/.mods/procs"),
    ("mdir Command",    "recipes/flat65280/.mods/mdir"),
    ("dir Command",     "recipes/flat65280/.mods/dir"),
    ("Basic09",         "/home/strick/modoc/coco-shelf/nitros9-languages/basic09/basic09_6809"),
]

output_img = "recipes/flat65280/flat65280.img"
if len(sys.argv) > 1:
    output_img = sys.argv[1]

img = bytearray(IMG_SIZE)

current_addr = START_ADDR

print(f"{'Role':<18} {'File':<25} {'Addr':<8} {'Size':<8} {'Name':<10} {'Exec':<8}")
print("-" * 80)

krn_exec = None

for role, path in MOD_PATHS:
    with open(path, "rb") as f:
        data = f.read()
    
    assert data[0] == 0x87 and data[1] == 0xCD, f"Invalid sync bytes in {path}"
    mod_size = (data[2] << 8) | data[3]
    assert mod_size == len(data), f"Size mismatch in {path}: header says {mod_size}, got {len(data)}"
    
    name_offset = (data[4] << 8) | data[5]
    name_bytes = bytearray()
    p = name_offset
    while p < len(data):
        b = data[p]
        p += 1
        name_bytes.append(b & 0x7F)
        if b & 0x80:
            break
    name = name_bytes.decode('ascii', errors='replace')
    
    exec_offset = (data[9] << 8) | data[10]
    
    if krn_exec is None:
        krn_exec = current_addr + exec_offset
    
    print(f"{role:<18} {os.path.basename(path):<25} ${current_addr:04X}   ${len(data):04X} ({len(data):<5}) {name:<10} ${exec_offset:04X}")
    
    img[current_addr:current_addr + len(data)] = data
    current_addr += len(data)

print("-" * 80)
print(f"Total module space used: ${START_ADDR:04X}..${current_addr:04X} ({current_addr - START_ADDR} bytes)")
print(f"Free RAM before I/O: ${current_addr:04X}..$FEFF ({0xFF00 - current_addr} bytes)")

# Top-page CPU Vectors ($FFF0..$FFFF)
img[0xFFF0:0xFFF2] = (0x0100).to_bytes(2, 'big') # TRAP
img[0xFFF2:0xFFF4] = (0x0100).to_bytes(2, 'big') # SWI3
img[0xFFF4:0xFFF6] = (0x0103).to_bytes(2, 'big') # SWI2
img[0xFFF6:0xFFF8] = (0x010F).to_bytes(2, 'big') # FIRQ
img[0xFFF8:0xFFFA] = (0x010C).to_bytes(2, 'big') # IRQ
img[0xFFFA:0xFFFC] = (0x0106).to_bytes(2, 'big') # SWI
img[0xFFFC:0xFFFE] = (0x0109).to_bytes(2, 'big') # NMI
img[0xFFFE:0x10000] = (krn_exec).to_bytes(2, 'big') # RESET

print(f"Reset vector ($FFFE) set to: ${krn_exec:04X}")

with open(output_img, "wb") as f:
    f.write(img)

print(f"Successfully generated {output_img} ({len(img)} bytes)")
