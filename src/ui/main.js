document.addEventListener('DOMContentLoaded', () => {
    const optionSelect = document.getElementById('optionSelect');
    const runBtn = document.getElementById('runBtn');
    const status = document.getElementById('status');
    const output = document.getElementById('output');
    const systemInfo = document.getElementById('systemInfo');

    // ansi_up 인스턴스 생성
    const ansi_up = new AnsiUp();

    // 시스템 정보 파싱 함수 (기존과 동일)
    function parseSystemInfo(data) {
        if (!data) return {};
        const info = {};
        data.split('\n').forEach(line => {
            const colonIndex = line.indexOf(': ');
            if (colonIndex !== -1) {
                const key = line.substring(0, colonIndex).trim();
                const value = line.substring(colonIndex + 2).trim();
                info[key] = value;
            }
        });
        return info;
    }

    // API 호출 함수 (기존과 동일)
    function callAPI(action, params = {}) {
        const urlParams = new URLSearchParams();
        urlParams.append('action', action);
        Object.keys(params).forEach(key => urlParams.append(key, params[key]));

        return fetch('api.cgi', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: urlParams.toString()
        })
        .then(res => {
            if (!res.ok) throw new Error('Network response was not ok');
            return res.json();
        });
    }

    // 시스템 정보 로드 함수 (기존과 동일)
    function loadSystemInfo() {
        systemInfo.innerHTML = '<span style="color: #0066cc;">Loading system information...</span>';

        callAPI('info')
            .then(data => {
                if (data.success) {
                    let infoObj = {};
                    try {
                        infoObj = JSON.parse(data.result);
                    } catch (e) {
                        console.error('Failed to parse system info:', e);
                    }
                    systemInfo.innerHTML = `
                        <strong>MODEL:</strong> <span>${infoObj.MODEL || 'N/A'}</span>
                        <strong>PLATFORM:</strong> <span>${infoObj.PLATFORM || 'N/A'}</span>
                        <strong>DSM_VERSION:</strong> <span>${infoObj.DSM_VERSION || 'N/A'}</span>
                        <strong>Update:</strong> <span>${infoObj.Update || 'N/A'}</span>
                    `;
                } else {
                    systemInfo.innerHTML = `<span style="color: red;">Failed to load system information: ${data.message || 'Unknown error'}</span>`;
                }
            })
            .catch(error => {
                systemInfo.innerHTML = `<span style="color: red;">Error loading system information: ${error.message}</span>`;
            });
    }

    // 상태 업데이트 함수 (기존과 동일)
    function updateStatus(message, type = 'info') {
        status.textContent = message;
        status.className = 'status ' + type;
    }

    // 버튼 상태 관리
    function setButtonsEnabled(enabled) {
        runBtn.disabled = !enabled;
        optionSelect.disabled = !enabled;
    }

    function showSudoersGuide() {
        return `
            <div style="background:#fff3cd; border:1px solid #ffc107; border-radius:6px; padding:16px; margin-top:12px; font-family:monospace;">
                <strong style="color:#856404;">⚠️ 권한 설정이 필요합니다 / Permission Setup Required</strong><br><br>
                <span style="color:#333;">
                    setuid 헬퍼가 준비되지 않았습니다. 보통 DSM이 설치 시 자동으로 설정하므로 이 화면은 드물게 나타납니다.<br>
                    <em style="color:#666;">The setuid helper is not ready. DSM normally sets this up automatically at install time, so this message is rare.</em>
                </span><br><br>
                <div style="background:#1e1e1e; color:#d4d4d4; padding:12px; border-radius:4px; line-height:1.8;">
                    <span style="color:#6a9955;"># 1) 패키지를 재설치하면 대부분 자동으로 해결됩니다.</span><br>
                    <span style="color:#6a9955;">#    Reinstalling the package usually fixes this automatically.</span><br>
                    <br>
                    <span style="color:#6a9955;"># 2) 그래도 안 되면 아래로 수동 설정 / manual fallback:</span><br>
                    <span style="color:#569cd6;">sudo chown</span> root:package /var/packages/Synosmartinfo/target/bin/helper/smartinfo-helper.x86_64<br>
                    <span style="color:#569cd6;">sudo chmod</span> <span style="color:#b5cea8;">6550</span> /var/packages/Synosmartinfo/target/bin/helper/smartinfo-helper.x86_64
                </div>
                <br>
                <span style="color:#856404;">
                    설정 완료 후 다시 RUN 버튼을 눌러주세요.<br>
                    <em>After setup is complete, please click the RUN button again.</em>
                </span>
            </div>
        `;
    }
    
    // RUN 버튼 이벤트 핸들러 수정: ANSI -> HTML 변환 후 출력
    runBtn.addEventListener('click', () => {
        const selectedOption = optionSelect.value;

        updateStatus('Starting SMART scan... Please wait.', 'warning');
        output.textContent = 'Initiating SMART scan...\nPlease wait up to 2 minutes.';
        setButtonsEnabled(false);

        callAPI('run', { option: selectedOption })
            .then(response => {
                if (response.success) {
                    updateStatus('Success: ' + response.message, 'success');

                    if (response.result && response.result.trim()) {
                        // ANSI 컬러 코드를 HTML 스타일로 변환
                        const html = ansi_up.ansi_to_html(response.result);
                        output.innerHTML = html;
                    } else {
                        output.textContent = 'No SMART result data returned.';
                    }
                } else {
                    updateStatus('Failed: ' + response.message, 'error');
                    // sudoers 파일 미존재 여부 감지
                    if (response.sudoers_missing === true) {
                        output.innerHTML = 'Error: ' + response.message + showSudoersGuide();
                    } else {
                        output.textContent = 'Error: ' + response.message;
                    }
                }
            })
            .catch(error => {
                console.error('Run command error:', error);
                updateStatus('Error: ' + error.message, 'error');
                output.textContent = 'Error occurred: ' + error.message;
            })
            .finally(() => {
                setButtonsEnabled(true);
            });
    });

    // 초기 시스템 정보 자동 로드
    loadSystemInfo();
});
//
