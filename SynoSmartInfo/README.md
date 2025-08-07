<!-- @format -->

[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/PeterSuh-Q3)
[![GitHub release](https://img.shields.io/github/release/PeterSuh-Q3/synology-package-builder?include_prereleases=&sort=semver&color=blue)](https://github.com/tomgrv/synology-package-builder/releases/)
[![License](https://img.shields.io/badge/License-MIT-blue)](#license)
[![issues - synology-package-builder](https://img.shields.io/github/issues/tomgrv/synology-package-builder)](https://github.com/tomgrv/synology-package-builder/issues)

# < Caution >

Synosmartinfo synology user must be granted the authority to process with sudoers.

Check if the file already exists with the command below, and if not,

sudores processing as below is absolutely necessary.

```
sudo -i
ll /etc/sudoers.d/Synosmartinfo
```

```
sudo -i
echo "synosmartinfo ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/Synosmartinfo
chmod 0440 /etc/sudoers.d/Synosmartinfo
```

## License

This repository is licensed under the [MIT License](LICENSE).

This work is not affiliated with Synology Inc. in any way. It is an independent project. It is not an official Synology product and does not have any official support from Synology Inc. Use at your own risk.
