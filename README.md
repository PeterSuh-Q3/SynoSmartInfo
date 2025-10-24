<!-- @format -->

[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/PeterSuh-Q3)
[![GitHub release](https://img.shields.io/github/release/PeterSuh-Q3/SynoSmartInfo?include_prereleases=&sort=semver&color=blue)](https://github.com/PeterSuh-Q3/SynoSmartInfo/releases/)
[![License](https://img.shields.io/badge/License-MIT-blue)](#license)
[![issues - SynoSmartInfo](https://img.shields.io/github/issues/PeterSuh-Q3/SynoSmartInfo)](https://github.com/PeterSuh-Q3/SynoSmartInfo/issues)

[Introduction and detailed explanation of Syno Smart Info]
https://www.reddit.com/r/synology/comments/1mgi44b/introducing_synology_custom_package_syno_smart/

# < Caution >

Synosmartinfo synology user must be granted the authority to process with sudoers.

Check if the file already exists with the command below, and if not,

sudoers processing as below is absolutely necessary.

```
sudo -i
ll /etc/sudoers.d/Synosmartinfo
```

```
sudo -i
echo "synosmartinfo ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/Synosmartinfo
chmod 0440 /etc/sudoers.d/Synosmartinfo
```

<img width="640" height="358" alt="introducing-synology-custom-package-syno-smart-info-v0-8kct095tw5hf1" src="https://github.com/user-attachments/assets/f3134377-c274-45f7-a8af-2a6a062701e8" />

<img width="1257" height="612" alt="스크린샷 2025-10-25 오전 12 17 34" src="https://github.com/user-attachments/assets/1bc92481-41f8-47dd-8bcb-1d876a0b1677" />

<img width="640" height="986" alt="introducing-synology-custom-package-syno-smart-info-v0-44mjssa6x5hf1" src="https://github.com/user-attachments/assets/b1da273e-8118-4219-8148-795861aa7a9c" />

<img width="1080" height="982" alt="introducing-synology-custom-package-syno-smart-info-v0-owm8qcbww5hf1" src="https://github.com/user-attachments/assets/cbcb34e9-a359-48fc-ac37-7dd2a2f2c2f3" />

## License

This repository is licensed under the [MIT License](LICENSE).

This work is not affiliated with Synology Inc. in any way. It is an independent project. It is not an official Synology product and does not have any official support from Synology Inc. Use at your own risk.
