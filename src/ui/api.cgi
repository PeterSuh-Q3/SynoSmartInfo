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
# DSM applies root-owned setuid (6550) to this exact path at install time,
# per the "tool" section of conf/privilege. Nothing copies or chmods it.
HELPER_BIN="${BIN_DIR}/helper/smartinfo-helper.$(uname -m)"

mkdir -p "${LOG_DIR}" "${RESULT_DIR}"

touch "${LOG_FILE}"
chmod 644 "${LOG_FILE}"
chmod 755 "${RESULT_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "${LOG_FILE}"
}

# --------- 3. HTTP 헤더 출력 ----------------------------------------

echo "Content-Type: application/json; charset=utf-8"
echo "" # 헤더/바디 구분 빈줄

# --------- DSM 세션 인증 -----------------------------------------------
#
# 다른 걸 하기 전에 반드시 먼저 체크해야 한다. DSM은 webman/3rdparty/
# 아래 서드파티 CGI를 대신 인증해주지 않는다 - 패키지 자신의 책임이다.
# 실기기(DSM 7.4.1/SA6400)로 확인: 이 검사가 없으면 같은 네트워크의
# 다른 머신에서 인증 없이 curl만으로 SMART 데이터(디스크 시리얼 포함)를
# 그대로 읽어갈 수 있었다 (MSHELL Manager에서 동일 패턴의 취약점을
# 먼저 발견·수정하며 확인).
#
# authenticate.cgi는 로그인된 DSM 사용자명을 출력하고, 세션이 없으면
# 아무것도 출력하지 않는다.
AUTH_USER="$(/usr/syno/synoman/webman/modules/authenticate.cgi 2>/dev/null)"
if [ -z "${AUTH_USER}" ]; then
    log "[SECURITY] rejected unauthenticated request from ${REMOTE_ADDR:-unknown}"
    echo '{"success":false,"message":"unauthorized - sign in to DSM first","result":null}'
    exit 0
fi

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
    local ok="$1" msg="$2" data="$3" sudoers_missing="${4:-false}"
    local msg_json=$(echo "$msg" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))')
    if [ -z "$data" ]; then
        echo "{\"success\":$ok, \"message\":$msg_json, \"result\":null, \"sudoers_missing\":$sudoers_missing}"
    else
        local data_json=$(json_escape "$data")
        echo "{\"success\":$ok, \"message\":$msg_json, \"result\":$data_json, \"sudoers_missing\":$sudoers_missing}"
    fi
}

# 권한 상승 경로 체크: setuid 헬퍼(우선) 또는 sudoers(레거시 폴백) 중
# 하나라도 사용 가능하면 false(정상), 둘 다 없으면 true(설정 필요)
check_sudoers() {
    if [ -u "${HELPER_BIN}" ] && [ -x "${HELPER_BIN}" ]; then
        echo "false"
    elif [ -f "/etc/sudoers.d/Synosmartinfo" ]; then
        echo "false"
    else
        echo "true"
    fi
}

# setuid 헬퍼가 있으면 우선 사용, 없으면 sudo 로 폴백.
# timeout(1)은 셸 함수를 직접 실행할 수 없으므로(execvp로 바로 찾음),
# 여기서 실제 실행 파일에 timeout 을 건다 - 호출부에서
# "timeout N run_smart ..." 처럼 감싸면 "run_smart: No such file"로 깨진다.
run_smart() {
    local secs="$1" opt="$2"
    if [ -u "${HELPER_BIN}" ] && [ -x "${HELPER_BIN}" ]; then
        timeout "${secs}" "${HELPER_BIN}" "${opt}"
    else
        if [ -n "${opt}" ]; then
            timeout "${secs}" sudo "${SMART_SCRIPT}" "${opt}"
        else
            timeout "${secs}" sudo "${SMART_SCRIPT}"
        fi
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
    
            # 요청마다 고유한 파일명을 써서, 연속/겹치는 요청 사이에
            # 같은 임시 파일을 공유하다 생기는 경합을 방지한다.
            TMP_RESULT="${RESULT_FILE}.tmp.$$"
            TMP_STDERR="${LOG_DIR}/last_smart_stderr.log.$$"
            rm -f "$TMP_RESULT" "$TMP_STDERR"
    
            run_smart 30 "$OPTION" > "$TMP_RESULT" 2> "$TMP_STDERR"
            sleep 0.3  # 300ms 정도 대기
            RET=$?
    
            cp -f "$TMP_STDERR" "${LOG_DIR}/last_smart_stderr.log" 2>/dev/null

            if [ $RET -eq 0 ] && [ -s "$TMP_RESULT" ]; then
                mv "$TMP_RESULT" "${RESULT_FILE}"
                chmod 644 "${RESULT_FILE}"
                SMART_RESULT="$(cat "${RESULT_FILE}")"
                json_response true "SMART script output" "$SMART_RESULT"
            else
                LAST_ERROR=$(tail -20 "$TMP_STDERR" | tail -c 2000 | sed ':a;N;$!ba;s/\n/\\n/g')
                [ -z "$LAST_ERROR" ] && LAST_ERROR="Unknown error or no error output"
                SUDOERS_MISSING=$(check_sudoers)
                json_response false "SMART script failed" "$LAST_ERROR" "$SUDOERS_MISSING"
                log "[ERROR] SMART script failed: $LAST_ERROR"
            fi
            rm -f "$TMP_RESULT" "$TMP_STDERR"
            ;;
        ""|"-a")
            # 기존 Finished 대기 루프 방식
            if [ ! -x "${SMART_SCRIPT}" ]; then
                json_response false "Smart script not found or not executable" ""
                log "[ERROR] Smart script not found or not executable"
                exit 0
            fi
    
            # 요청마다 고유한 파일명을 써서, 연속/겹치는 요청 사이에
            # 같은 임시 파일을 공유하다 생기는 경합을 방지한다.
            TMP_RESULT="${RESULT_FILE}.tmp.$$"
            TMP_STDERR="${LOG_DIR}/last_smart_stderr.log.$$"
            rm -f "$TMP_RESULT" "$TMP_STDERR"
    
            run_smart 240 "$OPTION" > "$TMP_RESULT" 2> "$TMP_STDERR" &
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
    
            cp -f "$TMP_STDERR" "${LOG_DIR}/last_smart_stderr.log" 2>/dev/null

            if grep -q "Finished" "$TMP_RESULT" 2>/dev/null; then
                mv "$TMP_RESULT" "${RESULT_FILE}"
                chmod 644 "${RESULT_FILE}"
                SMART_RESULT="$(cat "${RESULT_FILE}")"
                json_response true "SMART scan completed" "$SMART_RESULT"
            else
                LAST_ERROR=$(tail -20 "$TMP_STDERR" | tail -c 2000 | sed ':a;N;$!ba;s/\n/\\n/g')
                [ -z "$LAST_ERROR" ] && LAST_ERROR="Unknown error or no error output"
                SUDOERS_MISSING=$(check_sudoers)
                json_response false "SMART scan failed" "$LAST_ERROR" "$SUDOERS_MISSING"
                log "[ERROR] SMART scan failed: $LAST_ERROR"
            fi
            rm -f "$TMP_RESULT" "$TMP_STDERR"
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
