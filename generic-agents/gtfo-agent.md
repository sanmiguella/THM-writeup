# GTFOBins Agent Instructions

`gtfo` is the local CLI for the GTFOBins database (461 Unix binaries). Use it to look up privilege escalation, shell spawning, file read/write, SUID/sudo abuse, and reverse shell techniques. It works offline, reads fast, and outputs ready-to-use bash.

---

## Command Reference

```bash
gtfo <binary>                    # All techniques for a binary
gtfo <binary> -f <type>          # Filter to one technique type
gtfo -s <partial>                # Fuzzy search by name
gtfo -s <partial> -f <type>      # Fuzzy search + filter
gtfo -l                          # List all 461 binaries
gtfo -l -f <type>                # List all binaries with a specific technique
gtfo -i                          # Interactive mode with tab-complete
```

### Technique Types (`-f` values)

| Type | When to use |
|------|-------------|
| `shell` | Spawn interactive shell from restricted context |
| `command` | Execute arbitrary OS commands |
| `sudo` | Binary is in sudoers — look up the escape |
| `suid` | Binary has SUID bit set |
| `limited-suid` | SUID but restricted (e.g., drops privs in some cases) |
| `capabilities` | Binary has Linux capabilities (e.g., `cap_setuid`) |
| `reverse-shell` | Interactive reverse shell |
| `non-interactive-reverse-shell` | Non-interactive reverse shell (useful when tty is unavailable) |
| `bind-shell` | Bind shell listener on target |
| `non-interactive-bind-shell` | Non-interactive bind shell |
| `file-read` | Read arbitrary files |
| `file-write` | Write arbitrary files |
| `file-upload` | Exfiltrate files |
| `file-download` | Pull files to target |
| `library-load` | Load a shared library (`.so`) — useful for privesc via LD_PRELOAD paths |

---

## How to Use It

**Start with the unfiltered lookup.** `gtfo <binary>` shows everything — don't pre-filter until you know what context you're working in.

```bash
gtfo python3
```

**Once you know the scenario, filter.** If `python3` is in sudoers:
```bash
gtfo python3 -f sudo
```

If it has the SUID bit:
```bash
gtfo python3 -f suid
```

**For capability abuse**, first confirm with `getcap`:
```bash
getcap -r / 2>/dev/null
# if you see python3 = cap_setuid+ep → gtfo python3 -f capabilities
```

**Don't know the exact binary name?** Fuzzy search it:
```bash
gtfo -s perl        # matches perl, perl5, etc.
gtfo -s ruby -f sudo
```

**Discovering what's exploitable on a box:**
```bash
# cross-reference sudo -l output against:
gtfo -l -f sudo

# cross-reference find / -perm -4000 output against:
gtfo -l -f suid
```

---

## Reading the Output

Output is sectioned by technique type:

```
---------- [ SUDO ] ----------
sudo python3 -c 'import os; os.system("/bin/sh")'
```

**Placeholders to substitute:**

| Placeholder | Meaning |
|-------------|---------|
| `$RHOST` | Attacker IP |
| `$RPORT` | Listener port on attacker |
| `$LFILE` | Target file path (for read/write) |
| `$LPORT` | Local port (bind shells) |

Some techniques have a comment block above the code describing prerequisites — read it. For reverse shells it often tells you what to run on the attacker side first (e.g., `socat`, `nc`).

---

## Workflow Integration

### Privilege Escalation Checklist

1. Run `sudo -l` → any binaries listed? → `gtfo <binary> -f sudo`
2. Run `find / -perm -4000 -type f 2>/dev/null` → SUID binaries? → `gtfo <binary> -f suid`
3. Run `getcap -r / 2>/dev/null` → capabilities? → `gtfo <binary> -f capabilities`
4. Writable path with a known binary? → `gtfo <binary> -f file-write`

### Shell Escaping (restricted shell / rbash / lshell)

```bash
gtfo <binary> -f shell
```

Common escapes: `vi`, `vim`, `less`, `man`, `awk`, `find`, `nmap` (older versions), `python`, `perl`, `ruby`, `lua`, `gcc`.

### File Read Without Cat

If `cat` is blocked or you need to avoid leaving obvious logs:
```bash
gtfo -l -f file-read    # see what's available
gtfo less -f file-read
gtfo tee -f file-read
```

### File Write for Privesc

Writing to `/etc/passwd`, cron files, or writable sudoers:
```bash
gtfo tee -f file-write
gtfo dd -f file-write
```

---

## Tips

- Output is display-only — `gtfo` shows techniques, it doesn't execute them.
- Code is bash. On targets with only `/bin/sh`, drop bash-specific syntax (`$()`, `[[ ]]`).
- Multiple techniques for the same type are separated by dashes — try them in order; some require specific binary versions.
- For reverse shells, `gtfo` shows attacker-side setup in comments. Don't skip that part.
- When a technique uses `import pty` or similar — that's for shell stabilization, not the exploit itself.
