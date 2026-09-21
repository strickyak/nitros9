********************************************************************
* Init - NitrOS-9 Configuration module for flat65280
*
* Adapted from init_tfr901.asm (Henry Strickland)

                    nam       Init
                    ttl       NitrOS-9 Configuration module

                    use       defsfile

tylg                set       Systm+$00
atrv                set       ReEnt+rev
rev                 set       $00
edition             set       7

*
* Usually, the last two words here would be the module entry
* address and the dynamic data size requirement. Neither value is
* needed for this module so they are pressed into service to show
* MaxMem and PollCnt. For example:
* $0FE0,$0015 means
* MaxMem = $0FE000
* PollCnt = $0015
*
                    mod       eom,name,tylg,atrv,$0FE0,$0015

start               equ       *
                    fcb       $27                 entries in device table
                    fdb       DefProg             offset to program to fork
                    fdb       DefDev              offset to default disk device
                    fdb       DefCons             offset to default console device
                    fdb       DefBoot             offset to boot module name
                    fcb       $01                 write protect flag (?)
                    fcb       Level               OS level
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
                    fcc       "FLAT65280"
                    fcb       0                   null-terminate the name string

                    emod
eom                 equ       *
                    end
