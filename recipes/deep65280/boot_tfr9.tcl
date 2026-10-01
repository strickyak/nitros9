# boot_tfr9.tcl - Launch deep65280 engine on TFR911 firmware
# Usage from Tcl prompt:
#   source /pc/boot_tfr9.tcl

set Config(engine) "deep65280"
set Config(flat_img) "/pc/deep65280.img" ;# deep65280.img 64KB boot image
set Config(drive0) "/pc/disk0.dsk"
set Config(drive1) ""
menu store Config
bye
