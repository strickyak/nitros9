PORT ?= deep65280
CPU ?= 6809
MACHINE ?= deep65280v2
LEVEL = 2

include ../rules.mak
-include recipe.mak

DEEP_256K ?= 1
ifeq ($(DEEP_256K),1)
AFLAGS += -I. -I$(L2PD) -I$(L2PMD) -I$(L2MD)/kernel -I$(L1MD)/kernel -I$(L2MD) -I$(L1MD) -Ddeep65280=1 -DDEEP_256K=1
else
AFLAGS += -I. -I$(L2PD) -I$(L2PMD) -I$(L2MD)/kernel -I$(L1MD)/kernel -I$(L2MD) -I$(L1MD) -Ddeep65280=1
endif

MODDIR = .mods

KERNEL = krn krnp2
CONFIG = init
MANAGERS = ioman rbf scf
DRIVERS = sc6850 emudsk clock
DESCRIPTORS = term dd
CMDS = sysgo shell_21 mfree free procs mdir dir setime date stop

ALL_MODS = $(addprefix $(MODDIR)/, $(KERNEL) $(CONFIG) $(MANAGERS) $(DRIVERS) $(DESCRIPTORS) $(CMDS))

IMG = deep65280.img
DSK = deep0.dsk

LEVEL2_CMDS = asm attr backup bawk binex build calldbg cmp copy cputype date \
	dcheck debug ded deiniz del deldir devs dir dir_cb dirsort disasm display \
	dmem dmode dsave dump echo edit error exbin format format_d64 free go51 \
	help ident iniz irqs keyrpt link list load login makdir \
	mdir merge mfree minted mmap modpatch more mpi ngu padrom park pmap printerr \
	proc procs prompt pwd pxd rename save setime shell shell_21 shellplus sleep \
	smap stop tee tmode touch tsmon tuneport type unlink verify xmode

all: $(IMG) $(DSK)

$(IMG): $(ALL_MODS) build_img.py
	python3 build_img.py $@

$(DSK): $(addprefix $(MODDIR)/, $(LEVEL2_CMDS)) build_dsk.sh
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
