# ====================================================================
# selfgen_build.tcl - Native NitrOS-9 Level 2 Self-Generation in NCL
# ====================================================================

9chgdir /dd/SRC 1
9chgdir /dd/CMDS 4

# Ensure terminal page pauses are disabled
set cid [9fork -m8K tmode pau=0]
9wait c e

proc asm_mod {s d} {
    puts "--> Assembling $s to $d"
    set cid [9fork -m32K asm $s u -o=$d]
    9wait c e
    if {+ $e} {
        puts "FAILED: $s with status $e"
        9fork -m8K stop 1
        error "Assembly of $s failed"
    }
    puts "DONE: $s"
}

puts "=================================================================="
puts "Starting NitrOS-9 Level 2 Self-Generation via NCL"
puts "=================================================================="

# Create /dd/MODS if needed
set cid [9fork -m8K makdir /dd/MODS]
9wait c e

puts "=== Slot 4: System Commands ==="
asm_mod dir.asm /dd/MODS/dir
asm_mod setime.asm /dd/MODS/setime
asm_mod date.asm /dd/MODS/date
asm_mod stop.asm /dd/MODS/stop

puts "=== Slot 5: SCF, Drivers, Shell, Utilities ==="
asm_mod scf.asm /dd/MODS/scf
asm_mod sc6850.asm /dd/MODS/sc6850
asm_mod clock.asm /dd/MODS/clock
asm_mod term_sc6850.asm /dd/MODS/term
asm_mod shell_21.asm /dd/MODS/shell_21
asm_mod mfree.asm /dd/MODS/mfree
asm_mod free.asm /dd/MODS/free
asm_mod procs.asm /dd/MODS/procs
asm_mod mdir.asm /dd/MODS/mdir

puts "=== Slot 6: Storage Subsystem ==="
asm_mod dd.asm /dd/MODS/dd
asm_mod emudsk.asm /dd/MODS/emudsk
asm_mod sysgo_dd.asm /dd/MODS/sysgo
asm_mod rbf.asm /dd/MODS/rbf
asm_mod ioman.asm /dd/MODS/ioman

puts "=== Slot 7: Init, KrnP2 & Krn ==="
asm_mod init.asm /dd/MODS/init
asm_mod krnp2.asm /dd/MODS/krnp2
asm_mod krn.asm /dd/MODS/krn

puts "=================================================================="
puts "Packing Boot Modules into Boot Image /dd/deep65280.new.img"
puts "=================================================================="
set cid [9fork -m8K del /dd/deep65280.new.img]
9wait c e

set cid [9fork -m8K selfgen_img /dd/MODS /dd/deep65280.new.img]
9wait c e
if {+ $e} {
    puts "FAILED: selfgen_img failed with status $e"
    9fork -m8K stop 1
    error "selfgen_img failed"
}

puts "=== Assembling Additional Level 2 Commands ==="
asm_mod copy.asm /dd/CMDS/copy
asm_mod del.asm /dd/CMDS/del
asm_mod dump.asm /dd/CMDS/dump
asm_mod echo.asm /dd/CMDS/echo
asm_mod makdir.asm /dd/CMDS/makdir
asm_mod pwd.asm /dd/CMDS/pwd
asm_mod pxd.asm /dd/CMDS/pxd
asm_mod tmode.asm /dd/CMDS/tmode
asm_mod touch.asm /dd/CMDS/touch
asm_mod unlink.asm /dd/CMDS/unlink

puts "=== Installing Built Utilities to /dd/CMDS ==="
foreach c {dir setime date stop shell_21 mfree free procs mdir} {
    puts "--> Installing $c to /dd/CMDS/$c"
    set cid [9fork -m8K copy -o=0 -r /dd/MODS/$c /dd/CMDS/$c]
    9wait c e
}

puts "=================================================================="
puts "NitrOS-9 Level 2 Self-Generation in NCL Succeeded!"
puts "=================================================================="
set cid [9fork -m8K dir -e /dd/MODS]
9wait c e

9fork -m8K stop 0
