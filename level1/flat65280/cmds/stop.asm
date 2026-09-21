********************************************************************
* Stop - Stop or crash emulator utility for flat65280
*
* Usage:
*   stop 0   - Pokes $FC to $FF87 (exits emulator with status 0)
*   stop 1   - Pokes $FD to $FF87 (exits emulator with status 1)
*   stop ... - Any other argument pokes $FE to $FF87 (induces crash / core dump)
********************************************************************

                    nam       Stop
                    ttl       Stop emulator utility

                    ifp1
                    use       defsfile
                    endc

                    IFNDEF    CLOCK_AND_STOP.Base
CLOCK_AND_STOP.Base       equ       $FF87
CLOCK_AND_STOP.Exit0      equ       $FC
CLOCK_AND_STOP.Exit1      equ       $FD
CLOCK_AND_STOP.Crash      equ       $FE
                    ENDC

tylg                set       Prgrm+Objct
atrv                set       ReEnt+rev
rev                 set       $00
edition             set       1

                    mod       eom,name,tylg,atrv,start,size

                    org       0
u0000               rmb       200
size                equ       .

name                fcs       /stop/
                    fcb       edition

start
* Skip leading whitespace
SkipSpc             lda       ,x+
                    cmpa      #C$SPAC
                    beq       SkipSpc

* Check for '0' or '1'
                    cmpa      #'0'
                    beq       Chk0
                    cmpa      #'1'
                    beq       Chk1
                    bra       DoCrash

* '0' argument: verify nothing follows, then poke $FC to $FF87
Chk0                bsr       ChkEnd
                    bcs       DoCrash
                    lda       #CLOCK_AND_STOP.Exit0
                    sta       >CLOCK_AND_STOP.Base
                    clrb
                    os9       F$Exit

* '1' argument: verify nothing follows, then poke $FD to $FF87
Chk1                bsr       ChkEnd
                    bcs       DoCrash
                    lda       #CLOCK_AND_STOP.Exit1
                    sta       >CLOCK_AND_STOP.Base
                    ldb       #1
                    os9       F$Exit

* Any other argument (or empty, or syntax error): poke $FE to $FF87 (crash)
DoCrash             lda       #CLOCK_AND_STOP.Crash
                    sta       >CLOCK_AND_STOP.Base
                    ldb       #$FE
                    os9       F$Exit

* Check that remainder of line contains only spaces or terminates at CR
* Returns Carry clear on valid end of argument, Carry set on extra non-space characters
ChkEnd
EndLoop             lda       ,x+
                    cmpa      #C$SPAC
                    beq       EndLoop
                    cmpa      #C$CR
                    beq       EndOk
                    cmpa      #0                  ; null-terminated string check
                    beq       EndOk
                    coma                          ; set Carry flag (error)
                    rts
EndOk               clra                          ; clear Carry flag (success)
                    rts

                    emod
eom                 equ       *
                    end
