                    ifne      D65280_D-1
D65280_D            set       1

********************************************************************
* deep65280.d - NitrOS-9 Level 2 System Definitions for deep65280v2
*
* Physical Memory: 512KB RAM in 64 8KB blocks ($00..$3F)
* MMU: CoCo 3 compatible DAT registers ($FFA0..$FFAF) & Task reg ($FF91)
*
* Memory Layout at Boot:
*   Physical Pages $38..$3F populated with 64KB raw image
*   Task 0 Active ($FF91 = 0)
*   $FFA0..$FFA7 = $38, $39, $3A, $3B, $3C, $3D, $3E, $3F
*   $FFA8..$FFAF = $38, $39, $3A, $3B, $3C, $3D, $3E, $3F
*   Locked $FExx page permanently mapped to physical page $3F
*   Hardware vectors $FFF0..$FFFF permanently mapped to physical page $3F
*
* I/O Devices:
*   $FF80-$FF86 : EMUDSK Virtual Block Storage Controller
*   $FF87       : CLOCK_AND_STOP Periodic Clock & Emulator Control
*   $FF88-$FF89 : ACIA MC6850 Serial UART
*   $FF90       : GIME Init0 (Ignored / read 0)
*   $FF91       : Task Switch (Bit 0 = Task 0/1)
*   $FFA0-$FFA7 : Task 0 MMU DAT Registers
*   $FFA8-$FFAF : Task 1 MMU DAT Registers
*   $FFF0-$FFFF : System Exception & Reset Vectors
********************************************************************

                    nam       deep65280.d
                    ttl       NitrOS-9 Level 2 System Definitions for deep65280v2

deep65280           set       1

* 256KB memory configuration flag (defaults to 0 if not defined)
                    IFDEF     DEEP_256K
                    ELSE
DEEP_256K           set       0
                    ENDC

* Ticks per second and time slice
                    IFDEF     TkPerSec
                    IFNE      TkPerSec-6
                    ERROR     TkPerSec must be 6
                    ENDC
                    ELSE
TkPerSec            equ       6
                    ENDC

                    IFDEF     TkPerTS
                    IFNE      TkPerTS-1
                    ERROR     TkPerTS must be 1
                    ENDC
                    ELSE
TkPerTS             equ       1
                    ENDC

* Device descriptor hardware page & base
HW.Page             set       $07
HwBASE              equ       $FF88
* Terminal page pause default (0 = disable screen pausing)
Pauses              set       0
ACIA_PORT           equ       $FF88

* EMUDSK registers ($FF80..$FF86)
EMU.Base            equ       $FF80
EMU.LSN             equ       $FF80
EMU.CMD             equ       $FF83
EMU.BUF             equ       $FF84
EMU.DRV             equ       $FF86

* CLOCK_AND_STOP register ($FF87)
CLOCK_AND_STOP            equ       1
CLOCK_AND_STOP.Base       equ       $FF87
CLOCK_AND_STOP.Tick       equ       %00000001
CLOCK_AND_STOP.IRQEn      equ       %00000010
CLOCK_AND_STOP.R60Hz      equ       $00
CLOCK_AND_STOP.R50Hz      equ       $10
CLOCK_AND_STOP.R6Hz       equ       $20
CLOCK_AND_STOP.R01Hz      equ       $30
CLOCK_AND_STOP.RateM      equ       $30
CLOCK_AND_STOP.Value      equ       (CLOCK_AND_STOP.R6Hz|CLOCK_AND_STOP.IRQEn|CLOCK_AND_STOP.Tick)
CLOCK_AND_STOP.Exit0      equ       $FC
CLOCK_AND_STOP.Exit1      equ       $FD
CLOCK_AND_STOP.Crash      equ       $FE

* ACIA registers ($FF88..$FF89)
ACIA.Base           equ       $FF88
ACIA.Stat           equ       $FF88
ACIA.Ctrl           equ       $FF88
ACIA.Data           equ       $FF89

****************************************
* Dynamic Address Translator Definitions
****************************************
DAT.BlCt            EQU       8                   D.A.T. blocks/address space
DAT.BlSz            EQU       (256/DAT.BlCt)*256  D.A.T. block size (8192)
DAT.ImSz            EQU       DAT.BlCt*2          D.A.T. Image size (16 bytes)
DAT.Addr            EQU       -(DAT.BlSz/256)     D.A.T. MSB Address bits
DAT.Task            EQU       $FF91               Task Register address
DAT.TkCt            EQU       32                  Number of DAT Tasks
DAT.Regs            EQU       $FFA0               DAT Block Registers base address
DAT.Free            EQU       $333E               Free Block Number
DAT.BlMx            EQU       $3F                 Maximum Block number (63 for 512KB)
DAT.BMSz            EQU       $40                 Memory Block Map size (64 bytes)
DAT.WrPr            EQU       0                   no write protect
DAT.WrEn            EQU       0                   no write enable
SysTask             EQU       0                   System Task number
SysBlock            EQU       $00                 System globals block (physical block $00)
IOBlock             EQU       $3F
ROMBlock            EQU       $3F
IOAddr              EQU       $7F
ROMCount            EQU       1                   number of blocks of ROM (High RAM Block)
RAMCount            EQU       1                   initial blocks of RAM
MoveBlks            EQU       DAT.BlCt-ROMCount-2 Block numbers used for copies (5)
BlockTyp            EQU       1
ByteType            EQU       2
Limited             EQU       1
UnLimitd            EQU       2
RAMCheck            EQU       BlockTyp
ROMCheck            EQU       Limited
LastRAM             EQU       IOBlock             maximum RAM block number

KrnBlk              SET       $3F
Bt.Start            SET       $2000
SHIFTBIT            EQU       0

                    endc
