# boot_tfr9.tcl - Launch flat65280 engine on TFR911 firmware
# Usage from Tcl prompt:
#   source /pc/boot_tfr9.tcl

set Config(engine) "flat65280"
set Config(flat_img) "/pc/flat65280.img" ;# empty string uses embedded fallback image
set Config(drive0) "/pc/flat0.dsk"
set Config(drive1) ""
menu store Config
bye
