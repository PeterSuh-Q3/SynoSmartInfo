# Synology SPK 패키지 빌드 노하우

> SynoSmartInfo v2.0.0 개발 과정에서 실기기(DSM 7.4.1, SA6400/epyc7002)
> 테스트로 실증한 내용. MSHELL Manager를 포함해 이후 모든 DSM 서드파티
> 패키지 개발에 적용 가능. CI 성공은 DSM 설치 성공을 보장하지 않으므로,
> 아래 항목은 전부 **실기기 `synopkg install`로 검증된 사실**이다.

## 1. 권한 모델: postinst는 기본적으로 root가 아니다

서드파티 패키지의 `preinst`/`postinst`/`preuninst`/`postuninst`/
`preupgrade`/`postupgrade`는 **`conf/privilege`의 `defaults.run-as`를
그대로 따른다.** "설치 스크립트는 항상 root로 돈다"는 통념은 틀렸다
(DSM 7.4.1 실기기에서 `run-as: package` + ctrl-script 미지정 시
`postinst`가 서비스 계정으로 실행됨을 직접 확인).

### root가 필요한 파일에 setuid를 걸어야 할 때

**`postinst`에서 `chown root + chmod 6755`를 시도하지 말 것** — 서드파티
패키지는 `conf/privilege` 어디에도 `run-as: root`를 선언할 수 없다
(선언 시 DSM이 설치 자체를 `error 319 "invalid package privilege
content"`로 거부, 스크립트 실행 전 단계에서 막힘).

대신 `conf/privilege`의 **`tool` 섹션**을 쓴다 — DSM이 설치 시점에
**직접** 해당 파일을 지정한 소유자/권한으로 만들어 준다:

```json
{
  "defaults": { "run-as": "package" },
  "username": "sc-mypackage",
  "groupname": "mypackage",
  "tool": [
    {
      "relpath": "bin/helper/my-helper.x86_64",
      "user": "root",
      "group": "package",
      "permission": "6550"
    }
  ]
}
```

- `relpath`는 `target/` 기준 상대경로.
- `group`은 반드시 `"package"`(패키지 자체 그룹으로 치환됨) — `"root"`를
  쓰면 이것도 error 319로 거부된다.
- 결과: `-r-sr-s--- root <pkg-group> my-helper.x86_64` — 패키지 자신의
  서비스 그룹만 실행 가능한 setuid 바이너리. sudoers 전면허용보다
  훨씬 좁다.
- `postinst`는 이 결과를 **검증만** 하면 된다(`[ -u "$HELPER" ]`),
  직접 만들 필요가 없다.

### ctrl-script로 특정 액션만 root가 필요한 경우

`preinst`/`postinst`/`preuninst`/`postuninst`/`preupgrade`/
`postupgrade`/`start`/`stop`/`status`/`log`/`install_uifile` 액션별로
`run-as`를 override할 수 있다. 단, **정확한 조합/필드 스키마를
DSM이 엄격히 검증**하므로 임의로 추측해 쓰지 말고, 실기기의
`/var/packages/*/conf/privilege`(Synology 공식 패키지 다수가 이미
이 패턴을 씀 — StorageAnalyzer, SynoFinder, DownloadStation 등)를
먼저 훑어서 실제로 통과하는 형태를 확인할 것.

## 2. INFO 파일에서 빌더가 조용히 빠뜨리는 필드들

서드파티 빌드 툴(예: `tomgrv/synology-package-builder`류 래퍼)은
`package.json` → `INFO` 매핑이 **완전하지 않을 수 있다.** 빌드
후 `INFO`를 직접 열어서 다음을 확인할 것.

- **`checksum`**: `md5(package.tgz)` 값이 없으면 수동 설치 시
  `error 289 "spk is not from synology"`로 거부된다. 공식
  `pkgscripts-ng`는 자동으로 채우지만, 래퍼 툴은 안 채울 수 있다 —
  없으면 빌드 후처리 단계에서 직접 계산해 넣을 것.
- **`ctl_stop`/`ctl_uninstall`**: `package.json`에 넣어도 빌더가
  아예 매핑을 안 할 수 있다. 상시 데몬이 없는 패키지(요청마다
  CGI 실행)라면 `ctl_stop="no"`를 INFO에 직접 주입해서 패키지
  센터의 시작/중지 토글을 없앨 것 — 없으면 사용자에게 혼란을 준다.

## 3. 리포 디렉터리 구조 = 빌더가 실제로 패키징하는 경로와 반드시 일치해야 함

`conf/`, `WIZARD_UIFILES/` 등을 리포 루트에 두는 습관이 있으면
위험하다. 사용하는 빌드 툴이 실제로 어느 디렉터리를 패키지 안에
집어넣는지 **빌드 스크립트 소스를 직접 읽어서** 확인할 것 — 그냥
관례적으로 어떤 폴더 이름을 쓰면 반영될 거라 가정하지 말 것. (이번
사례: `conf/`가 리포 루트에 있었지만 빌더는 `<repo>/synology/*`만
패키징 — `conf/privilege`를 아무리 고쳐도 빌드 산출물엔 한 번도
반영된 적이 없었음. 이동 후 해결.)

## 4. 서드파티 빌더의 숨은 부작용: 조건부 강제 의존성

빌더가 `conf/presets`나 `conf/resource`의 특정 키(`"docker"` 등)
**존재 여부만으로** `install_dep_packages`에 패키지 의존성을 몰래
추가하는 경우가 있다(예: `has("docker")`가 true면 배열이 비어있어도
`ContainerManager>=20.0.0-0` 강제 추가). 안 쓰는 기능이면 관련 설정
파일 자체를 만들지 말 것. 빌드 후 `INFO`의 `install_dep_packages`를
항상 눈으로 확인할 것.

## 5. start-stop-status의 `status`는 DSM이 주기적으로 폴링해서 헬스체크에 쓴다

`status` 액션이 exit 0이 아니면 DSM이 실행 중인 패키지를 "비정상"으로
보고 **자동으로 중지**시킨다(`synopkg.log`: `"begin to stop due to
abnormal status"`). 상시 데몬이 없는 패키지라도 `status`는 반드시
**현재 실제로 유효한 상태**(예: setuid 헬퍼가 제자리에 있는지)를
확인해서 반환해야 한다. 리팩터링 중 옛 메커니즘(예: 이제 안 쓰는
sudoers 파일 존재 여부)을 그대로 남겨두면 영구적으로 비정상 판정을
받는다 — 권한 모델을 바꿀 때 `status` 로직도 반드시 같이 바꿀 것.

## 6. 셸 스크립팅 함정: `timeout(1)`은 셸 함수를 직접 실행 못 함

```sh
timeout 30 my_shell_function "$arg"   # 깨짐: "No such file or directory"
```

`timeout`은 `execvp`로 인자를 바로 실행하려 하므로 셸 함수 이름을
찾지 못한다. `timeout`은 함수 **내부에서, 실제 바이너리 호출에** 걸
것.

## 7. Synology 툴체인 다운로드는 불안정하다 — 자체 미러링으로 해결

`dataupdate7.synology.com` / `global.synologydownload.com`에서
받는 DSM 빌드 툴체인(`base_env-<dsm>.txz`,
`ds.<platform>-<dsm>.{env,dev}.txz`)은 CI에서 자주 멈추거나
`ContentTooShortError`로 끊긴다. 해결책: 필요한 툴체인 파일을 우리
저장소 GitHub Release(예: 태그 `TOOLCHAIN`)에 미러링해두고, 빌드
스크립트가 `EnvDeploy` 호출 전에 그 릴리즈에서 먼저 받아
`toolkit_tarballs/`에 채운 뒤 `EnvDeploy -D`(다운로드 생략)로
호출하도록 한다. 미러 실패 시 기존 Synology 다운로드로 자동
폴백하게 만들면 안전하다. (실증: SynoSmartInfo →
`PeterSuh-Q3/SynoSmartInfo` 릴리즈 `TOOLCHAIN`, 포크
`PeterSuh-Q3/synology-package-builder`.) DSM 커널 빌드(x86_64-GPL의
`.github/workflows/*.yml`, `epyc7002`/`geminilakenk`/`r1000nk`/
`v1000nk` 툴체인 다운로드)도 같은 클래스의 문제를 겪을 가능성이
높으므로 동일 패턴 적용을 검토할 것.

## 8. 검증 원칙

CI 그린 ≠ 설치 성공. 이번에 CI에서는 한 번도 안 걸렸던 버그 5개
(289/313/268/276/319)가 전부 실기기 `synopkg install`에서만
드러났다. 패키지 구조를 바꾸는 변경(특히 `conf/privilege`,
`package.json`의 설치 관련 필드)은 **반드시 실제 DSM에
설치·기동·반복 요청까지** 해보고 나서 완료로 간주할 것.
