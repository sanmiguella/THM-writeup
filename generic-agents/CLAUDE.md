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
2. Read `USER-CONFIG.md` to load user-specific settings (GitHub repo URL, SecLists path).
3. Read `coordinator-agent.md` and follow its session-start protocol (includes hexstrike_mcp availability check).
   - If `ctf-commands-agent.md` is being invoked, it must read `USER-CONFIG.md` for `COMMANDS_RAW_URL`, then fetch that URL via WebFetch before answering any question.
4. If `box-state.md` does not exist, create it immediately once a target is provided — do not wait for an agent to complete.
5. If `progress.md` does not exist, create it at the same time as `box-state.md`.

---

## What This Project Is

A multi-agent CTF/penetration-testing framework for TryHackMe. Each `.md` file is a specialized agent prompt. The coordinator routes tasks to sub-agents; sub-agents execute immediately without confirmation.

## Agent Roster and Triggers

**Routing priority:** When `hexstrike_mcp` is available (`MCP_Available=true`), the coordinator routes recon, web enum, privesc, cracking, web vuln scanning, stego, forensics, and OSINT tasks to `hexstrike-agent.md` first. Specialized fallback agents are used only when MCP is down.

| File | Triggers |
|------|---------|
| `coordinator-agent.md` | Entry point — reads `box-state.md`, routes, updates state |
| `hexstrike-agent.md` | **PRIMARY when MCP up** — IP/hostname, URL, "shell"+OS, hash/crack, web vuln, stego, forensics, OSINT, binary RE; "hexstrike", "MCP", checksec/ghidra/radare2/angr/rop/gdb, volatility, shodan/sherlock, autorecon — hexstrike_server at localhost:8888 |
| `recon-agent.md` | **Fallback (MCP down)** — IP or hostname given |
| `ffuf-agent.md` | **Fallback (MCP down)** — URL / web port discovered |
| `linprivesc-agent.md` | **Fallback (MCP down)** — "shell" + Linux context |
| `winprivesc-agent.md` | **Fallback (MCP down)** — "shell" + Windows context |
| `cracking-agent.md` | **Fallback (MCP down)** — Hash string, "crack", credential file |
| `owasp-top-10-agent.md` | **Fallback (MCP down)** or chained after hexstrike for deep bypass analysis |
| `brainstorm-agent.md` | Recon dump, "what next", "stuck" — always available regardless of MCP |
| `payload-agent.md` | LHOST + LPORT, reverse/web shell requested — always (hexstrike doesn't generate payloads) |
| `exploit-scripting-agent.md` | CVE ID, exploit description, "write an exploit" — always (hexstrike doesn't write Python exploits) |
| `gtfo-agent.md` | Binary name + privilege-escalation context — always (hexstrike doesn't have GTFOBins) |
| `searchsploit-agent.md` | Service/version needing exploit search — always (hexstrike doesn't have searchsploit) |
| `ctf-commands-agent.md` | "command for", "how do I", technique needing exact syntax — reads `USER-CONFIG.md` for URL, then fetches live COMMANDS.md on every init |
| `THM-WRITEUP-AGENT.md` | "writeup", box completion |

## Session State Files (created at runtime)

- `box-state.md` — coordinator state: target, OS, ports, shell user, dead ends, pending action
- `progress.md` — timestamped log of every agent run and findings
- `findings.md` — hexstrike-agent MCP findings; read alongside `box-state.md` when hexstrike is active
- `logged-commands.md` — auto-generated audit log of all Bash commands run (hook-managed)

## Key Symlinks

| Symlink | Points to (default) |
|---------|---------------------|
| `hosts` | `/etc/hosts` |
| `DNS/` | `~/SecLists/Discovery/DNS/` |
| `Passwords/` | `~/SecLists/Passwords/` |
| `Usernames/` | `~/SecLists/Usernames/` |
| `Web-Content/` | `~/SecLists/Discovery/Web-Content/` |

Set your actual SecLists path in `USER-CONFIG.md` and run the symlink commands listed there.

## Automatic Agent Chains

1. **IP given** → IF MCP up: hexstrike (rustscan→nmap→autorecon+web enum) → brainstorm; ELSE: recon → brainstorm → ffuf (if web ports found)
2. **URL given** → IF MCP up: hexstrike (feroxbuster+nuclei+nikto); ELSE: ffuf
3. **"got a shell"** → ask OS → payload; THEN IF MCP up: hexstrike (linpeas/winpeas via 8080) → brainstorm; ELSE: matching privesc agent
4. **Hash / crack** → IF MCP up: hexstrike (hash_identifier→hashcat/john via MCP); ELSE: cracking-agent
5. **CVE + target** → exploit-scripting → payload generation
6. **"stuck" / dead end** → brainstorm → recommend next agent
7. **"writeup"** → THM-WRITEUP-AGENT → standards compliance check → COMMANDS.md audit → update repo README → git push
8. **Binary / OSINT / forensics / stego** → IF MCP up: hexstrike → brainstorm (if paths ambiguous); ELSE: ctf-commands-agent for syntax

## Design Rules

- **No confirmation prompts** — all agents execute on trigger.
- **One clarifying question max** — only when input is genuinely ambiguous.
- **Exploit scripts are Python 3 only.**
- **Hashcat GPU flag** — always `-D 2` (Metal backend).
- **Output sections** — use labelled blocks (`[QUICK WINS]`, `[ATTACK PATHS]`, `[NEXT STEPS]`).
- **hexstrike first** — when hexstrike_mcp is reachable, it handles recon, web enum, privesc, cracking, web vulns, stego, forensics, and OSINT. Specialized agents are fallbacks only.
- **hexstrike fallback** — if hexstrike_mcp is unreachable (MCP_Available=false), route to the equivalent specialized agent. If hexstrike fails mid-session, update MCP_Available=false and re-route immediately.
- **Port 8888 is hexstrike_server** — never use 8888 for http.server or any other listener. Use 8080 instead.
- **No disclaimers** — do not add a disclaimer section to any room writeup. A site-wide disclaimer already exists in the repo-level README.md.

## Extending the Framework

1. Follow: **Role → Trigger → Workflow → Output Format → Rules**.
2. Register trigger keywords in `coordinator-agent.md` (registry table + routing tree).
3. Add a row to the Agent Roster above.
