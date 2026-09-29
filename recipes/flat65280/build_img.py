#!/usr/bin/env python3
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MOD_DIR = os.path.join(SCRIPT_DIR, ".mods")

IMG_SIZE = 65536
START_ADDR = 0x0800

MOD_PATHS = [
    ("Kernel (part 1)", os.path.join(MOD_DIR, "krn")),
    ("Kernel (part 2)", os.path.join(MOD_DIR, "krnp2")),
    ("Configuration",   os.path.join(MOD_DIR, "init")),
    ("I/O Manager",     os.path.join(MOD_DIR, "ioman")),
    ("RBF Manager",     os.path.join(MOD_DIR, "rbf")),
    ("SCF Manager",     os.path.join(MOD_DIR, "scf")),
    ("ACIA Driver",     os.path.join(MOD_DIR, "sc6850")),
    ("Clock Driver",    os.path.join(MOD_DIR, "clock")),
    ("Term Descriptor", os.path.join(MOD_DIR, "term")),
    ("EmuDsk Driver",   os.path.join(MOD_DIR, "emudsk")),
    ("DD Descriptor",   os.path.join(MOD_DIR, "dd")),
    ("SysGo Module",    os.path.join(MOD_DIR, "sysgo")),
    ("Shell Command",   os.path.join(MOD_DIR, "shell_21")),
    ("mfree Command",   os.path.join(MOD_DIR, "mfree")),
    ("free Command",    os.path.join(MOD_DIR, "free")),
    ("procs Command",   os.path.join(MOD_DIR, "procs")),
    ("mdir Command",    os.path.join(MOD_DIR, "mdir")),
    ("dir Command",     os.path.join(MOD_DIR, "dir")),
    ("setime Command",  os.path.join(MOD_DIR, "setime")),
    ("date Command",    os.path.join(MOD_DIR, "date")),
    ("stop Command",    os.path.join(MOD_DIR, "stop")),
    ("Basic09",         "/home/strick/modoc/coco-shelf/nitros9-languages/basic09/basic09_6809"),
]

output_img = os.path.join(SCRIPT_DIR, "flat65280.img")
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
# In Level 1, vectors point to trampolines copied to low RAM ($0100..$010F)
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
