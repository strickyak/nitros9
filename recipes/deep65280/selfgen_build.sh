* ====================================================================
* selfgen_build.sh - Native NitrOS-9 Level 2 Self-Generation Script
* ====================================================================

chx /dd/CMDS
chd /dd/SRC
tmode pau=0

echo
echo ==================================================================
echo Starting NitrOS-9 Level 2 Self-Generation (21 Boot Modules)
echo ==================================================================
deldir -e /dd/MODS
makdir /dd/MODS

* Slot 4 commands
echo Assembling Slot 4 modules...
asm #32K dir.asm u -o=/dd/MODS/dir
asm #32K setime.asm u -o=/dd/MODS/setime
asm #32K date.asm u -o=/dd/MODS/date
asm #32K stop.asm u -o=/dd/MODS/stop

* Slot 5 SCF, drivers, shell & commands
echo Assembling Slot 5 modules...
asm #32K scf.asm u -o=/dd/MODS/scf
asm #32K sc6850.asm u -o=/dd/MODS/sc6850
asm #32K clock.asm u -o=/dd/MODS/clock
asm #32K term_sc6850.asm u -o=/dd/MODS/term
asm #32K shell_21.asm u -o=/dd/MODS/shell_21
asm #32K mfree.asm u -o=/dd/MODS/mfree
asm #32K free.asm u -o=/dd/MODS/free
asm #32K procs.asm u -o=/dd/MODS/procs
asm #32K mdir.asm u -o=/dd/MODS/mdir

* Slot 6 Storage subsystem & managers
echo Assembling Slot 6 modules...
asm #32K dd.asm u -o=/dd/MODS/dd
asm #32K emudsk.asm u -o=/dd/MODS/emudsk
asm #32K sysgo_dd.asm u -o=/dd/MODS/sysgo
asm #32K rbf.asm u -o=/dd/MODS/rbf
asm #32K ioman.asm u -o=/dd/MODS/ioman

* Slot 7 Init, KrnP2 & Krn
echo Assembling Slot 7 modules...
asm #32K init.asm u -o=/dd/MODS/init
asm #32K krnp2.asm u -o=/dd/MODS/krnp2
asm #32K krn.asm u -o=/dd/MODS/krn

echo
echo ==================================================================
echo Packing Boot Modules into Boot Image /dd/deep65280.new.img
echo ==================================================================
selfgen_img #8K /dd/MODS /dd/deep65280.new.img

echo
echo ==================================================================
echo Assembling Level 2 Commands into /dd/CMDS
echo ==================================================================
asm #32K asm.asm u -o=/dd/CMDS/asm
asm #32K attr.asm u -o=/dd/CMDS/attr
asm #32K backup.asm u -o=/dd/CMDS/backup
asm #32K bawk.asm u -o=/dd/CMDS/bawk
asm #32K binex.asm u -o=/dd/CMDS/binex
asm #32K build.asm u -o=/dd/CMDS/build
asm #32K calldbg.asm u -o=/dd/CMDS/calldbg
asm #32K cmp.asm u -o=/dd/CMDS/cmp
asm #32K copy.asm u -o=/dd/CMDS/copy
asm #32K cputype.asm u -o=/dd/CMDS/cputype
asm #32K dcheck.asm u -o=/dd/CMDS/dcheck
asm #32K debug.asm u -o=/dd/CMDS/debug
asm #32K ded.asm u -o=/dd/CMDS/ded
asm #32K deiniz.asm u -o=/dd/CMDS/deiniz
asm #32K del.asm u -o=/dd/CMDS/del
asm #32K deldir.asm u -o=/dd/CMDS/deldir
asm #32K devs.asm u -o=/dd/CMDS/devs
asm #32K dir_cb.asm u -o=/dd/CMDS/dir_cb
asm #32K dirsort.asm u -o=/dd/CMDS/dirsort
asm #32K disasm.asm u -o=/dd/CMDS/disasm
asm #32K display.asm u -o=/dd/CMDS/display
asm #32K dmem.asm u -o=/dd/CMDS/dmem
asm #32K dmode.asm u -o=/dd/CMDS/dmode
asm #32K dsave.asm u -o=/dd/CMDS/dsave
asm #32K dump.asm u -o=/dd/CMDS/dump
asm #32K echo.asm u -o=/dd/CMDS/echo
asm #32K edit.asm u -o=/dd/CMDS/edit
asm #32K error.asm u -o=/dd/CMDS/error
asm #32K exbin.asm u -o=/dd/CMDS/exbin
asm #32K format.asm u -o=/dd/CMDS/format
asm #32K format_d64.asm u -o=/dd/CMDS/format_d64
asm #32K go51.asm u -o=/dd/CMDS/go51
asm #32K help.asm u -o=/dd/CMDS/help
asm #32K ident.asm u -o=/dd/CMDS/ident
asm #32K iniz.asm u -o=/dd/CMDS/iniz
asm #32K irqs.asm u -o=/dd/CMDS/irqs
asm #32K keyrpt.asm u -o=/dd/CMDS/keyrpt
asm #32K link.asm u -o=/dd/CMDS/link
asm #32K list.asm u -o=/dd/CMDS/list
asm #32K load.asm u -o=/dd/CMDS/load
asm #32K login.asm u -o=/dd/CMDS/login
asm #32K makdir.asm u -o=/dd/CMDS/makdir
asm #32K merge.asm u -o=/dd/CMDS/merge
asm #32K minted.asm u -o=/dd/CMDS/minted
asm #32K mmap.asm u -o=/dd/CMDS/mmap
asm #32K modpatch.asm u -o=/dd/CMDS/modpatch
asm #32K more.asm u -o=/dd/CMDS/more
asm #32K mpi.asm u -o=/dd/CMDS/mpi
asm #32K ngu.asm u -o=/dd/CMDS/ngu
asm #32K padrom.asm u -o=/dd/CMDS/padrom
asm #32K park.asm u -o=/dd/CMDS/park
asm #32K pmap.asm u -o=/dd/CMDS/pmap
asm #32K printerr.asm u -o=/dd/CMDS/printerr
asm #32K proc.asm u -o=/dd/CMDS/proc
asm #32K prompt.asm u -o=/dd/CMDS/prompt
asm #32K pwd.asm u -o=/dd/CMDS/pwd
asm #32K pxd.asm u -o=/dd/CMDS/pxd
asm #32K rename.asm u -o=/dd/CMDS/rename
asm #32K save.asm u -o=/dd/CMDS/save
asm #32K shellplus.asm u -o=/dd/CMDS/shellplus
asm #32K sleep.asm u -o=/dd/CMDS/sleep
asm #32K smap.asm u -o=/dd/CMDS/smap
asm #32K tee.asm u -o=/dd/CMDS/tee
asm #32K tmode.asm u -o=/dd/CMDS/tmode
asm #32K touch.asm u -o=/dd/CMDS/touch
asm #32K tsmon.asm u -o=/dd/CMDS/tsmon
asm #32K tuneport.asm u -o=/dd/CMDS/tuneport
asm #32K unlink.asm u -o=/dd/CMDS/unlink
asm #32K verify.asm u -o=/dd/CMDS/verify
asm #32K xmode_bld.asm u -o=/dd/CMDS/xmode

* Aliases
copy -o=0 -r /dd/CMDS/shell_21 /dd/CMDS/shell
copy -o=0 -r /dd/CMDS/list /dd/CMDS/type

* Set execution attributes on commands
attr -q -pe -npw -pr -e -w -r /dd/CMDS/*

echo
echo ==================================================================
echo NitrOS-9 Self-Generation Complete!
echo ==================================================================
dir /dd/MODS
ident /dd/deep65280.new.img
