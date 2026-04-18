# 🗒️ Hacking Notes — Command Reference

Personal cheatsheet of commonly used commands across recon, enumeration, exploitation, and post-exploitation.

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

medusa
```bash
medusa -h <ip> -u admin -P ./Passwords/Common-Credentials/10k-most-common.txt -M http -m DIR:/ -v 6
```

Previous targets
```bash
hydra -l admin -P ./Passwords/Common-Credentials/10k-most-common.txt broadcast.vulnnet.thm http-get / -v
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
