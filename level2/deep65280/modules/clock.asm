********************************************************************
* clock - NitrOS-9 Level 2 Clock module for deep65280v2
*
* Uses CLOCK_AND_STOP periodic timer register at $FF87.
********************************************************************

                    nam       Clock
                    ttl       Clock for deep65280 Level 2

                    ifp1
                    use       defsfile
                    endc

Edtn                equ       1
Vrsn                equ       0

********************************************************************
* Module Header
********************************************************************
                    mod       len,name,Systm+Objct,ReEnt+Vrsn,Init,0

name                fcs       "Clock"
                    fcb       Edtn

********************************************************************
* Service Calls Table
********************************************************************
NewSvc              fcb       F$Time
                    fdb       F.Time-*-2
                    fcb       F$VIRQ
                    fdb       F.VIRQ-*-2
                    fcb       F$Alarm
                    fdb       F.Alarm-*-2
                    fcb       F$STime
                    fdb       F.STime-*-2
                    fcb       $80       end of service call table

********************************************************************
* SvcIRQ - Primary IRQ handler entry point
*
* Called on every hardware IRQ. Check if CLOCK_AND_STOP caused it.
********************************************************************
SvcIRQ              lda       >CLOCK_AND_STOP.Base  read clock register
                    bita      #CLOCK_AND_STOP.Tick  clock timer tick?
                    beq       NotClock

* Clock IRQ: acknowledge and re-arm timer
                    lda       #CLOCK_AND_STOP.Value quench and re-arm
                    sta       >CLOCK_AND_STOP.Base
                    ldx       <D.VIRQ   VIRQ handler
                    clr       <D.QIRQ   flag as clock IRQ
                    bra       ContIRQ

NotClock            leax      DoPoll,pcr not clock IRQ, poll other devices
                    lda       #$FF
                    sta       <D.QIRQ   flag as non-clock IRQ

ContIRQ             stx       <D.SvcIRQ
                    jmp       [D.XIRQ]  chain to kernel timeslice handler

********************************************************************
* SvcVIRQ - Clock Tick Processing
********************************************************************
SvcVIRQ             clra
                    pshs      a
                    ldy       <D.CLTb   get address of VIRQ table
                    bra       virqent

virqloop            ldd       Vi.Cnt,x  decrement tick count
                    subd      #$0001
                    bne       notzero
                    lda       Vi.Stat,x
                    bmi       doreset
                    lbsr      DelVIRQ
doreset             ora       #$01      mark VIRQ as triggered
                    sta       Vi.Stat,x
                    lda       #$80
                    sta       ,s
                    ldd       Vi.Rst,x
notzero             std       Vi.Cnt,x
virqent             ldx       ,y++
                    bne       virqloop

                    puls      a         get VIRQ status
                    bsr       DoPoll    poll all registered devices

KbdCheck            jsr       [>D.AltIRQ]

                    dec       <D.Tick   end of second?
                    bne       VIRQend
                    lda       #TkPerSec reset tick count
                    sta       <D.Tick

                    inc       <D.Sec    increment second
                    lda       <D.Sec
                    cmpa      #60       end of minute?
                    blo       VIRQend
                    clr       <D.Sec

                    inc       <D.Min
                    lda       <D.Min
                    cmpa      #60
                    blo       VIRQend
                    clr       <D.Min

                    inc       <D.Hour
                    lda       <D.Hour
                    cmpa      #24
                    blo       VIRQend
                    clr       <D.Hour

                    inc       <D.Day
                    lda       <D.Day
                    cmpa      #32       simple day roll
                    blo       VIRQend
                    lda       #1
                    sta       <D.Day

VIRQend             jmp       [>D.Clock] jump to kernel timeslice routine

********************************************************************
* DoPoll - Poll registered interrupt devices
********************************************************************
DoPoll              pshs      b
                    clrb
DoPollLp            jsr       [>D.Poll]
                    bcs       DoPollDn
                    incb
                    bra       DoPollLp
DoPollDn            tstb
                    puls      b,pc

********************************************************************
* F$VIRQ - Virtual IRQ handler
********************************************************************
F.VIRQ              pshs      cc
                    orcc      #IntMasks
                    ldy       <D.CLTb
                    ldx       <D.Init
                    ldb       PollCnt,x
                    ldx       R$X,u
                    beq       RemVIRQ
FindVIRQ            ldx       ,y++
                    beq       AddVIRQ
                    decb
                    bne       FindVIRQ
                    puls      cc
                    comb
                    ldb       #E$Poll
                    rts

AddVIRQ             leay      -2,y
                    ldx       R$Y,u
                    stx       ,y
                    ldy       R$D,u
                    sty       ,x
                    bra       virqexit

RemVIRQ             ldx       ,y++
                    beq       virqexit
                    cmpx      R$Y,u
                    bne       RemVIRQ
                    bsr       DelVIRQ
virqexit            puls      cc
                    clrb
                    rts

DelVIRQ             pshs      x,y
DelVLup             ldx       ,y++
                    stx       -4,y
                    bne       DelVLup
                    puls      x,y
                    leay      -2,y
                    rts

********************************************************************
* F$Alarm - Dummy Alarm Call
********************************************************************
F.Alarm             clrb
                    rts

********************************************************************
* F$Time - Get Current System Time
********************************************************************
F.Time              ldx       #D.Time
RetTime             ldy       <D.Proc
                    ldb       P$Task,y
                    lda       <D.SysTsk
                    ldu       R$X,u
STime.Mv            ldy       #6
FMove               os9       F$Move
                    rts

********************************************************************
* F$STime - Set Current System Time
********************************************************************
F.STime             ldx       <D.Proc
                    lda       P$Task,x
                    ldx       R$X,u
                    ldu       #D.Time
                    ldb       <D.SysTsk
                    bsr       STime.Mv
                    lda       #TkPerSec
                    sta       <D.Tick
                    clrb
                    rts

********************************************************************
* Init - Clock Module Initialization
********************************************************************
Init                pshs      cc
                    orcc      #IntMasks

* Start CLOCK_AND_STOP periodic timer
                    lda       #CLOCK_AND_STOP.Value
                    sta       >CLOCK_AND_STOP.Base

* Initialize time slice and tick counts
                    ldb       #TkPerTS
                    stb       <D.TSlice
                    stb       <D.Slice
                    lda       #TkPerSec
                    sta       <D.Tick

* Install IRQ and VIRQ handlers
                    leax      SvcIRQ,pcr
                    stx       <D.IRQ
                    leax      SvcVIRQ,pcr
                    stx       <D.VIRQ

* Install service calls
                    leay      NewSvc,pcr
                    os9       F$SSvc

                    puls      cc
                    clrb
                    rts

                    emod
len                 equ       *
                    end
