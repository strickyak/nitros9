# boot_tfr9.tcl - Launch flat65280 engine on TFR911 firmware
# Usage from Tcl prompt:
#   source /pc/recipes/flat65280/boot_tfr9.tcl

set Config(engine) "flat65280"
set Config(flat_img) "" ;# empty string uses embedded fallback image
set Config(drive0) "/pc/recipes/flat65280/flat0.dsk"
set Config(drive1) ""
menu store Config
bye
