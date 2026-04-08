#!/bin/bash

#########################################################################
# Synology SMART Info API - CGI endpoint
#
# Runs as the non-root package user (synosmartinfo).
# Privileged SMART operations are delegated to smart_helper via Unix
# domain socket — no sudo required.
#########################################################################

# --------- 1. 경로 상수 --------------------------------------------------

PKG_NAME="Synosmartinfo"
PKG_ROOT="/var/packages/${PKG_NAME}"
TARGET_DIR="${PKG_ROOT}/target"
LOG_DIR="${PKG_ROOT}/var"
LOG_FILE="${LOG_DIR}/api.log"
BIN_DIR="${TARGET_DIR}/bin"
RESULT_DIR="/usr/syno/synoman/webman/3rdparty/${PKG_NAME}/result"
RESULT_FILE="${RESULT_DIR}/smart.result"
SMART_CLIENT="${BIN_DIR}/smart_client.py"

mkdir -p "${LOG_DIR}" "${RESULT_DIR}"
touch "${LOG_FILE}"
chmod 644 "${LOG_FILE}"
chmod 755 "${RESULT_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "${LOG_FILE}"
}

# --------- 2. HTTP 헤더 -------------------------------------------------

echo "Content-Type: application/json; charset=utf-8"
echo "Access-Control-Allow-Origin: *"
echo "Access-Control-Allow-Methods: GET, POST"
echo "Access-Control-Allow-Headers: Content-Type"
echo ""

# --------- 3. URL-encoded 파라미터 파싱 ----------------------------------

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

# --------- 4. JSON 유틸 함수 --------------------------------------------

json_escape() {
    echo "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

json_response() {
    local ok="$1" msg="$2" data="$3"
    local msg_json
    msg_json=$(echo "$msg" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))')
    if [ -z "$data" ]; then
        echo "{\"success\":${ok}, \"message\":${msg_json}, \"result\":null}"
    else
        local data_json
        data_json=$(json_escape "$data")
        echo "{\"success\":${ok}, \"message\":${msg_json}, \"result\":${data_json}}"
    fi
}

# --------- 5. 시스템 정보 함수 ------------------------------------------

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

# --------- 6. Helper 통신 함수 ------------------------------------------
# smart_client.py 를 통해 Unix domain socket 으로 smart_helper 에 요청.
# 항상 JSON 문자열을 stdout 으로 반환한다.

call_helper() {
    local action="$1"
    local option="$2"
    python3 "${SMART_CLIENT}" "${action}" "${option}"
}

# helper 응답 JSON 에서 필드를 추출하는 헬퍼 (stdin 으로 JSON 수신)
extract_field() {
    local field="$1"
    python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('${field}',''))"
}

# --------- 7. 액션 처리 -------------------------------------------------

case "${ACTION}" in

info)
    log "[INFO] Getting system information"
    DATA="$(get_system_info)"
    json_response true "System information retrieved" "${DATA}"
    ;;

run)
    # 허용 옵션 화이트리스트 검증 (api.cgi 레벨 — helper 도 독립적으로 검증)
    case "${OPTION}" in
        ""|"-a"|"-i"|"-v"|"-h"|"-e") ;;  # OK
        *)
            log "[WARN] Rejected invalid option: ${OPTION}"
            json_response false "Invalid option: ${OPTION}" ""
            exit 0
            ;;
    esac

    if [ ! -f "${SMART_CLIENT}" ]; then
        log "[ERROR] smart_client.py not found: ${SMART_CLIENT}"
        json_response false "Smart client not found" ""
        exit 0
    fi

    TMP_RESULT="${RESULT_FILE}.tmp"
    rm -f "${TMP_RESULT}"

    # helper 에 요청 → JSON 응답 수신
    HELPER_RESPONSE="$(call_helper smart_scan "${OPTION}")"
    CALL_STATUS=$?

    if [ ${CALL_STATUS} -ne 0 ] || [ -z "${HELPER_RESPONSE}" ]; then
        log "[ERROR] Helper communication failed (exit=${CALL_STATUS})"
        json_response false "Helper communication failed" ""
        exit 0
    fi

    # 응답 파싱
    SUCCESS="$(echo "${HELPER_RESPONSE}" | python3 -c \
        'import json,sys; d=json.load(sys.stdin); print("true" if d.get("success") else "false")' \
        2>/dev/null)"
    SMART_OUTPUT="$(echo "${HELPER_RESPONSE}" | extract_field output 2>/dev/null)"
    HELPER_ERROR="$(echo "${HELPER_RESPONSE}"  | extract_field error  2>/dev/null)"

    if [ "${SUCCESS}" = "true" ] && [ -n "${SMART_OUTPUT}" ]; then
        echo "${SMART_OUTPUT}" > "${TMP_RESULT}"
        mv "${TMP_RESULT}" "${RESULT_FILE}"
        chmod 644 "${RESULT_FILE}"
        log "[INFO] SMART scan completed successfully"
        json_response true "SMART scan completed" "${SMART_OUTPUT}"
    else
        ERROR_MSG="${HELPER_ERROR:-Unknown error}"
        log "[ERROR] SMART scan failed: ${ERROR_MSG}"
        json_response false "SMART scan failed" "${ERROR_MSG}"
    fi
    ;;

*)
    log "[ERROR] Invalid action: ${ACTION}"
    json_response false "Invalid action: ${ACTION}" ""
    ;;
esac

exit 0
