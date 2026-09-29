#!/usr/bin/env python3
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MOD_DIR = os.path.join(SCRIPT_DIR, ".mods")

IMG_SIZE = 65536
SLOT_SIZE = 8192
START_ADDR = 0x2000       # Slot 1 start ($2000)
MAX_MOD_ADDR = 0xE000     # Slots 1..6 end ($E000)
KRN_START_ADDR = 0xEE00   # Kernel start ($EE00 in Slot 7)

KRN_PATH = os.path.join(MOD_DIR, "krn")

SLOT_GROUPS = [
    # Slot 4 ($8000..$9FFF): Remaining commands abutting $A000
    (0x8000, 0xA000, [
        ("dir Command",     os.path.join(MOD_DIR, "dir")),
        ("setime Command",  os.path.join(MOD_DIR, "setime")),
        ("date Command",    os.path.join(MOD_DIR, "date")),
        ("stop Command",    os.path.join(MOD_DIR, "stop")),
    ]),
    # Slot 5 ($A000..$BFFF): SCF, drivers, shell & commands abutting $C000
    (0xA000, 0xC000, [
        ("SCF Manager",     os.path.join(MOD_DIR, "scf")),
        ("ACIA Driver",     os.path.join(MOD_DIR, "sc6850")),
        ("Clock Driver",    os.path.join(MOD_DIR, "clock")),
        ("Term Descriptor", os.path.join(MOD_DIR, "term")),
        ("Shell Command",   os.path.join(MOD_DIR, "shell_21")),
        ("mfree Command",   os.path.join(MOD_DIR, "mfree")),
        ("free Command",    os.path.join(MOD_DIR, "free")),
        ("procs Command",   os.path.join(MOD_DIR, "procs")),
        ("mdir Command",    os.path.join(MOD_DIR, "mdir")),
    ]),
    # Slot 6 ($C000..$DFFF): Storage subsystem abutting $E000 (ioman placed highest in Slot 6)
    (0xC000, 0xE000, [
        ("DD Descriptor",   os.path.join(MOD_DIR, "dd")),
        ("EmuDsk Driver",   os.path.join(MOD_DIR, "emudsk")),
        ("SysGo Module",    os.path.join(MOD_DIR, "sysgo")),
        ("RBF Manager",     os.path.join(MOD_DIR, "rbf")),
        ("I/O Manager",     os.path.join(MOD_DIR, "ioman")),
    ]),
    # Slot 7 lower ($E000..$EE00): init & krnp2 abutting $EE00 (krnp2 placed highest in memory)
    (0xE000, KRN_START_ADDR, [
        ("Configuration",   os.path.join(MOD_DIR, "init")),
        ("Kernel (part 2)", os.path.join(MOD_DIR, "krnp2")),
    ]),
]

output_img = os.path.join(SCRIPT_DIR, "deep65280.img")
if len(sys.argv) > 1:
    output_img = sys.argv[1]

img = bytearray(IMG_SIZE)

print(f"{'Role':<18} {'File':<25} {'Addr':<8} {'Size':<8} {'Name':<10} {'Exec':<8}")
print("-" * 80)

# 1. Place pre-loaded modules in Slots 4..7 packed against top of each slot
for slot_start, slot_end, mod_list in SLOT_GROUPS:
    mod_data = []
    for role, path in mod_list:
        with open(path, "rb") as f:
            data = f.read()
        assert data[0] == 0x87 and data[1] == 0xCD, f"Invalid sync bytes in {path}"
        mod_size = (data[2] << 8) | data[3]
        assert mod_size == len(data), f"Size mismatch in {path}: header says {mod_size}, got {len(data)}"
        mod_data.append((role, path, data))

    total_slot_size = sum(len(d) for _, _, d in mod_data)
    curr_addr = slot_end - total_slot_size
    assert curr_addr >= slot_start, f"Slot overflow: {total_slot_size} > {slot_end - slot_start} for slot ending at ${slot_end:04X}"

    for role, path, data in mod_data:
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

        print(f"{role:<18} {os.path.basename(path):<25} ${curr_addr:04X}   ${len(data):04X} ({len(data):<5}) {name:<10} ${exec_offset:04X}")

        img[curr_addr:curr_addr + len(data)] = data
        curr_addr += len(data)
    assert curr_addr == slot_end, f"Address mismatch: expected ${slot_end:04X}, got ${curr_addr:04X}"

# 2. Place Kernel in Slot 7 ($EE00..$FEFF)
with open(KRN_PATH, "rb") as f:
    krn_data = f.read()

assert krn_data[0] == 0x87 and krn_data[1] == 0xCD, f"Invalid sync bytes in {KRN_PATH}"
krn_mod_size = (krn_data[2] << 8) | krn_data[3]
krn_exec_offset = (krn_data[9] << 8) | krn_data[10]
krn_exec = KRN_START_ADDR + krn_exec_offset

print(f"{'Kernel (part 1)':<18} {'krn':<25} ${KRN_START_ADDR:04X}   ${len(krn_data):04X} ({len(krn_data):<5}) {'Krn':<10} ${krn_exec_offset:04X}")
print("-" * 80)
print(f"Slot 0 ($0000..$1FFF): System globals, DP, stack (zeroed)")
print(f"Slots 1..3 ($2000..$7FFF) + lower Slot 4: Free dynamic RAM (31KB)")
print(f"Slots 4..7 ($99DB..$EDFF): Preloaded modules (high-packed, abutting $EE00)")
print(f"Slot 7 ($EE00..$FFFF): Kernel at ${KRN_START_ADDR:04X}, size ${len(krn_data):04X}, ends at ${KRN_START_ADDR + len(krn_data):04X}")

assert KRN_START_ADDR + len(krn_data) == 0xFF00, f"Kernel must end exactly at $FF00, got ${KRN_START_ADDR + len(krn_data):04X}"
img[KRN_START_ADDR:KRN_START_ADDR + len(krn_data)] = krn_data

# 3. Top-page CPU Vectors ($FFF0..$FFFF)
# Vectors point to trampolines in locked $FExx page ($FEEE..$FEFD)
img[0xFFF0:0xFFF2] = (0xFEEE).to_bytes(2, 'big') # TRAP / Reserved
img[0xFFF2:0xFFF4] = (0xFEEE).to_bytes(2, 'big') # SWI3
img[0xFFF4:0xFFF6] = (0xFEF1).to_bytes(2, 'big') # SWI2
img[0xFFF6:0xFFF8] = (0xFEF4).to_bytes(2, 'big') # FIRQ
img[0xFFF8:0xFFFA] = (0xFEF7).to_bytes(2, 'big') # IRQ
img[0xFFFA:0xFFFC] = (0xFEFA).to_bytes(2, 'big') # SWI
img[0xFFFC:0xFFFE] = (0xFEFD).to_bytes(2, 'big') # NMI
img[0xFFFE:0x10000] = (krn_exec).to_bytes(2, 'big') # RESET

print(f"Reset vector ($FFFE) set to: ${krn_exec:04X}")
print(f"SWI2 vector ($FFF4) set to:  $FEF1")
print(f"IRQ vector ($FFF8) set to:   $FEF7")

with open(output_img, "wb") as f:
    f.write(img)

print(f"Successfully generated {output_img} ({len(img)} bytes)")
