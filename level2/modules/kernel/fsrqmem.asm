**************************************************
* System Call: F$SRqMem
*
* Function: Request memory
*
* Input:  D = Byte count
*
* Output: U = Address of allocated memory area
*
* Error:  CC = C bit set; B = error code
*
* It also updates 8K DAT blocks-if it finds an empty block, it re-does the 32
* entries in the SMAP table to indicate that they are free
*
FSRqMem  ldd   R$D,u        get size requested
         addd  #$00FF       round it up to nearest 256 byte page
         clrb               Just keep # of pages (and start 8K block #)
         std   R$D,u        save rounded version back to user
         ldy   <D.SysMem    Get ptr to SMAP table
         leay  $ED,y      

*         leay  $20,y        Skip Block 0 (always reserved for system)
* Change to pshs a,b:use 1,s for block # to check, and ,s for TFM spot
*         incb               Skip block 0 (always reserved for system)
         pshs  d            Reserve a byte & put 0 byte on stack

* This loop updates the SMAP table if anything can be marked as unused
*L082F    ldx   <D.SysDAT    get pointer to system DAT block list
*         lslb               adjust block offset for 2 bytes/entry
*         ldd   b,x          get block type/# from system DAT
*         cmpd  #DAT.Free    Unused block?
*         beq   L0847        yes, mark it free in SMAP table
*         ldx   <D.BlkMap    No, get ptr to MMAP table
*         lda   d,x          Get block marker for 2 meg mem map
*         cmpa  #RAMinUse    Is it in use (not free, ROM or used by module)?
*         bne   L0848        No, mark it as type it is in SMAP table
*         leay  $20,y        Yes, move to next block in pages
*         bra   L084F        move to next block & try again

*L0847    clra               Byte to fill system page map with (0=Not in use)
*L0848    sta   ,s           Put it on stack
*         ldw   #$0020       Get size of 8K block in pages
*         tfm   s,y+         Mark entire block's worth of pages with A
*L084F    inc   1,s          Bump up to next block to check
*         ldb   1,s          Get it
*         cmpb  #8           Done whole 64k system space?
*         blo   L082F        no, keep checking
* Now we can actually attempt to allocate the system RAM requested
* NOTE: Opt for Coco/TC9 OS9 ONLY: skip last 17 pages with leay -17,y since
* they are: Kernal (REL/BOOT/OS9P1 - 15 pages), vector RAM & I/O (2 pages)
* (Already permanently marked @ L01D2)
* At the start, Y is pointing to the end of the SMAP table+1
         ldx   <D.SysMem    Get start of table ptr
         ldb   #$20         skip block 0: it's always full
         abx                same size, but faster than leax $20,x
*         leay  -17,y        Skip Kernal, Vector RAM & I/O (Can't be free)
L0857    ldb   R$A,u        Get # 256 byte pages requested
* Loop (from end of system mem map) to look for # continuous pages requested
L0859    equ   *
         IFNE  H6309
* TODO: Verify order of comparison
         cmpr  x,y          We still have any system RAM left to try?
         ELSE
         pshs  y
         cmpx  ,s++
         ENDC
         bhi   L0863        Yes, continue
         comb               Exit with No System RAM Error
         ldb   #E$NoRam
         bra   L0894        Eat stack & exit

L0863    lda   ,-y          Get page marker (starting @ end of SMAP)
         bne   L0857        Used, try next lower page
         decb               Found 1 page, dec # pages we need to allocate
         bne   L0859        Still more pages needed, check if we can get more
         sty   ,s           Found free contigous pages, save SMAP entry ptr
         lda   1,s          Get LSB of ptr
         lsra               Divide by 32 (Calculate start 8K block #)
         lsra  
         lsra  
         lsra  
         lsra  
         ldb   1,s          Get LSB of ptr again
         andb  #%00011111   Keep only within 8K block offset
         addb  R$A,u        Add # pages requested
         addb  #$1F         Round up to nearest 8K block
         lsrb               Divide by 32 (Calculate end 8K block #)
         lsrb  
         lsrb  
         lsrb  
         lsrb
         ldx   <D.SysPrc    Get ptr to system proc. dsc.
         lbsr  L09BE        Allocate an image with our start/end block #'s
         bcs   L0894        Couldn't, exit with error
         ldb   R$A,u        Get # pages requested
         lda   #RAMinUse    Get SMAP in use flag
L088A    sta   ,y+          Mark all the pages requested as In Use
         decb
         bne   L088A
         lda   1,s          Get MSB of ptr to start of newly allocated Sys RAM
         std   R$U,u        Save for caller
         clrb               No error
L0894    puls  u,pc         Eat stack (U is changed after it exits) & return


**************************************************
* System Call: F$SRtMem
*
* Function: Return memory
*
* Input:  U = Address of memory to return
*         D = Number of bytes to return
*
* Output: None
*
* Error:  CC = C bit set; B = error code
*
FSRtMem  ldd   R$D,u        get # pages to free up
         beq   L08F2        nothing to free, return without error
         addd  #$00FF       round it up to nearest page
         ldb   R$U+1,u      get LSB of address
         beq   L08A6        it's a even page, skip ahead
         comb               set carry
         ldb   #E$BPAddr    get error code
         rts                return

L08A6    ldb   R$U,u        get MSB of page address
         beq   L08F2        not a legal page, return without error
         ldx   <D.SysMem    get pointer to system memory map
         abx                set pointer into map
L08AD    equ   *
         IFNE  H6309
         aim   #^RAMinUse,,x+
         ELSE
         ldb   ,x
         andb  #^RAMinUse
         stb   ,x+
         ENDC
         deca  
         bne   L08AD
* Scan DAT image to find memory blocks to free up
         ldx   <D.SysDAT    get pointer to system DAT image
         IFNE  H6309
         lde   #8           get # blocks to check
         ELSE
         ldy   #DAT.BlCt
         ENDC
L08BC    ldd   ,x           get block image
         cmpd  #DAT.Free    is it already free?
         beq   L08EC        yes, skip to next one
         ldu   <D.BlkMap    get pointer to MMU block map
         lda   d,u          get allocation flag for this block: 16-bit offset
         cmpa  #RAMinUse    being used?
         bne   L08EC        no, move to next block
         tfr   x,d
         subd  <D.SysDAT
         lslb  
         lslb  
         lslb  
         lslb  
         ldu   <D.SysMem    get pointer to system map
         IFNE   H6309
         addr   d,u
* Check if we can remove the entire memory block from system map
         ldf   #16          get # pages per block/2
L08DA    ldd   ,u++         Either of these 2 pages allocated?
         ELSE
         leau  d,u
         ldb   #32
L08DA    lda   ,u+          Either of these 2 pages allocated?
         ENDC
         bne   L08EC        yes, can't free block, skip to next one
         IFNE  H6309
         decf               checked all pages?
         ELSE
         decb
         ENDC
         bne   L08DA        no, keep looking
         ldd   ,x           get block # into B: could be >$80
         ldu   <D.BlkMap    point to allocation table
         IFNE  H6309
         sta   d,u          clear the block using 16-bit offset
         ELSE
         clr   d,u
         ENDC
         ldd   #DAT.Free    get free block marker
         std   ,x           save it into DAT image
L08EC    leax  2,x          move to next DAT block
         IFNE  H6309
         dece               done?
         ELSE
         leay  -1,y
         ENDC
         bne   L08BC        no, keep checking
L08F2    clrb               clear errors
L08F3    rts                return

* Optimize F$Boot for size, as it's only called once...
* F$Boot entry point
FBoot    lda   #'t        tried to boot
         jsr   <D.BtBug
         coma               Set boot flag
         lda   <D.Boot      we booted once before?
         bne   L08F3        Yes, return
         inc   <D.Boot      Set boot flag
         ldx   <D.Init      Get ptr to init module if it exists
         beq   L0908        it doesn't, point to boot name
         ldd   <BootStr,x   Get offset to text
         beq   L0908        Doesn't exist, get hard coded text
         leax   d,x         Adjust X to point to boot module
         bra   L090C        Try & link to module

boot     fcs   /Boot/

L0908    leax  <boot,pcr
* Link to module and execute
L090C    lda   #Systm+Objct
         os9   F$Link   
         bcs   L08F3
         lda   #'b        calling boot
         jsr   <D.BtBug
         jsr   ,y           load boot file
         bcs   L08F3
         std   <D.BtSz      save boot file size
         stx   <D.BtPtr     save start pointer of bootfile
         lda   #'b        boot returns OK
         jsr   <D.BtBug

* added for IOMan system memory extentions
         ldd   M$Name,x   grab the name offset
         ldd   d,x        find the first 2 bytes of the first module
         cmpd  #$4E69     'Ni' ? (NitrOS9 module?)
         bne   not.ext    no, not system memory extensions
         ldd   M$Exec,x   grab the execution ptr
         jmp   d,x        and go execute the system memory extension module

not.ext  ldd   <D.BtSz
         bsr   I.VBlock   internal verify block routine
         ldx   <D.SysDAT    get system DAT pointer
         ldb   $0D,x      get highest allocated block number
         incb             allocate block 0, too
         ldx   <D.BlkMap  point to the memory block map
         lbra  L01DF      and go mark the blocks as used.

FVBlock  ldd   R$D,u      size of block to verify
         ldx   R$X,u      start address to verify

I.VBlock leau  d,x          point to end of bootfile
         tfr   x,d
         anda  #$E0
         clrb  
         pshs  d,u
         lsra  
         lsra  
         lsra  
         lsra  
         ldy   <D.SysDAT    get pointer to system DAT
         leay  a,y          offset to bootfile
L092D    ldd   M$ID,x       get module ID
         cmpd  #M$ID12      legal ID?
         bne   L0954        no, keep looking
         ldd   M$Name,x   find name offset pointer
         pshs  x
         leax  d,x

name.prt lda   ,x+        get first character of the name
         jsr   <D.BtBug   print it out
         bpl   name.prt
         lda   #C$SPAC    a space
         jsr   <D.BtBug

         puls  x
         IFNE  H6309
         ldd   ,s         offset into block
         subr  d,x        make X=offset into block
         ELSE
         tfr   x,d
         subd  ,s
         tfr   d,x
         ENDC
         tfr   y,d
         os9   F$VModul 
         IFNE  H6309
         ldw   ,s
         leax  w,x
         ELSE
         pshs  b
         ldd   1,s
         leax  d,x
         puls  b
         ENDC
         bcc   L094E
         cmpb  #E$KwnMod
         bne   L0954
L094E    ldd   M$Size,x
         leax  d,x
         fcb   $8C        skip 2 bytes

L0954    leax  1,x          move to next byte
L0956    cmpx  2,s          gone thru whole bootfile?
         bcs   L092D        no, keep looking
         leas  4,s          purge stack
         clrb
         rts