# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Bootstrap (Run Once Per Fresh Directory)

When starting a session in a directory where `.claude/settings.json` does not exist:

1. Create the `.claude/` directory if it is missing.
2. Write `.claude/settings.json` with the following content exactly:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 -c \"import sys,json,datetime; d=json.load(sys.stdin); cmd=d.get('tool_input',{}).get('command',''); ts=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'); open('logged-commands.md','a').write('### {}\\n\\n```bash\\n{}\\n```\\n\\n'.format(ts,cmd)) if cmd else None\""
          }
        ]
      }
    ]
  }
}
```

3. Create `logged-commands.md` with the header `# Command Log` if it does not already exist.
4. Confirm bootstrap is complete, then continue with the session start protocol below.

---

## Session Start (Required)

At the start of every session, before doing anything else:
1. Run the Bootstrap steps above if `.claude/settings.json` is missing.
2. Read `coordinator-agent.md` and follow its session-start protocol (includes hexstrike_mcp availability check).
   - If `ctf-commands-agent.md` is being invoked, it must fetch `https://raw.githubusercontent.com/sanmiguella/THM-writeup/main/COMMANDS.md` via WebFetch before answering any question.
3. If `box-state.md` does not exist, create it immediately once a target is provided — do not wait for an agent to complete.
4. If `progress.md` does not exist, create it at the same time as `box-state.md`.

---

## What This Project Is

A multi-agent CTF/penetration-testing framework for TryHackMe. Each `.md` file is a specialized agent prompt. The coordinator routes tasks to sub-agents; sub-agents execute immediately without confirmation.

## Agent Roster and Triggers

| File | Triggers |
|------|---------|
| `coordinator-agent.md` | Entry point — reads `box-state.md`, routes, updates state |
| `recon-agent.md` | IP or hostname given |
| `ffuf-agent.md` | URL / web port discovered |
| `brainstorm-agent.md` | Recon dump, "what next", "stuck" |
| `payload-agent.md` | LHOST + LPORT, reverse/web shell requested |
| `exploit-scripting-agent.md` | CVE ID, exploit description, "write an exploit" |
| `linprivesc-agent.md` | "shell" + Linux context |
| `winprivesc-agent.md` | "shell" + Windows context |
| `cracking-agent.md` | Hash string, "crack", credential file |
| `owasp-top-10-agent.md` | Web vulnerability class mentioned |
| `gtfo-agent.md` | Binary name + privilege-escalation context |
| `searchsploit-agent.md` | Service/version needing exploit search |
| `ctf-commands-agent.md` | "command for", "how do I", technique needing exact syntax — fetches live COMMANDS.md from GitHub on every init |
| `hexstrike-agent.md` | "hexstrike", "MCP", binary RE (checksec/ghidra/radare2/angr/rop/gdb), memory forensics (volatility), OSINT (shodan/sherlock), "autorecon", "comprehensive scan" — requires hexstrike_mcp at localhost:8888 |
| `THM-WRITEUP-AGENT.md` | "writeup", box completion |

## Session State Files (created at runtime)

- `box-state.md` — coordinator state: target, OS, ports, shell user, dead ends, pending action
- `progress.md` — timestamped log of every agent run and findings
- `findings.md` — hexstrike-agent MCP findings; read alongside `box-state.md` when hexstrike is active
- `logged-commands.md` — auto-generated audit log of all Bash commands run (hook-managed)

## Key Symlinks

Create these once in your working directory (adjust `SECLISTS` if installed elsewhere):

```bash
SECLISTS=~/SecLists   # Kali default: /usr/share/seclists
ln -s /etc/hosts hosts
ln -s $SECLISTS/Discovery/DNS DNS
ln -s $SECLISTS/Passwords Passwords
ln -s $SECLISTS/Usernames Usernames
ln -s $SECLISTS/Discovery/Web-Content Web-Content
```

| Symlink | Points to |
|---------|-----------|
| `hosts` | `/etc/hosts` |
| `DNS/` | `$SECLISTS/Discovery/DNS/` |
| `Passwords/` | `$SECLISTS/Passwords/` |
| `Usernames/` | `$SECLISTS/Usernames/` |
| `Web-Content/` | `$SECLISTS/Discovery/Web-Content/` |

## Automatic Agent Chains

1. **IP given** → recon → brainstorm → ffuf (if web ports found)
2. **"got a shell"** → ask OS → payload + matching privesc agent
3. **CVE + target** → exploit-scripting → payload generation
4. **"stuck" / dead end** → brainstorm → recommend next agent
5. **"writeup"** → THM-WRITEUP-AGENT → update repo README → git push
6. **Binary / OSINT / forensics** → hexstrike → brainstorm (if paths ambiguous)

## Design Rules

- **No confirmation prompts** — all agents execute on trigger.
- **One clarifying question max** — only when input is genuinely ambiguous.
- **Exploit scripts are Python 3 only.**
- **Hashcat GPU flag** — use `-D 2` on macOS (Metal backend); omit or use `-D 1` on Linux (CPU) unless an NVIDIA/AMD GPU is available.
- **Output sections** — use labelled blocks (`[QUICK WINS]`, `[ATTACK PATHS]`, `[NEXT STEPS]`).
- **hexstrike fallback** — if hexstrike_mcp is unreachable, route to the equivalent specialized agent.
- **No disclaimers** — do not add a disclaimer section to any room writeup. A site-wide disclaimer already exists in the repo-level README.md.

## Extending the Framework

1. Follow: **Role → Trigger → Workflow → Output Format → Rules**.
2. Register trigger keywords in `coordinator-agent.md` (registry table + routing tree).
3. Add a row to the Agent Roster above.
