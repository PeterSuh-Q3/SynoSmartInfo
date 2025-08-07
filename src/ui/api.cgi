#!/bin/bash

#########################################################################
# Synology SMART Info API - CGI API (generate_smart_result.sh 내용 내부 통합)
#########################################################################

# --------- 1. 공통 변수 및 경로 계산 ---------------------------------

PKG_NAME="Synosmartinfo"
PKG_ROOT="/var/packages/${PKG_NAME}"
TARGET_DIR="${PKG_ROOT}/target"
LOG_DIR="${PKG_ROOT}/var"
LOG_FILE="${LOG_DIR}/api.log"
BIN_DIR="${TARGET_DIR}/bin"
RESULT_DIR="/usr/syno/synoman/webman/3rdparty/${PKG_NAME}/result"
RESULT_FILE="${RESULT_DIR}/smart.result"

SMART_SCRIPT="${BIN_DIR}/syno_smart_info.sh"

mkdir -p "${LOG_DIR}" "${RESULT_DIR}"

touch "${LOG_FILE}"
chmod 644 "${LOG_FILE}"
chmod 755 "${RESULT_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "${LOG_FILE}"
}

# --------- 3. HTTP 헤더 출력 ----------------------------------------

echo "Content-Type: application/json; charset=utf-8"
echo "Access-Control-Allow-Origin: *"
echo "Access-Control-Allow-Methods: GET, POST"
echo "Access-Control-Allow-Headers: Content-Type"
echo "" # 헤더/바디 구분 빈줄

# --------- 4. URL-encoded 파라미터 파싱 ------------------------------

urldecode() { : "${*//+/ }"; echo -e "${_//%/\\x}"; }
declare -A PARAM
parse_kv() {
    local kv_pair key val
    IFS='&' read -ra kv_pair <<< "$1"
    for pair in "${kv_pair[@]}"; do
        IFS='=' read -r key val <<< "${pair}"
        key="$(urldecode "${key}")"
        val="$(urldecode "${val}")"
        PARAM["${key}"]="${val}"
    done
}

case "$REQUEST_METHOD" in
POST)
    CONTENT_LENGTH=${CONTENT_LENGTH:-0}
    if [ "$CONTENT_LENGTH" -gt 0 ]; then
        read -r -n "$CONTENT_LENGTH" POST_DATA
    else
        POST_DATA=""
    fi
    parse_kv "${POST_DATA}"
    ;;
GET)
    parse_kv "${QUERY_STRING}"
    ;;
*)
    log "Unsupported METHOD: ${REQUEST_METHOD}"
    echo '{"success":false,"message":"Unsupported METHOD","result":null}'
    exit 0
    ;;
esac

ACTION="${PARAM[action]}"
OPTION="${PARAM[option]}"
log "Request: ACTION=${ACTION}, OPTION=[${OPTION}]"

# --------- 5. JSON 유틸 함수 ----------------------------------------

json_escape() {
    echo "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

json_response() {
    local ok="$1" msg="$2" data="$3"
    local msg_json=$(echo "$msg" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))')
    if [ -z "$data" ]; then
        echo "{\"success\":$ok, \"message\":$msg_json, \"result\":null}"
    else
        local data_json=$(json_escape "$data")
        echo "{\"success\":$ok, \"message\":$msg_json, \"result\":$data_json}"
    fi
}

clean_system_string() {
    local input="$1"
    input=$(echo "$input" | sed 's/ unknown//g; s/unknown //g; s/^unknown$//')
    input=$(echo "$input" | sed 's/  */ /g; s/^ *//; s/ *$//')
    if [ -z "$input" ] || [ "$input" = " " ]; then
        echo "N/A"
    else
        echo "$input"
    fi
}

get_system_info() {
    local model platform productversion build version smallfix

    model="$(cat /proc/sys/kernel/syno_hw_version 2>/dev/null || echo '')"
    platform="$(/bin/get_key_value /etc.defaults/synoinfo.conf platform_name 2>/dev/null || echo '')"
    productversion="$(/bin/get_key_value /etc.defaults/VERSION productversion 2>/dev/null || echo '')"
    build="$(/bin/get_key_value /etc.defaults/VERSION buildnumber 2>/dev/null || echo '')"

    if [ -n "$productversion" ] && [ -n "$build" ]; then
        version="${productversion}-${build}"
    else
        version=""
    fi

    smallfix="$(/bin/get_key_value /etc.defaults/VERSION smallfixnumber 2>/dev/null || echo '')"

    model="$(clean_system_string "$model")"
    platform="$(clean_system_string "$platform")"
    version="$(clean_system_string "$version")"
    smallfix="$(clean_system_string "$smallfix")"

    python3 -c "
import json
print(json.dumps({
'MODEL': '$model',
'PLATFORM': '$platform',
'DSM_VERSION': '$version',
'Update': '$smallfix'
}))"
}

# --------- 8. 액션 처리 -------------------------------------------

case "${ACTION}" in
info)
    log "[DEBUG] Getting system information"
    DATA="$(get_system_info)"
    json_response true "System information retrieved" "${DATA}"
    ;;

run)
    case "${OPTION}" in
        "-v"|"-h")
            # Finished 대기 없이 바로 실행 + 출력
            if [ ! -x "${SMART_SCRIPT}" ]; then
                json_response false "Smart script not found or not executable" ""
                log "[ERROR] Smart script not found or not executable"
                exit 0
            fi
    
            TMP_RESULT="${RESULT_FILE}.tmp"
            TMP_STDERR="${LOG_DIR}/last_smart_stderr.log"
            rm -f "$TMP_RESULT" "$TMP_STDERR"
    
            timeout 30 sudo "${SMART_SCRIPT}" "$OPTION" > "$TMP_RESULT" 2> "$TMP_STDERR"
            sleep 0.3  # 300ms 정도 대기
            RET=$?
    
            if [ $RET -eq 0 ] && [ -s "$TMP_RESULT" ]; then
                mv "$TMP_RESULT" "${RESULT_FILE}"
                chmod 644 "${RESULT_FILE}"
                SMART_RESULT="$(cat "${RESULT_FILE}")"
                json_response true "SMART script output" "$SMART_RESULT"
            else
                LAST_ERROR=$(tail -20 "$TMP_STDERR" | tail -c 2000 | sed ':a;N;$!ba;s/\n/\\n/g')
                [ -z "$LAST_ERROR" ] && LAST_ERROR="Unknown error or no error output"
                json_response false "SMART script failed" "$LAST_ERROR"
                log "[ERROR] SMART script failed: $LAST_ERROR"
            fi
            ;;
        ""|"-a")
            # 기존 Finished 대기 루프 방식
            if [ ! -x "${SMART_SCRIPT}" ]; then
                json_response false "Smart script not found or not executable" ""
                log "[ERROR] Smart script not found or not executable"
                exit 0
            fi
    
            TMP_RESULT="${RESULT_FILE}.tmp"
            TMP_STDERR="${LOG_DIR}/last_smart_stderr.log"
            rm -f "$TMP_RESULT" "$TMP_STDERR"
    
            if [ -n "$OPTION" ]; then
                timeout 240 sudo "${SMART_SCRIPT}" "$OPTION" > "$TMP_RESULT" 2> "$TMP_STDERR" &
            else
                timeout 240 sudo "${SMART_SCRIPT}" > "$TMP_RESULT" 2> "$TMP_STDERR" &
            fi
            CMD_PID=$!
    
            i=0
            while [ $i -lt 240 ]; do
                if grep -q "Finished" "$TMP_RESULT" 2>/dev/null; then
                    break
                fi
                if ! kill -0 $CMD_PID 2>/dev/null; then
                    break
                fi
                sleep 1
                i=$((i+1))
            done
    
            if kill -0 $CMD_PID 2>/dev/null; then
                kill $CMD_PID 2>/dev/null
                wait $CMD_PID 2>/dev/null
            fi
    
            if grep -q "Finished" "$TMP_RESULT" 2>/dev/null; then
                mv "$TMP_RESULT" "${RESULT_FILE}"
                chmod 644 "${RESULT_FILE}"
                SMART_RESULT="$(cat "${RESULT_FILE}")"
                json_response true "SMART scan completed" "$SMART_RESULT"
            else
                LAST_ERROR=$(tail -20 "$TMP_STDERR" | tail -c 2000 | sed ':a;N;$!ba;s/\n/\\n/g')
                [ -z "$LAST_ERROR" ] && LAST_ERROR="Unknown error or no error output"
                json_response false "SMART scan failed" "$LAST_ERROR"
                log "[ERROR] SMART scan failed: $LAST_ERROR"
            fi
            ;;
        *)
            json_response false "Invalid option: ${OPTION}" ""
            exit 0
            ;;
        esac
        ;;
*)
    log "[ERROR] Invalid action: ${ACTION}"
    json_response false "Invalid action: ${ACTION}" ""
    ;;
esac

exit 0
