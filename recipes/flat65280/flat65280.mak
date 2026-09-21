PORT ?= flat65280
CPU ?= 6809
MACHINE ?= flat65280v2
LEVEL = 1

include ../rules.mak
-include recipe.mak

AFLAGS += -I. -I$(L1PD) -I$(L1PMD) -I$(L1MD)/kernel -I$(L1MD) -DFLAT65280=1

MODDIR = .mods

KERNEL = krn krnp2
CONFIG = init
MANAGERS = ioman rbf scf
DRIVERS = sc6850 emudsk clock
DESCRIPTORS = term dd
CMDS = sysgo shell_21 mfree free procs mdir dir setime date stop

ALL_MODS = $(addprefix $(MODDIR)/, $(KERNEL) $(CONFIG) $(MANAGERS) $(DRIVERS) $(DESCRIPTORS) $(CMDS))

IMG = flat65280.img
DSK = flat0.dsk

LEVEL1_CMDS = asm attr backup bawk binex build calldbg cmp config copy cputype date \
	dcheck debug ded deiniz del deldir devs dir dir_cb dirsort disasm display \
	dmode dsave dump echo edit error exbin format format_d64 free go51 \
	grfdrv help ident iniz irqs keyrpt link list load login makdir \
	mdir merge mfree minted more mpi ngu padrom park printerr \
	procs prompt pwd pxd rename save setime shell shell_21 shellplus sleep \
	stop tee tmode touch tsmon tuneport type unlink verify xmode

all: $(IMG) $(DSK)

$(IMG): $(ALL_MODS) build_img.py
	python3 build_img.py $@

$(DSK): $(addprefix $(MODDIR)/, $(LEVEL1_CMDS)) build_dsk.sh
	./build_dsk.sh $@

$(MODDIR)/term: $(L1MD)/term_sc6850.asm | $(MODDIR)
	$(AS) $(AFLAGS) $< $(ASOUT)$@

$(MODDIR)/dd: $(L1MD)/emudskdesc.asm | $(MODDIR)
	$(AS) $(AFLAGS) -DDD=1 -DDNum=0 $< $(ASOUT)$@

$(MODDIR)/sysgo: $(L1MD)/sysgo.asm | $(MODDIR)
	$(AS) $(AFLAGS) -DDD=1 $< $(ASOUT)$@

$(MODDIR)/pwd: pd.asm | $(MODDIR)
	$(AS) $(AFLAGS) $< $(ASOUT)$@ -DPWD=1

$(MODDIR)/pxd: pd.asm | $(MODDIR)
	$(AS) $(AFLAGS) $< $(ASOUT)$@ -DPXD=1

$(MODDIR)/tmode: xmode.asm | $(MODDIR)
	$(AS) $(AFLAGS) $< $(ASOUT)$@ -DTMODE=1

$(MODDIR)/xmode: xmode.asm | $(MODDIR)
	$(AS) $(AFLAGS) $< $(ASOUT)$@ -DXMODE=1

$(MODDIR)/shell: $(MODDIR)/shell_21
	cp $< $@

$(MODDIR)/type: $(MODDIR)/list
	cp $< $@

clean:
	$(RM) -r $(MODDIR) $(IMG) $(DSK) *.list *.map
