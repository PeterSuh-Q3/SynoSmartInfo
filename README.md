<!-- @format -->

[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/PeterSuh-Q3)
[![GitHub release](https://img.shields.io/github/release/PeterSuh-Q3/SynoSmartInfo?include_prereleases=&sort=semver&color=blue)](https://github.com/PeterSuh-Q3/SynoSmartInfo/releases/)
[![License](https://img.shields.io/badge/License-MIT-blue)](#license)
[![issues - SynoSmartInfo](https://img.shields.io/github/issues/PeterSuh-Q3/SynoSmartInfo)](https://github.com/PeterSuh-Q3/SynoSmartInfo/issues)

[Introduction and detailed explanation of Syno Smart Info]
https://www.reddit.com/r/synology/comments/1mgi44b/introducing_synology_custom_package_syno_smart/

# < Another installation method instead of manually installing .spk >

Another installation method instead of manually installing the .spk

You can use 007revad's Synology package repository.

Add this URL to the package sources in the Package Center settings.

https://spkrepo.007daver.workers.dev/

<img width="887" height="373" alt="580502821-e7badc9e-8302-421e-88fc-c140b76c5f2e" src="https://github.com/user-attachments/assets/1e36a2b3-2aeb-4b39-a6ce-a82f5880197d" />

Installable package icons are available as shown below.

<img width="953" height="614" alt="580502718-67a0de6b-7a0d-493a-b859-79c1d244cdef" src="https://github.com/user-attachments/assets/48cdd566-0ce8-4e73-b0de-f4f1308e18d4" />

Thanks @007revad

# < Privileges >

**No manual setup is required.** Earlier versions asked you to hand-write a
`/etc/sudoers.d/Synosmartinfo` rule over SSH; that is no longer needed and the
package removes any leftover rule on install.

Reading S.M.A.R.T. data requires root, but the web UI itself runs as an
unprivileged service account (`sc-synosmartinfo`). Root is reached through a
small setuid helper that only ever executes `syno_smart_info.sh`, and only with
a whitelisted option (`-a`, `-i`, `-v`, `-h`, or none) — anything else is
rejected. DSM installs that helper as root-owned setuid itself, via the `tool`
section of `conf/privilege`:

```
-r-sr-s--- 1 root <package-group>  smartinfo-helper.x86_64
```

Mode `6550` means only members of the package group can execute it at all, so
this is considerably narrower than the blanket sudoers rule it replaces.

If the UI ever reports that privileges are missing, reinstalling the package is
the fix — that re-triggers DSM's setuid handling.

### Why this is better than the old sudoers rule

| | Old (sudoers) | New (privilege `tool` + setuid) |
|---|---|---|
| **Scope** | `synosmartinfo ALL=(ALL) NOPASSWD: ALL` — unlimited root, any command | One fixed binary only, and only whitelisted options (`-a`/`-i`/`-v`/`-h`/none) — everything else rejected |
| **Who can run it** | Anyone who can reach the sudoers rule | Mode `6550` — **only members of the package group** can execute it at all |
| **Dependencies** | Requires `/usr/bin/sudo` to be installed and its DSM config (secure_path, env_reset, ...) to behave as expected | None — the helper calls `execl()` on a fixed absolute path directly, no PATH lookup at all |
| **Environment exposure** | Whatever `sudo` forwards is out of the package's control | The helper calls `clearenv()` and sets a fixed `PATH`/`HOME` itself |
| **How it's installed** | postinst has to write to `/etc/sudoers.d/` itself, which requires postinst to run as root | DSM applies the setuid bit automatically at install time via `conf/privilege`'s `tool` section — **postinst never needs root at all** (verified on real hardware) |
| **User effort** | SSH in once and type commands by hand | Fully automatic, no manual step |
| **Leftovers** | `/etc/sudoers.d/Synosmartinfo` can linger system-wide across reinstalls | Lives only inside the package directory; removed with the package |

In short: instead of "let root run anything," it's now "let the package group run
one fixed script, with a few fixed options" — and the entity granting that
narrow privilege is DSM itself, not our own postinst script, so the old
chicken-and-egg problem of "postinst needs root to grant root" disappears too.

<img width="640" height="358" alt="introducing-synology-custom-package-syno-smart-info-v0-8kct095tw5hf1" src="https://github.com/user-attachments/assets/f3134377-c274-45f7-a8af-2a6a062701e8" />

<img width="1257" height="612" alt="스크린샷 2025-10-25 오전 12 17 34" src="https://github.com/user-attachments/assets/1bc92481-41f8-47dd-8bcb-1d876a0b1677" />

<img width="1462" height="892" alt="dsm-floating-window" src="https://github.com/user-attachments/assets/85ba9334-1d73-499b-962c-c5ad11bf1919" />

<img width="640" height="986" alt="introducing-synology-custom-package-syno-smart-info-v0-44mjssa6x5hf1" src="https://github.com/user-attachments/assets/b1da273e-8118-4219-8148-795861aa7a9c" />

<img width="1080" height="982" alt="introducing-synology-custom-package-syno-smart-info-v0-owm8qcbww5hf1" src="https://github.com/user-attachments/assets/cbcb34e9-a359-48fc-ac37-7dd2a2f2c2f3" />

<details>
<summary>🇰🇷 한국어 설명 (클릭하여 펼치기)</summary>

[Syno Smart Info 소개 및 상세 설명]
https://www.reddit.com/r/synology/comments/1mgi44b/introducing_synology_custom_package_syno_smart/

## < .spk 수동 설치 대신 사용할 수 있는 다른 설치 방법 >

.spk를 수동으로 설치하는 대신 007revad의 Synology 패키지 저장소를 사용할 수 있습니다.

패키지 센터 설정의 패키지 소스에 아래 URL을 추가하세요.

https://spkrepo.007daver.workers.dev/

설치 가능한 패키지 아이콘은 아래와 같이 표시됩니다.

@007revad 님께 감사드립니다.

## < 권한 설정 >

**별도의 수동 설정이 필요 없습니다.** 예전 버전에서는 SSH로 접속해서
`/etc/sudoers.d/Synosmartinfo` 규칙을 직접 작성해야 했지만, 이제는 필요
없으며 설치 시 남아있는 규칙도 패키지가 알아서 정리합니다.

S.M.A.R.T. 정보를 읽으려면 root 권한이 필요하지만, 웹 UI 자체는 권한 없는
서비스 계정(`sc-synosmartinfo`)으로 동작합니다. root 권한은 작은 setuid
헬퍼를 통해서만 얻는데, 이 헬퍼는 오직 `syno_smart_info.sh`만 실행하며 그마저도
화이트리스트에 있는 옵션(`-a`, `-i`, `-v`, `-h`, 또는 옵션 없음)만 허용하고
나머지는 전부 거부합니다. 이 헬퍼에 root 소유 setuid를 부여하는 것도 DSM이
`conf/privilege`의 `tool` 섹션을 통해 직접 처리합니다.

```
-r-sr-s--- 1 root <package-group>  smartinfo-helper.x86_64
```

모드 `6550`은 패키지 그룹 구성원만 실행할 수 있다는 뜻이라, 이전에 쓰던
전면 허용 sudoers 규칙보다 훨씬 좁은 권한입니다.

만약 UI에서 권한이 없다는 메시지가 뜬다면, 패키지를 재설치하면 됩니다 —
그러면 DSM의 setuid 처리가 다시 트리거됩니다.

### 기존 sudoers 방식보다 좋아진 점

| | 기존 (sudoers) | 새 방식 (privilege `tool` + setuid) |
|---|---|---|
| **권한 범위** | `synosmartinfo ALL=(ALL) NOPASSWD: ALL` — 사실상 전체 명령을 root로 무제한 허용 | 딱 하나의 헬퍼 바이너리만, 그마저도 화이트리스트 옵션(`-a`/`-i`/`-v`/`-h`/없음) 외엔 거부 |
| **실행 주체 제한** | `sudoers.d` 파일에 접근 가능한 사람 누구나 | 파일모드 `6550` → **패키지 그룹 구성원만** 실행 가능 |
| **의존성** | `/usr/bin/sudo` 바이너리와 DSM의 sudo 설정(secure_path, env_reset 등)에 의존 | 외부 바이너리 의존 없음. `execl()`로 절대경로 직접 실행, PATH 탐색조차 없음 |
| **환경변수 노출면** | sudo가 어떤 환경변수를 넘기는지 패키지가 통제 못 함 | 헬퍼 자체가 `clearenv()` 후 고정 `PATH`/`HOME`만 세팅 — 우리가 직접 통제 |
| **설치 방식** | postinst가 직접 `/etc/sudoers.d/`에 파일을 써야 해서 **root 권한이 있는 postinst**가 전제 | DSM이 설치 시점에 자동으로 setuid를 부여 — **postinst는 root일 필요 자체가 없음**(실기기 테스트로 확인) |
| **사용자 개입** | 최초 1회 SSH 접속 → 명령어 직접 타이핑 필요 | 설치 즉시 자동 완료, 수동 설정 전혀 불필요 |
| **잔재 관리** | 재설치를 거듭해도 `/etc/sudoers.d/Synosmartinfo`가 시스템 전역에 남을 수 있음 | 패키지 디렉터리 안에만 존재, 패키지 삭제 시 함께 정리됨 |

한 줄로 요약하면: **"root로 뭐든 하게 허용"에서 "미리 정해둔 스크립트를, 미리
정해둔 몇 개 옵션으로만, 패키지 그룹만" 실행하게 좁힌 것**이고, 그 좁힌 권한을
부여하는 주체도 우리 postinst 스크립트가 아니라 DSM 자신이라 "root 권한을
확보하려면 root 권한이 필요하다"는 부트스트래핑 문제 자체가 사라졌습니다.

</details>

## Troubleshooting

### `error 313: failed to revise file attributes`, coming from a v1.4.2 or v2.0.0–v2.0.4 install

If this device ever had **v1.4.2, or v2.0.0 through v2.0.4**, installed —
even if it's fully uninstalled now — DSM permanently keeps the OS-level
service account those versions used, and its mere presence blocks *any*
future install/upgrade of this package, fresh installs included. This
cannot be fixed by the package itself: the conflict is enforced by DSM's
installer before any package script (`preinst` included) ever runs, and
package scripts have no permission to touch these accounts even when they
do run (they execute as the package's own unprivileged service account,
and `synouser`/`synogroup` are root-only, mode `0700`).

**Fix — SSH in and run, as root, before installing:**

```bash
sudo synouser --del sc-synosmartinfo
sudo synogroup --del synosmartinfo
```

Then install/upgrade normally. This is safe: v2.0.5+ no longer uses either
name, and it won't affect any other package's accounts.

### `error 313: failed to revise file attributes` — v1.4.2 또는 v2.0.0~v2.0.4 설치 이력이 있는 경우

이 장비에 **v1.4.2 또는 v2.0.0~v2.0.4가 한 번이라도 설치된 적**이 있다면 —
지금은 완전히 삭제된 상태라 해도 — DSM은 그 버전들이 쓰던 OS 레벨 서비스 계정을
영구적으로 남겨두고, 이 계정이 존재하는 것만으로 이후의 모든 설치/업그레이드가
막힙니다(신규 설치 포함). 패키지 자체로는 해결할 수 없습니다: 이 충돌은 패키지
스크립트(`preinst` 포함)가 실행되기도 전에 DSM 설치기 내부에서 강제되고, 설령
스크립트가 실행되더라도 패키지 자체의 권한 없는 서비스 계정으로 실행되기 때문에
`synouser`/`synogroup`(root 전용, 모드 `0700`)을 호출할 권한 자체가 없습니다.

**해결 — 설치 전에 SSH로 접속해 root 권한으로 실행:**

```bash
sudo synouser --del sc-synosmartinfo
sudo synogroup --del synosmartinfo
```

이후 정상적으로 설치/업그레이드하면 됩니다. v2.0.5부터는 두 이름 모두 사용하지
않으므로 안전하며, 다른 패키지의 계정에는 영향을 주지 않습니다.

## License

This repository is licensed under the [MIT License](LICENSE).

This work is not affiliated with Synology Inc. in any way. It is an independent project. It is not an official Synology product and does not have any official support from Synology Inc. Use at your own risk.
