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
#include <sys/stat.h>
#include <errno.h>

/* Overridable at compile time (-DTARGET_SCRIPT='"/path"') for testing only;
 * production builds always use the real script path below. */
#ifndef TARGET_SCRIPT
#define TARGET_SCRIPT "/var/packages/Synosmartinfo/target/bin/syno_smart_info.sh"
#endif

#ifndef BIN_DIR
#define BIN_DIR "/var/packages/Synosmartinfo/target/bin"
#endif
#define HELPER_DIR BIN_DIR "/helper"

/*
 * conf/privilege's "tool" section only accepts file relpaths, not
 * directories (confirmed empirically: directory entries make DSM's
 * installer fail with error 313). So the containing directories stay
 * owned by the non-root service account, which can delete+recreate
 * syno_smart_info.sh with attacker content despite the file itself
 * being root-owned/read-only - POSIX delete/recreate is governed by
 * the parent directory's write bit, not the target file's own mode.
 * Since this helper already holds root (via setuid) on every
 * invocation, it re-locks the directories here instead: best-effort,
 * never blocks the actual SMART check on failure.
 */
static void heal_dir(const char *path)
{
    struct stat st;
    if (stat(path, &st) != 0) return;

    if (st.st_uid != 0) {
        if (chown(path, 0, st.st_gid) != 0) {
            fprintf(stderr, "smartinfo-helper: chown %s failed: %s\n", path, strerror(errno));
        }
    }

    mode_t safe_mode = st.st_mode & ~(S_IWGRP | S_IWOTH);
    if ((st.st_mode & 07777) != (safe_mode & 07777)) {
        if (chmod(path, safe_mode & 07777) != 0) {
            fprintf(stderr, "smartinfo-helper: chmod %s failed: %s\n", path, strerror(errno));
        }
    }
}

int main(int argc, char *argv[])
{
    /* Must match syno_smart_info.sh's actual accepted options exactly;
     * "-i" was never a real option upstream and always failed.
     * "selfheal" is not a script option at all - it's caught below,
     * before exec, and only re-locks BIN_DIR/HELPER_DIR then exits.
     * postinst/postupgrade call this once, immediately after install,
     * to close the window between "package installed" and "a real
     * SMART check first runs" during which bin/ is still owned by the
     * service account (conf/privilege can't chown directories - see
     * heal_dir()'s comment) and a compromised service-account process
     * could delete+recreate syno_smart_info.sh before heal_dir() ever
     * gets a chance to run. Reported by 007revad, issue #21. */
    const char *allowed[] = { "", "-a", "-v", "-h", "selfheal", NULL };
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

    /* Self-heal directory ownership before doing anything else with
     * our newly-acquired root. See heal_dir()'s comment for why. */
    heal_dir(BIN_DIR);
    heal_dir(HELPER_DIR);

    if (strcmp(opt, "selfheal") == 0) {
        return 0;
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
