# boot_tfr9_verify.tcl - Launch deep65280 engine with newly compiled boot image
# Usage from Tcl prompt:
#   source /pc/boot_tfr9_verify.tcl

set Config(engine) "deep65280"
set Config(flat_img) "/pc/deep65280.new.img" ;# newly compiled boot image
set Config(drive0) "/pc/disk0.dsk"
set Config(drive1) ""
menu store Config
bye
