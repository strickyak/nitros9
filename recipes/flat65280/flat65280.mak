PORT ?= flat65280
CPU ?= 6809
MACHINE ?= flat65280v2
LEVEL = 1

include ../rules.mak
-include recipe.mak

AFLAGS += -I. -I$(L1PD) -I$(L1PMD) -I$(L1PD)/defs -I$(L1MD)/kernel -I$(L1MD) -DFLAT65280=1

MODDIR = .mods

KERNEL = krn krnp2
CONFIG = init
MANAGERS = ioman rbf scf
DRIVERS = sc6850 emudsk
DESCRIPTORS = term dd
CMDS = shell_21 mfree free procs mdir dir

ALL_MODS = $(addprefix $(MODDIR)/, $(KERNEL) $(CONFIG) $(MANAGERS) $(DRIVERS) $(DESCRIPTORS) $(CMDS))

all: $(ALL_MODS)

$(MODDIR)/term: $(L1MD)/term_sc6850.asm | $(MODDIR)
	$(AS) $(AFLAGS) $< $(ASOUT)$@

$(MODDIR)/dd: $(L1MD)/emudskdesc.asm | $(MODDIR)
	$(AS) $(AFLAGS) -DDD=1 -DDNum=0 $< $(ASOUT)$@

clean:
	$(RM) -r $(MODDIR)
