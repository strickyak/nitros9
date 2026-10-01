#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-/tmp/pc/disk0.dsk}"
TFR9_DIR="/home/strick/modoc/coco-shelf/tfr9/v4"
WIRE="${WIRE:-/dev/ttyACM0}"

echo "=================================================================="
echo "NitrOS-9 Level 2 Native Self-Generation on TFR911h Hardware"
echo "Wire: $WIRE"
echo "Disk: $TARGET"
echo "=================================================================="

# Check for serial device
if [ ! -e "$WIRE" ]; then
    echo "ERROR: Serial device $WIRE not found!" >&2
    exit 1
fi

mkdir -p /tmp/pc
cp "$SCRIPT_DIR/deep65280.img" /tmp/pc/deep65280.img
cp "$SCRIPT_DIR/boot_tfr9.tcl" /tmp/pc/boot_deep.tcl
cp "$SCRIPT_DIR/boot_tfr9.tcl" /tmp/pc/boot_tfr9.tcl
cp "$SCRIPT_DIR/boot_tfr9_verify.tcl" /tmp/pc/boot_tfr9_verify.tcl
ln -sf "$(basename "$TARGET")" /tmp/pc/deep0.dsk

cat <<'EOF' > /tmp/pc/mode9.tcl
# mode9.tcl on PC filesystem
source /pc/boot_deep.tcl
EOF

echo "Launching tether on TFR911h (build will auto-start via /dd/startup)..."
go run "$TFR9_DIR/tether/" -wire "$WIRE" -pc /tmp/pc -level 2 -bootmode 9 < /dev/null

EXIT_CODE=$?
echo "=================================================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "TFR911h Native Self-Generation Completed Successfully!"
    echo "=================================================================="
    if [ -f "$TARGET" ]; then
        echo "Extracting self-generated boot image from $TARGET..."
        os9 copy -o=0 -r "$TARGET,deep65280.new.img" /tmp/pc/deep65280.new.img 2>/dev/null || true
        if [ -f /tmp/pc/deep65280.new.img ]; then
            ls -la /tmp/pc/deep65280.new.img
        fi
    fi
else
    echo "TFR911h Self-Generation Failed with exit code $EXIT_CODE" >&2
    echo "=================================================================="
fi
exit $EXIT_CODE
