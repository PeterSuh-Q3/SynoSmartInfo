#!/bin/bash

BOT_TOKEN="${1}"
CHAT_ID="${2}"
URL="https://api.telegram.org/bot${BOT_TOKEN}/sendMessage"

LOG_DIR="/usr/mshell/smartlogs"

# 로그 디렉토리 생성 (없으면 생성)
mkdir -p "$LOG_DIR"

# 실행 정보 저장 파일 (이전 값 보관용) - 유지하려면 /volume1/log 에 함께 저장
DATA_FILE="${LOG_DIR}/smart_id199_counts.txt"

# 오늘 날짜 기반 로그 파일명
TODAY=$(date '+%Y-%m-%d')
LOG_FILE="${LOG_DIR}/smart_id199_history_${TODAY}.json"

DISKS=$(ls /dev/sd? /dev/sata? 2>/dev/null)

declare -A prev_counts
first_run=false

is_seagate(){
    DEVICE=$("$SMARTCTL" -A -i "${1}" | awk -F ' ' '/Device Model/{print $3}')
    if [[ "${DEVICE:0:2}" == "ST" ]]; then
        return 0
    else
        return 1
    fi
}

# Get smartctl location and check if version 7
if which smartctl7 >/dev/null; then
    # smartmontools 7 from SynoCli Disk Tools is installed
    SMARTCTL=$(which smartctl7)
    smartversion=7
else
    SMARTCTL=$(which smartctl)
    smartversion=6
fi

# 이전 값 불러오기 (시리얼 넘버 기반)
if [ -f "$DATA_FILE" ]; then
  while IFS=' ' read -r serial count; do
    prev_counts[$serial]=$count
  done < "$DATA_FILE"
else
  first_run=true
fi

declare -A new_counts
declare -A serial_to_disk

# 실행 시간
timestamp=$(date '+%Y-%m-%d %H:%M:%S')

for disk in $DISKS; do
  # Check if a Seagate drive
  if is_seagate "$disk"; then
      seagate="yes"
  else
      seagate=
  fi
    
  smart_info=$($SMARTCTL -i "$disk" 2>/dev/null)
  
  # 모델명과 시리얼 넘버 추출
  if [[ $seagate == "yes" ]]; then
    model=$(echo "$smart_info" | grep -i '^Device Model:' | sed 's/Device Model:\s*//')
    serial=$(echo "$smart_info" | grep -i '^Serial Number:' | sed 's/Serial Number:\s*//')
  else
    model=$(echo "$smart_info" | grep -i '^Product:' | sed 's/Product:\s*//')
    serial=$(echo "$smart_info" | grep -i '^Serial number:' | sed 's/Serial number:\s*//')
  fi
  
  # 시리얼 넘버가 없으면 해당 디스크 건너뛰기
  if [ -z "$serial" ]; then
    continue
  fi
  
  # 시리얼 넘버와 디스크 경로 매핑
  serial_to_disk[$serial]=$disk
  
  # SMART 199 값 추출
  raw_val=$($SMARTCTL -A -d sat -v 199,raw48 "$disk" 2>/dev/null | awk '$1 == 199 {print $10; exit}')
  
  if [[ ! "$raw_val" =~ ^[0-9]+$ ]]; then
    raw_val=0
  fi
  
  # 시리얼 넘버를 키로 사용
  new_counts[$serial]=$raw_val
  
  prev_val=${prev_counts[$serial]:-0}
  diff=$((raw_val - prev_val))
  
  # JSON 로그 기록 (NDJSON 형식)
  echo "{\"timestamp\":\"$timestamp\",\"disk\":\"$disk\",\"model\":\"$model\",\"serial\":\"$serial\",\"id199\":$raw_val,\"prev\":$prev_val,\"diff\":$diff}" >> "$LOG_FILE"
  
  # 알림 (최초 실행 제외)
  if [ "$first_run" = false ] && [ "$diff" -gt 0 ]; then
    text="[Synology UDMA_CRC detection] $disk 199 UDMA_CRC increments occurred $diff times in (MODEL: $model, S/N: $serial)"
    curl -s --data "chat_id=${CHAT_ID}&text=${text}" "${URL}" > /dev/null 2>&1
  fi
done

# 현재 값 저장 (시리얼 넘버 기반)
> "$DATA_FILE"
for serial in "${!new_counts[@]}"; do
  echo "$serial ${new_counts[$serial]}" >> "$DATA_FILE"
done
