********************************************************************
* Init - NitrOS-9 Configuration module for deep65280
*
* Adapted for deep65280 Level 2 (512KB MMU)

                    nam       Init
                    ttl       NitrOS-9 Configuration module

                    use       defsfile

tylg                set       Systm+$00
atrv                set       ReEnt+rev
rev                 set       $00
edition             set       1

                    mod       eom,name,tylg,atrv,$0FE0,$0015

start               equ       *
                    fcb       $27                 entries in device table
                    fdb       DefProg             offset to program to fork
                    fdb       DefDev              offset to default disk device
                    fdb       DefCons             offset to default console device
                    fdb       DefBoot             offset to boot module name
                    fcb       $01                 write protect flag (?)
                    fcb       Level               OS level (2)
                    fcb       3                   OS version
                    fcb       33                  OS major revision
                    fcb       33                  OS minor revision
                    ifne      H6309
                    fcb       Proc6309+CRCOff     feature byte #1
                    else
                    fcb       CRCOff              feature byte #1
                    endc
                    fcb       $00                 feature byte #2
                    fdb       OSStr
                    fdb       InstStr
                    fcb       0,0,0,0             reserved

name                fcs       "Init"
                    fcb       edition

DefProg             fcs       "SysGo"
DefDev              fcs       "/DD"
DefCons             fcs       "/Term"
DefBoot             fcs       "Boot"

OSStr               equ       *
                    fcc       "NitrOS-9/"
                    ifne      H6309
                    fcc       /6309 /
                    else
                    fcc       /6809 /
                    endc
                    fcc       /Level /
                    fcb       '0+Level
                    fcb       0

InstStr             equ       *
                    fcc       "DEEP65280"
                    fcb       0                   null-terminate the name string

                    emod
eom                 equ       *
                    end
