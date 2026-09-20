                    ifne      FLAT65280.D-1
FLAT65280.D         set       1

********************************************************************
* flat65280.d - NitrOS-9 System Definitions for flat65280v2
*
* Physical Memory Map:
*   $0000-$FEFF : 65,280 bytes of flat, contiguous RAM
*   $FF00-$FFFF : Protected Red Page (I/O & System Vectors)
*
* I/O Devices:
*   $FF80-$FF86 : EMUDSK Virtual Block Storage Controller
*   $FF88-$FF89 : ACIA MC6850 Serial UART
*   $FFF0-$FFFF : System Exception & Reset Vectors
********************************************************************

                    nam       flat65280.d
                    ttl       NitrOS-9 System Definitions for flat65280v2

                    IFNDEF    FLAT65280
FLAT65280           set       1
                    ENDC

* Ticks per second
                    IFNDEF    TkPerSec
TkPerSec            SET       60
                    ENDC

HW.Page             set       $00                 Device descriptor hardware page (extended addr)
HwBASE              equ       $FF88               Default hardware base address (ACIA)
ACIA_PORT           equ       $FF88

* EMUDSK registers ($FF80..$FF86)
EMU.Base            equ       $FF80
EMU.LSN             equ       $FF80
EMU.CMD             equ       $FF83
EMU.BUF             equ       $FF84
EMU.DRV             equ       $FF86

* ACIA registers ($FF88..$FF89)
ACIA.Base           equ       $FF88
ACIA.Stat           equ       $FF88
ACIA.Ctrl           equ       $FF88
ACIA.Data           equ       $FF89

                    endc
