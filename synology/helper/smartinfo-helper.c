/*
 * smartinfo-helper.c
 *
 * Narrow setuid-root launcher for SynoSmartInfo.
 * Installed with owner root:root, mode 6755 (setuid) by postinst,
 * which itself always runs as root during DSM package install.
 *
 * This replaces the sudoers-based escalation: it does not depend on
 * /usr/bin/sudo being present, and only ever executes one fixed,
 * hardcoded script path with a whitelisted, single argument.
 */

#define _GNU_SOURCE
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* Overridable at compile time (-DTARGET_SCRIPT='"/path"') for testing only;
 * production builds always use the real script path below. */
#ifndef TARGET_SCRIPT
#define TARGET_SCRIPT "/var/packages/Synosmartinfo/target/bin/syno_smart_info.sh"
#endif

int main(int argc, char *argv[])
{
    const char *allowed[] = { "", "-a", "-i", "-v", "-h", NULL };
    const char *opt = (argc >= 2) ? argv[1] : "";

    if (argc > 2) {
        fprintf(stderr, "smartinfo-helper: too many arguments\n");
        return 1;
    }

    int ok = 0;
    for (int i = 0; allowed[i] != NULL; i++) {
        if (strcmp(opt, allowed[i]) == 0) { ok = 1; break; }
    }
    if (!ok) {
        fprintf(stderr, "smartinfo-helper: rejected option '%s'\n", opt);
        return 1;
    }

    /* setuid binary gives us euid=0; promote ruid too so the exec'd
     * script is genuinely root, not just effectively root. */
    if (setuid(0) != 0) {
        perror("smartinfo-helper: setuid(0) failed");
        return 1;
    }

    /* Sanitize environment: fixed PATH, no inherited surprises. */
    if (clearenv() != 0) {
        fprintf(stderr, "smartinfo-helper: clearenv failed\n");
        return 1;
    }
    setenv("PATH", "/usr/bin:/bin:/usr/sbin:/sbin:/usr/syno/bin:/usr/syno/sbin", 1);
    setenv("HOME", "/root", 1);

    if (opt[0] == '\0') {
        execl(TARGET_SCRIPT, TARGET_SCRIPT, (char *)NULL);
    } else {
        execl(TARGET_SCRIPT, TARGET_SCRIPT, opt, (char *)NULL);
    }

    perror("smartinfo-helper: execl failed");
    return 1;
}
