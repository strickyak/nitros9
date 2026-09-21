#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NITROS9DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
MOD_DIR="${MOD_DIR:-$SCRIPT_DIR/.mods}"
OS9="${OS9:-os9}"

TARGET="${1:-$SCRIPT_DIR/flat0.dsk}"

echo "Building NitrOS-9 disk image: $TARGET"

# Ensure target directory exists
mkdir -p "$(dirname "$TARGET")"

# Remove existing disk image if present
rm -f "$TARGET"

# 1. Format disk with requested options
echo "Formatting disk: $TARGET"
"$OS9" format -e -n'FLAT65280' -l'40000' "$TARGET"

# 2. Create CMDS directory
echo "Creating CMDS directory..."
"$OS9" makdir "$TARGET,CMDS"

# 3. List of Level 1 commands to populate
CMDS=(
    asm attr backup bawk binex build calldbg cmp config copy cputype date
    dcheck debug ded deiniz del deldir devs dir dir_cb dirsort disasm display
    dmode dsave dump echo edit error exbin format format_d64 free go51
    grfdrv help ident iniz irqs keyrpt link list load login makdir
    mdir merge mfree minted more mpi ngu padrom park printerr
    procs prompt pwd pxd rename save setime shell shell_21 shellplus sleep
    stop tee tmode touch tsmon tuneport type unlink verify xmode
)

echo "Copying Level 1 commands from $MOD_DIR to CMDS..."
installed_cmds=()

for cmd in "${CMDS[@]}"; do
    src="$MOD_DIR/$cmd"
    if [ -f "$src" ]; then
        "$OS9" copy -o=0 "$src" "$TARGET,CMDS/$cmd"
        installed_cmds+=("$cmd")
    fi
done

# Optional language runtimes if available
BASIC09_SRC="/home/strick/modoc/coco-shelf/nitros9-languages/basic09/basic09_6809"
if [ -f "$BASIC09_SRC" ]; then
    echo "Installing Basic09..."
    "$OS9" copy -o=0 "$BASIC09_SRC" "$TARGET,CMDS/basic09"
    installed_cmds+=("basic09")
fi

RUNB_SRC="/home/strick/modoc/coco-shelf/nitros9-languages/basic09/runb_6809"
if [ -f "$RUNB_SRC" ]; then
    echo "Installing runb..."
    "$OS9" copy -o=0 "$RUNB_SRC" "$TARGET,CMDS/runb"
    installed_cmds+=("runb")
fi

# 4. Set execution attributes on all commands in CMDS
echo "Setting execute attributes on installed commands (${#installed_cmds[@]} commands)..."
attr_targets=()
for cmd in "${installed_cmds[@]}"; do
    attr_targets+=("$TARGET,CMDS/$cmd")
done

if [ ${#attr_targets[@]} -gt 0 ]; then
    "$OS9" attr -q -pe -npw -pr -e -w -r "${attr_targets[@]}"
fi

# 5. Create default startup script on disk
echo "Creating startup script..."
tmp_startup="$(mktemp)"
cat <<'EOF' > "$tmp_startup"
chx CMDS
EOF
"$OS9" copy -o=0 -l "$tmp_startup" "$TARGET,startup"
"$OS9" attr -q -npw -pr -ne -w -r "$TARGET,startup"
rm -f "$tmp_startup"

echo "Successfully built $TARGET with ${#installed_cmds[@]} commands in CMDS."
