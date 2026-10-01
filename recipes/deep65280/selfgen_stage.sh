#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NITROS9DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
OS9="${OS9:-os9}"

TARGET="${1:-/tmp/pc/disk0.dsk}"

echo "=================================================================="
echo "NitrOS-9 Level 2 Self-Generation Staging"
echo "Target disk: $TARGET"
echo "=================================================================="

mkdir -p "$(dirname "$TARGET")"

# 1. Format disk if it doesn't exist
if [ ! -f "$TARGET" ]; then
    echo "Formatting disk image: $TARGET ..."
    "$OS9" format -e -n'DEEP65280' -l'40000' "$TARGET"
fi

# 2. Create standard directory structure
echo "Creating directory structure (CMDS, DEFS, SRC, MODS, SYS)..."
for d in CMDS DEFS SRC MODS SYS; do
    "$OS9" makdir "$TARGET,$d" 2>/dev/null || true
done

# 3. Create unified DEFS/defsfile
echo "Generating unified DEFS/defsfile..."
TMP_DEFS="$(mktemp)"
cat <<'EOF' > "$TMP_DEFS"
* ====================================================================
* NitrOS-9 Level 2 Unified Definitions for Native Self-Generation
* ====================================================================
Level               set       2
DEEP_256K           set       1
NOS9VER             set       0
NOS9MAJ             set       0
NOS9MIN             set       0

* Platform conditional equates (treat undefined platform symbols as 0)
picothing           set       0
wildbits            set       0
mc09                set       0
TC9                 set       0
H6309               set       0
coco3               set       0
atari               set       0
corsham             set       0
FLAT65280           set       0
dalpha              set       0
ROM                 set       0
NOS9DEV             set       0
coco                set       0
DOHELP              set       0

EOF

cat "$NITROS9DIR/defs/os9.d" >> "$TMP_DEFS"
cat "$NITROS9DIR/defs/scf.d" >> "$TMP_DEFS"
cat "$NITROS9DIR/defs/rbf.d" >> "$TMP_DEFS"
cat "$NITROS9DIR/defs/deep65280.d" >> "$TMP_DEFS"

TMP_DEFS_P="$(mktemp)"
python3 "$SCRIPT_DIR/selfgen_preprocess.py" --no-collisions "$TMP_DEFS" "$TMP_DEFS_P"
"$OS9" copy -l -r "$TMP_DEFS_P" "$TARGET,DEFS/defsfile"
"$OS9" copy -l -r "$TMP_DEFS_P" "$TARGET,SRC/defsfile"

# Copy individual def files
for d in os9.d scf.d rbf.d cocovtio.d; do
    "$OS9" copy -l -r "$NITROS9DIR/defs/$d" "$TARGET,DEFS/$d"
    "$OS9" copy -l -r "$NITROS9DIR/defs/$d" "$TARGET,SRC/$d"
done

# 4. Generate wrappers in SRC
echo "Creating target wrappers in SRC..."
TMP_WRAP="$(mktemp -d)"

cat <<'EOF' > "$TMP_WRAP/dd.asm"
                    use       defsfile
DD                  equ       1
DNum                equ       0
                    use       emudskdesc.asm
EOF

cat <<'EOF' > "$TMP_WRAP/sysgo_dd.asm"
                    use       defsfile
DD                  equ       1
                    use       sysgo.asm
EOF

cat <<'EOF' > "$TMP_WRAP/pwd.asm"
                    use       defsfile
PWD                 equ       1
PXD                 equ       0
                    use       pd.asm
EOF

cat <<'EOF' > "$TMP_WRAP/pxd.asm"
                    use       defsfile
PWD                 equ       0
PXD                 equ       1
                    use       pd.asm
EOF

cat <<'EOF' > "$TMP_WRAP/tmode.asm"
                    use       defsfile
TMODE               equ       1
XMODE               equ       0
                    use       xmode.asm
EOF

cat <<'EOF' > "$TMP_WRAP/xmode_bld.asm"
                    use       defsfile
TMODE               equ       0
XMODE               equ       1
                    use       xmode.asm
EOF

for w in dd.asm sysgo_dd.asm pwd.asm pxd.asm tmode.asm xmode_bld.asm; do
    "$OS9" copy -l -r "$TMP_WRAP/$w" "$TARGET,SRC/$w"
done
rm -rf "$TMP_WRAP"

# 5. Preprocess and install all assembly sources
echo "Preprocessing and copying assembly sources to SRC..."
TMP_PREP="$(mktemp -d)"

# Helper sources for krnp2
KRNP2_HELPERS=(
    fcrcmod.asm funlink.asm ffork.asm fallprc.asm fchain.asm
    fexit.asm fmem.asm fsend.asm ficpt.asm fsleep.asm
    fallram.asm fsprior.asm fid.asm fdelram.asm fsswi.asm
    fstime.asm fallbit.asm fgprdsc.asm fgblkmp.asm fgmoddr.asm
    fsuser.asm funload.asm ffind64.asm fgprocp.asm fdelimg.asm
    fmapblk.asm fclrblk.asm fgcmdir.asm fdebug.asm
)

KRNP2_GROUP=("$NITROS9DIR/level2/modules/kernel/krnp2.asm")
for h in "${KRNP2_HELPERS[@]}"; do
    if [ -f "$NITROS9DIR/level2/modules/kernel/$h" ]; then
        KRNP2_GROUP+=("$NITROS9DIR/level2/modules/kernel/$h")
    else
        KRNP2_GROUP+=("$NITROS9DIR/level1/modules/kernel/$h")
    fi
done

# Helper sources for krn
KRN_HELPERS=(
    fssvc.asm flink.asm fvmodul.asm ffmodul.asm fprsnam.asm
    fcmpnam.asm fsrqmem.asm fdelram.asm fallimg.asm ffreehb.asm
    fdatlog.asm fld.asm fcpymem.asm fmove.asm fldabx.asm
    falltsk.asm faproc.asm fnproc.asm
)

KRN_GROUP=("$NITROS9DIR/level2/modules/kernel/krn.asm")
for h in "${KRN_HELPERS[@]}"; do
    if [ -f "$NITROS9DIR/level2/modules/kernel/$h" ]; then
        KRN_GROUP+=("$NITROS9DIR/level2/modules/kernel/$h")
    else
        KRN_GROUP+=("$NITROS9DIR/level1/modules/kernel/$h")
    fi
done

# Preprocess krnp2 group and krn group
echo "Preprocessing krnp2 group (${#KRNP2_GROUP[@]} files)..."
python3 "$SCRIPT_DIR/selfgen_preprocess.py" --group "$TMP_PREP" --defs "$TMP_DEFS_P" "${KRNP2_GROUP[@]}"

echo "Preprocessing krn group (${#KRN_GROUP[@]} files)..."
python3 "$SCRIPT_DIR/selfgen_preprocess.py" --group "$TMP_PREP" --defs "$TMP_DEFS_P" "${KRN_GROUP[@]}"

# Copy all preprocessed helpers and kernel sources to SRC
for f in "$TMP_PREP"/*; do
    "$OS9" copy -l -r "$f" "$TARGET,SRC/$(basename "$f")"
done

# Shared module sources
for s in level1/modules/emudskdesc.asm level1/modules/sysgo.asm level1/cmds/pd.asm level1/cmds/xmode.asm; do
    b="$(basename "$s")"
    python3 "$SCRIPT_DIR/selfgen_preprocess.py" --defs "$TMP_DEFS_P" "$NITROS9DIR/$s" "$TMP_PREP/$b"
    "$OS9" copy -l -r "$TMP_PREP/$b" "$TARGET,SRC/$b"
done

# Boot modules (excluding krnp2 and krn which are already staged above)
BOOT_SOURCES=(
    level1/cmds/dir.asm
    level1/cmds/setime.asm
    level1/cmds/date.asm
    level2/deep65280/cmds/stop.asm
    level1/modules/scf.asm
    level1/modules/sc6850.asm
    level2/deep65280/modules/clock.asm
    level1/modules/term_sc6850.asm
    level1/cmds/shell_21.asm
    level2/cmds/mfree.asm
    level1/cmds/free.asm
    level2/cmds/procs.asm
    level2/cmds/mdir.asm
    level1/modules/emudsk.asm
    level2/modules/rbf.asm
    level1/modules/ioman.asm
    level2/deep65280/modules/init.asm
)

for s in "${BOOT_SOURCES[@]}"; do
    b="$(basename "$s")"
    python3 "$SCRIPT_DIR/selfgen_preprocess.py" --defs "$TMP_DEFS_P" "$NITROS9DIR/$s" "$TMP_PREP/$b"
    "$OS9" copy -l -r "$TMP_PREP/$b" "$TARGET,SRC/$b"
done

# Level 2 commands
COMMANDS=(
    asm attr backup bawk binex build calldbg cmp copy cputype
    dcheck debug ded deiniz del deldir devs dir_cb dirsort disasm display
    dmem dmode dsave dump echo edit error exbin format format_d64 go51
    help ident iniz irqs keyrpt link list load login makdir
    merge minted mmap modpatch more mpi ngu padrom park pmap printerr
    proc prompt rename save shellplus sleep smap tee touch tsmon
    tuneport unlink verify
)

for c in "${COMMANDS[@]}"; do
    src=""
    for dir in level2/deep65280/cmds level2/cmds level1/cmds; do
        if [ -f "$NITROS9DIR/$dir/$c.asm" ]; then
            src="$NITROS9DIR/$dir/$c.asm"
            break
        fi
    done
    if [ -n "$src" ]; then
        python3 "$SCRIPT_DIR/selfgen_preprocess.py" --defs "$TMP_DEFS_P" "$src" "$TMP_PREP/$c.asm"
        "$OS9" copy -l -r "$TMP_PREP/$c.asm" "$TARGET,SRC/$c.asm"
    fi
done

rm -rf "$TMP_PREP"
rm -f "$TMP_DEFS" "$TMP_DEFS_P"

# 6. Install compiled tools & bootstrap commands into CMDS
echo "Installing tools and bootstrap commands to CMDS..."
installed_cmds=()
if [ -f "$SCRIPT_DIR/selfgen_img" ]; then
    "$OS9" copy -o=0 -r "$SCRIPT_DIR/selfgen_img" "$TARGET,CMDS/selfgen_img"
    installed_cmds+=("selfgen_img")
fi

NCL_SRC="/home/strick/modoc/coco-shelf/tfr9/v4/misc/ncl-2026-09/ncl"
if [ -f "$NCL_SRC" ]; then
    "$OS9" copy -o=0 -r "$NCL_SRC" "$TARGET,CMDS/ncl"
    installed_cmds+=("ncl")
fi

MOD_DIR="$SCRIPT_DIR/.mods"
if [ -d "$MOD_DIR" ]; then
    for f in "$MOD_DIR"/*; do
        if [ -f "$f" ]; then
            cmd="$(basename "$f")"
            "$OS9" copy -o=0 -r "$f" "$TARGET,CMDS/$cmd" 2>/dev/null || true
            installed_cmds+=("$cmd")
        fi
    done
fi

# Aliases
"$OS9" copy -o=0 -r "$TARGET,CMDS/shell_21" "$TARGET,CMDS/shell" 2>/dev/null || true
"$OS9" copy -o=0 -r "$TARGET,CMDS/list" "$TARGET,CMDS/type" 2>/dev/null || true
installed_cmds+=("shell" "type")

# 7. System files & scripts
echo "Installing system files and scripts..."
NCLRC_SRC="/home/strick/modoc/coco-shelf/frobio/frob3/ncl/nclrc.tcl"
if [ -f "$NCLRC_SRC" ]; then
    "$OS9" copy -l -r "$NCLRC_SRC" "$TARGET,SYS/nclrc.tcl"
fi

TMP_STARTUP="$(mktemp)"
cat <<'EOF' > "$TMP_STARTUP"
tmode </term pau=0
setime 2001/01/01
chx /dd/CMDS
chd /dd/SRC
EOF
"$OS9" copy -l -r "$TMP_STARTUP" "$TARGET,startup"
rm -f "$TMP_STARTUP"

# Copy build scripts to root of disk
"$OS9" copy -l -r "$SCRIPT_DIR/selfgen_build.sh" "$TARGET,selfgen_build.sh"
"$OS9" copy -l -r "$SCRIPT_DIR/selfgen_build.tcl" "$TARGET,selfgen_build.tcl"

# 8. Set execution and read attributes
echo "Setting attributes on ${#installed_cmds[@]} commands..."
attr_targets=()
for cmd in "${installed_cmds[@]}"; do
    attr_targets+=("$TARGET,CMDS/$cmd")
done
if [ ${#attr_targets[@]} -gt 0 ]; then
    "$OS9" attr -q -pe -npw -pr -e -w -r "${attr_targets[@]}" 2>/dev/null || true
fi
"$OS9" attr -q -npw -pr -ne -w -r "$TARGET,selfgen_build.sh" 2>/dev/null || true
"$OS9" attr -q -npw -pr -ne -w -r "$TARGET,selfgen_build.tcl" 2>/dev/null || true
"$OS9" attr -q -npw -pr -ne -w -r "$TARGET,startup" 2>/dev/null || true

echo "=================================================================="
echo "Staging Complete! Target disk: $TARGET is ready for self-generation."
echo "=================================================================="
