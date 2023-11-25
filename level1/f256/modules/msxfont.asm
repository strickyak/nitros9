********************************************************************
* font - F256 font
*
* $Id$
*
* Edt/Rev  YYYY/MM/DD  Modified by
* Comment
* ------------------------------------------------------------------
*   1      2023/09/24  Boisy G. Pitre
* Created.
*
               nam       font
               ttl       F256 font

               use       defsfile

tylg           set       Data
atrv           set       ReEnt+rev
rev            set       $01

               mod       eom,name,tylg,atrv,start,0

name           fcs       /font/

start


L0000    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0008    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0010    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0018    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0020    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0028    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0030    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0038    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0040    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0048    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0050    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0058    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0060    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0068    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0070    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0078    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0080    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0088    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0090    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0098    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L00A0    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L00A8    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L00B0    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L00B8    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L00C0    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L00C8    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L00D0    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L00D8    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L00E0    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L00E8    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L00F0    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L00F8    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0100    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0108    fcb   $10,$10,$10,$10,$10,$00,$10,$00   ........
L0110    fcb   $28,$28,$28,$00,$00,$00,$00,$00   (((.....
L0118    fcb   $28,$28,$7C,$28,$7C,$28,$28,$00   ((|(|((.
L0120    fcb   $10,$3C,$50,$38,$14,$78,$10,$00   .<P8.x..
L0128    fcb   $60,$64,$08,$10,$20,$4C,$0C,$00   `d.. L..
L0130    fcb   $20,$50,$50,$20,$54,$48,$34,$00    PP TH4.
L0138    fcb   $08,$10,$20,$00,$00,$00,$00,$00   .. .....
L0140    fcb   $10,$20,$40,$40,$40,$20,$10,$00   . @@@ ..
L0148    fcb   $10,$08,$04,$04,$04,$08,$10,$00   ........
L0150    fcb   $10,$54,$38,$10,$38,$54,$10,$00   .T8.8T..
L0158    fcb   $00,$10,$10,$7C,$10,$10,$00,$00   ...|....
L0160    fcb   $00,$00,$00,$00,$10,$10,$20,$00   ...... .
L0168    fcb   $00,$00,$00,$7C,$00,$00,$00,$00   ...|....
L0170    fcb   $00,$00,$00,$00,$00,$18,$18,$00   ........
L0178    fcb   $00,$00,$04,$08,$10,$20,$40,$00   ..... @.
L0180    fcb   $38,$44,$44,$54,$44,$44,$38,$00   8DDTDD8.
L0188    fcb   $10,$30,$50,$10,$10,$10,$7C,$00   .0P...|.
L0190    fcb   $38,$44,$04,$08,$30,$40,$7C,$00   8D..0@|.
L0198    fcb   $38,$44,$04,$18,$04,$44,$38,$00   8D...D8.
L01A0    fcb   $08,$18,$28,$48,$7C,$08,$08,$00   ..(H|...
L01A8    fcb   $7C,$40,$70,$08,$04,$08,$70,$00   |@p...p.
L01B0    fcb   $18,$20,$40,$78,$44,$44,$38,$00   . @xDD8.
L01B8    fcb   $7C,$44,$08,$10,$10,$10,$10,$00   |D......
L01C0    fcb   $38,$44,$44,$38,$44,$44,$38,$00   8DD8DD8.
L01C8    fcb   $38,$44,$44,$3C,$04,$08,$30,$00   8DD<..0.
L01D0    fcb   $00,$00,$10,$00,$00,$10,$00,$00   ........
L01D8    fcb   $00,$00,$10,$00,$00,$10,$20,$00   ...... .
L01E0    fcb   $0C,$18,$30,$60,$30,$18,$0C,$00   ..0`0...
L01E8    fcb   $00,$00,$7C,$00,$00,$7C,$00,$00   ..|..|..
L01F0    fcb   $60,$30,$18,$0C,$18,$30,$60,$00   `0...0`.
L01F8    fcb   $38,$44,$04,$08,$10,$00,$10,$00   8D......
L0200    fcb   $38,$44,$04,$34,$54,$54,$38,$00   8D.4TT8.
L0208    fcb   $10,$28,$44,$44,$7C,$44,$44,$00   .(DD|DD.
L0210    fcb   $78,$24,$24,$38,$24,$24,$78,$00   x$$8$$x.
L0218    fcb   $18,$24,$40,$40,$40,$24,$18,$00   .$@@@$..
L0220    fcb   $70,$28,$24,$24,$24,$28,$70,$00   p($$$(p.
L0228    fcb   $7C,$40,$40,$78,$40,$40,$7C,$00   |@@x@@|.
L0230    fcb   $7C,$40,$40,$78,$40,$40,$40,$00   |@@x@@@.
L0238    fcb   $38,$44,$40,$5C,$44,$44,$38,$00   8D@\DD8.
L0240    fcb   $44,$44,$44,$7C,$44,$44,$44,$00   DDD|DDD.
L0248    fcb   $38,$10,$10,$10,$10,$10,$38,$00   8.....8.
L0250    fcb   $1C,$08,$08,$08,$48,$48,$30,$00   ....HH0.
L0258    fcb   $44,$48,$50,$60,$50,$48,$44,$00   DHP`PHD.
L0260    fcb   $40,$40,$40,$40,$40,$40,$7C,$00   @@@@@@|.
L0268    fcb   $44,$6C,$54,$54,$44,$44,$44,$00   DlTTDDD.
L0270    fcb   $44,$44,$64,$54,$4C,$44,$44,$00   DDdTLDD.
L0278    fcb   $38,$44,$44,$44,$44,$44,$38,$00   8DDDDD8.
L0280    fcb   $78,$44,$44,$78,$40,$40,$40,$00   xDDx@@@.
L0288    fcb   $38,$44,$44,$44,$54,$48,$34,$00   8DDDTH4.
L0290    fcb   $78,$44,$44,$78,$50,$48,$44,$00   xDDxPHD.
L0298    fcb   $38,$44,$40,$38,$04,$44,$38,$00   8D@8.D8.
L02A0    fcb   $7C,$10,$10,$10,$10,$10,$10,$00   |.......
L02A8    fcb   $44,$44,$44,$44,$44,$44,$38,$00   DDDDDD8.
L02B0    fcb   $44,$44,$44,$44,$44,$28,$10,$00   DDDDD(..
L02B8    fcb   $44,$44,$44,$54,$54,$6C,$44,$00   DDDTTlD.
L02C0    fcb   $44,$44,$28,$10,$28,$44,$44,$00   DD(.(DD.
L02C8    fcb   $44,$44,$44,$38,$10,$10,$10,$00   DDD8....
L02D0    fcb   $7C,$04,$08,$10,$20,$40,$7C,$00   |... @|.
L02D8    fcb   $3C,$20,$20,$20,$20,$20,$3C,$00   <     <.
L02E0    fcb   $00,$40,$20,$10,$08,$04,$00,$00   .@ .....
L02E8    fcb   $3C,$04,$04,$04,$04,$04,$3C,$00   <.....<.
L02F0    fcb   $10,$28,$44,$00,$00,$00,$00,$00   .(D.....
L02F8    fcb   $00,$00,$00,$00,$00,$00,$7C,$00   ......|.
L0300    fcb   $20,$10,$08,$00,$00,$00,$00,$00    .......
L0308    fcb   $00,$00,$38,$04,$3C,$44,$3C,$00   ..8.<D<.
L0310    fcb   $40,$40,$58,$64,$44,$64,$58,$00   @@XdDdX.
L0318    fcb   $00,$00,$38,$44,$40,$44,$38,$00   ..8D@D8.
L0320    fcb   $04,$04,$34,$4C,$44,$4C,$34,$00   ..4LDL4.
L0328    fcb   $00,$00,$38,$44,$7C,$40,$38,$00   ..8D|@8.
L0330    fcb   $18,$24,$20,$78,$20,$20,$20,$00   .$ x   .
L0338    fcb   $00,$00,$38,$44,$44,$3C,$04,$38   ..8DD<.8
L0340    fcb   $40,$40,$78,$44,$44,$44,$44,$00   @@xDDDD.
L0348    fcb   $00,$10,$00,$30,$10,$10,$38,$00   ...0..8.
L0350    fcb   $00,$08,$00,$18,$08,$08,$48,$30   ......H0
L0358    fcb   $40,$40,$48,$50,$60,$50,$48,$00   @@HP`PH.
L0360    fcb   $30,$10,$10,$10,$10,$10,$38,$00   0.....8.
L0368    fcb   $00,$00,$68,$54,$54,$54,$54,$00   ..hTTTT.
L0370    fcb   $00,$00,$58,$64,$44,$44,$44,$00   ..XdDDD.
L0378    fcb   $00,$00,$38,$44,$44,$44,$38,$00   ..8DDD8.
L0380    fcb   $00,$00,$58,$64,$64,$58,$40,$40   ..XddX@@
L0388    fcb   $00,$00,$34,$4C,$4C,$34,$04,$04   ..4LL4..
L0390    fcb   $00,$00,$58,$64,$40,$40,$40,$00   ..Xd@@@.
L0398    fcb   $00,$00,$3C,$40,$38,$04,$78,$00   ..<@8.x.
L03A0    fcb   $20,$20,$78,$20,$20,$24,$18,$00     x  $..
L03A8    fcb   $00,$00,$48,$48,$48,$48,$34,$00   ..HHHH4.
L03B0    fcb   $00,$00,$44,$44,$44,$28,$10,$00   ..DDD(..
L03B8    fcb   $00,$00,$44,$44,$54,$54,$28,$00   ..DDTT(.
L03C0    fcb   $00,$00,$44,$28,$10,$28,$44,$00   ..D(.(D.
L03C8    fcb   $00,$00,$44,$44,$4C,$34,$04,$38   ..DDL4.8
L03D0    fcb   $00,$00,$7C,$08,$10,$20,$7C,$00   ..|.. |.
L03D8    fcb   $0C,$10,$10,$20,$10,$10,$0C,$00   ... ....
L03E0    fcb   $10,$10,$10,$00,$10,$10,$10,$00   ........
L03E8    fcb   $30,$08,$08,$04,$08,$08,$30,$00   0.....0.
L03F0    fcb   $20,$54,$08,$00,$00,$00,$00,$00    T......
L03F8    fcb   $7C,$7C,$7C,$7C,$7C,$7C,$7C,$00   |||||||.
L0400    fcb   $10,$38,$7C,$FE,$FE,$38,$7C,$00   .8|..8|.
L0408    fcb   $00,$6C,$FE,$FE,$7C,$38,$10,$00   .l..|8..
L0410    fcb   $38,$38,$FE,$FE,$54,$10,$7C,$00   88..T.|.
L0418    fcb   $10,$38,$7C,$FE,$7C,$38,$10,$00   .8|.|8..
L0420    fcb   $7C,$82,$82,$82,$82,$82,$7C,$00   |.....|.
L0428    fcb   $7C,$FE,$FE,$FE,$FE,$FE,$7C,$00   |.....|.
L0430    fcb   $10,$78,$26,$38,$54,$20,$1E,$00   .x&8T ..
L0438    fcb   $00,$10,$3C,$10,$3C,$5A,$32,$00   ..<.<Z2.
L0440    fcb   $00,$00,$48,$44,$44,$44,$20,$00   ..HDDD .
L0448    fcb   $00,$38,$00,$38,$44,$04,$18,$00   .8.8D...
L0450    fcb   $00,$38,$00,$78,$10,$30,$4C,$00   .8.x.0L.
L0458    fcb   $00,$10,$7C,$12,$3C,$52,$34,$00   ..|.<R4.
L0460    fcb   $00,$48,$2C,$32,$54,$10,$08,$00   .H,2T...
L0468    fcb   $00,$08,$5C,$6A,$4A,$0C,$10,$00   ..\jJ...
L0470    fcb   $00,$08,$0E,$08,$38,$4C,$3A,$00   ....8L:.
L0478    fcb   $00,$00,$00,$3C,$02,$02,$0C,$00   ...<....
L0480    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0488    fcb   $20,$7C,$20,$7C,$AA,$92,$64,$00    | |*.d.
L0490    fcb   $00,$44,$42,$42,$42,$40,$20,$00   .DBBB@ .
L0498    fcb   $38,$00,$38,$44,$04,$08,$30,$00   8.8D..0.
L04A0    fcb   $38,$00,$7C,$08,$10,$30,$4E,$00   8.|..0N.
L04A8    fcb   $12,$7D,$10,$3E,$51,$51,$22,$00   .}.>QQ".
L04B0    fcb   $20,$22,$79,$25,$24,$44,$18,$00    "y%$D..
L04B8    fcb   $10,$7E,$08,$7E,$04,$40,$3C,$00   .~.~.@<.
L04C0    fcb   $08,$10,$20,$40,$20,$10,$08,$00   .. @ ...
L04C8    fcb   $04,$44,$5E,$44,$44,$44,$28,$00   .D^DDD(.
L04D0    fcb   $3C,$02,$00,$00,$00,$40,$3E,$00   <....@>.
L04D8    fcb   $10,$7E,$08,$04,$04,$80,$78,$00   .~....x.
L04E0    fcb   $80,$80,$80,$80,$84,$88,$70,$00   ......p.
L04E8    fcb   $08,$FE,$38,$48,$38,$08,$10,$00   ..8H8...
L04F0    fcb   $44,$44,$FE,$44,$48,$40,$3C,$00   DD.DH@<.
L04F8    fcb   $44,$28,$FE,$20,$40,$40,$3C,$00   D(. @@<.
L0500    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L0508    fcb   $00,$20,$50,$50,$20,$00,$00,$00   . PP ...
L0510    fcb   $38,$20,$20,$20,$00,$00,$00,$00   8   ....
L0518    fcb   $00,$00,$00,$08,$08,$08,$38,$00   ......8.
L0520    fcb   $00,$00,$00,$00,$20,$10,$08,$00   .... ...
L0528    fcb   $00,$00,$00,$18,$18,$00,$00,$00   ........
L0530    fcb   $7C,$04,$7C,$04,$08,$10,$20,$00   |.|... .
L0538    fcb   $00,$00,$78,$08,$30,$20,$40,$00   ..x.0 @.
L0540    fcb   $00,$00,$08,$10,$30,$50,$10,$00   ....0P..
L0548    fcb   $00,$10,$78,$48,$08,$10,$20,$00   ..xH.. .
L0550    fcb   $00,$00,$78,$10,$10,$10,$78,$00   ..x...x.
L0558    fcb   $00,$10,$78,$30,$50,$50,$10,$00   ..x0PP..
L0560    fcb   $00,$20,$7C,$24,$28,$20,$20,$00   . |$(  .
L0568    fcb   $00,$00,$38,$08,$08,$08,$7C,$00   ..8...|.
L0570    fcb   $00,$00,$7C,$04,$7C,$04,$7C,$00   ..|.|.|.
L0578    fcb   $00,$00,$54,$54,$04,$08,$10,$00   ..TT....
L0580    fcb   $00,$00,$00,$80,$7C,$00,$00,$00   ....|...
L0588    fcb   $7C,$04,$14,$18,$10,$10,$20,$00   |..... .
L0590    fcb   $04,$08,$10,$30,$50,$10,$10,$00   ...0P...
L0598    fcb   $10,$7C,$44,$04,$04,$08,$10,$00   .|D.....
L05A0    fcb   $7C,$10,$10,$10,$10,$10,$7C,$00   |.....|.
L05A8    fcb   $08,$7C,$08,$18,$28,$48,$08,$00   .|..(H..
L05B0    fcb   $10,$7C,$14,$14,$14,$24,$44,$00   .|...$D.
L05B8    fcb   $10,$7C,$10,$7C,$10,$10,$10,$00   .|.|....
L05C0    fcb   $3C,$24,$44,$04,$04,$08,$10,$00   <$D.....
L05C8    fcb   $20,$3C,$28,$48,$08,$08,$10,$00    <(H....
L05D0    fcb   $7C,$04,$04,$04,$04,$04,$7C,$00   |.....|.
L05D8    fcb   $28,$7C,$28,$28,$08,$08,$10,$00   (|((....
L05E0    fcb   $00,$60,$04,$64,$04,$08,$70,$00   .`.d..p.
L05E8    fcb   $00,$7C,$04,$08,$10,$28,$44,$00   .|...(D.
L05F0    fcb   $20,$7C,$24,$28,$20,$20,$1C,$00    |$(  ..
L05F8    fcb   $44,$44,$24,$04,$08,$10,$20,$00   DD$... .
L0600    fcb   $3C,$24,$3C,$44,$04,$08,$10,$00   <$<D....
L0608    fcb   $08,$70,$10,$7C,$10,$10,$20,$00   .p.|.. .
L0610    fcb   $54,$54,$54,$04,$04,$08,$10,$00   TTT.....
L0618    fcb   $38,$00,$7C,$10,$10,$10,$20,$00   8.|... .
L0620    fcb   $40,$40,$60,$50,$48,$40,$40,$00   @@`PH@@.
L0628    fcb   $10,$7C,$10,$10,$10,$10,$20,$00   .|.... .
L0630    fcb   $00,$38,$00,$00,$00,$00,$7C,$00   .8....|.
L0638    fcb   $00,$7C,$04,$68,$10,$28,$44,$00   .|.h.(D.
L0640    fcb   $10,$7C,$04,$18,$74,$10,$10,$00   .|..t...
L0648    fcb   $04,$04,$04,$08,$10,$20,$40,$00   ..... @.
L0650    fcb   $10,$08,$24,$24,$24,$24,$44,$00   ..$$$$D.
L0658    fcb   $40,$40,$7C,$40,$40,$40,$3C,$00   @@|@@@<.
L0660    fcb   $7C,$04,$04,$04,$08,$10,$20,$00   |..... .
L0668    fcb   $00,$20,$50,$08,$04,$04,$00,$00   . P.....
L0670    fcb   $10,$7C,$10,$10,$54,$54,$10,$00   .|..TT..
L0678    fcb   $00,$7C,$04,$04,$28,$10,$08,$00   .|..(...
L0680    fcb   $78,$00,$30,$00,$00,$78,$04,$00   x.0..x..
L0688    fcb   $08,$10,$20,$40,$48,$44,$7C,$00   .. @HD|.
L0690    fcb   $04,$04,$04,$28,$10,$28,$40,$00   ...(.(@.
L0698    fcb   $3C,$10,$7C,$10,$10,$10,$0C,$00   <.|.....
L06A0    fcb   $20,$7C,$24,$24,$28,$20,$20,$00    |$$(  .
L06A8    fcb   $00,$38,$08,$08,$08,$08,$7C,$00   .8....|.
L06B0    fcb   $00,$7C,$04,$7C,$04,$04,$7C,$00   .|.|..|.
L06B8    fcb   $38,$00,$7C,$04,$04,$08,$10,$00   8.|.....
L06C0    fcb   $48,$48,$48,$48,$48,$10,$20,$00   HHHHH. .
L06C8    fcb   $00,$28,$28,$28,$28,$2C,$48,$00   .((((,H.
L06D0    fcb   $40,$40,$40,$48,$48,$50,$60,$00   @@@HHP`.
L06D8    fcb   $00,$7C,$44,$44,$44,$44,$7C,$00   .|DDDD|.
L06E0    fcb   $7C,$44,$44,$04,$04,$08,$10,$00   |DD.....
L06E8    fcb   $00,$60,$00,$04,$04,$08,$70,$00   .`....p.
L06F0    fcb   $48,$24,$00,$00,$00,$00,$00,$00   H$......
L06F8    fcb   $30,$48,$30,$00,$00,$00,$00,$00   0H0.....
L0700    fcb   $20,$F8,$20,$4E,$40,$90,$8E,$00    x N@...
L0708    fcb   $10,$FE,$20,$78,$04,$04,$78,$00   .. x..x.
L0710    fcb   $00,$FC,$02,$02,$02,$04,$18,$00   ........
L0718    fcb   $FE,$08,$10,$20,$20,$20,$1C,$00   ...   ..
L0720    fcb   $10,$12,$1C,$30,$40,$40,$3E,$00   ...0@@>.
L0728    fcb   $2C,$F2,$44,$44,$9C,$26,$1C,$00   ,rDD.&..
L0730    fcb   $00,$9E,$80,$80,$80,$90,$4E,$00   ......N.
L0738    fcb   $48,$48,$7C,$D2,$B6,$AA,$4C,$00   HH|R6*L.
L0740    fcb   $40,$4C,$D2,$62,$4E,$D2,$4E,$00   @LRbNRN.
L0748    fcb   $00,$38,$54,$92,$A2,$A2,$44,$00   .8T.""D.
L0750    fcb   $04,$9E,$84,$84,$8C,$96,$4C,$00   ......L.
L0758    fcb   $10,$E4,$26,$44,$44,$48,$30,$00   .d&DDH0.
L0760    fcb   $20,$10,$00,$20,$14,$52,$B2,$00    .. .R2.
L0768    fcb   $00,$00,$20,$50,$88,$04,$02,$00   .. P....
L0770    fcb   $1E,$84,$9E,$84,$8C,$96,$4C,$00   ......L.
L0778    fcb   $10,$FC,$10,$FC,$70,$98,$74,$00   ....p.t.
L0780    fcb   $70,$10,$14,$7E,$A4,$A4,$48,$00   p..~$$H.
L0788    fcb   $20,$F4,$22,$60,$A2,$62,$1C,$00    t"`"b..
L0790    fcb   $48,$48,$7C,$AA,$92,$A2,$44,$00   HH|*."D.
L0798    fcb   $10,$7C,$10,$7C,$10,$12,$0C,$00   .|.|....
L07A0    fcb   $48,$5C,$6A,$E2,$24,$10,$10,$00   H\jb$...
L07A8    fcb   $10,$9C,$B2,$D2,$92,$1C,$20,$00   ..2R.. .
L07B0    fcb   $10,$1C,$10,$10,$78,$94,$70,$00   ....x.p.
L07B8    fcb   $60,$10,$80,$B8,$C4,$84,$38,$00   `..8D.8.
L07C0    fcb   $04,$82,$82,$82,$42,$04,$18,$00   ....B...
L07C8    fcb   $3C,$08,$1C,$22,$5A,$26,$1C,$00   <.."Z&..
L07D0    fcb   $20,$2C,$F4,$24,$64,$A4,$26,$00    ,t$d$&.
L07D8    fcb   $3C,$08,$10,$3C,$42,$02,$1C,$00   <..<B...
L07E0    fcb   $40,$40,$DC,$62,$42,$C2,$44,$00   @@\bBBD.
L07E8    fcb   $10,$10,$20,$20,$60,$52,$8C,$00   ..  `R..
L07F0    fcb   $00,$00,$00,$00,$00,$00,$00,$00   ........
L07F8    fcb   $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ........

               emod
eom            equ       *
               end
