#!/bin/bash
RESULT_DIR="/usr/syno/synoman/webman/3rdparty/Synosmartinfo/result"
RESULT_FILE="$RESULT_DIR/smart.result"
TMP_FILE="$RESULT_FILE.tmp"
SMART_SCRIPT="/var/packages/Synosmartinfo/target/bin/syno_smart_info.sh"

mkdir -p "$RESULT_DIR"

# 실행 (옵션 전달 가능)
if [ -n "$1" ]; then
    "$SMART_SCRIPT" "$1" 2>&1 > "$TMP_FILE"
else
    "$SMART_SCRIPT" 2>&1 > "$TMP_FILE"
fi

if [ $? -eq 0 ]; then
    mv "$TMP_FILE" "$RESULT_FILE"
    chmod 644 "$RESULT_FILE"
    exit 0
else
    echo "ERROR: Failed to run syno_smart_info.sh" > "$RESULT_FILE"
    cat "$TMP_FILE" >> "$RESULT_FILE"
    chmod 644 "$RESULT_FILE"
    exit 1
fi
