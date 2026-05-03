# User Configuration

Edit this file once before your first session. All agents that need GitHub or wordlist paths read it automatically.

---

## GitHub Writeup Repository

Replace `YOUR_GITHUB_USERNAME` with your GitHub username. Fork or create a repo named `THM-writeup` (or rename the variables to match your repo name).

```
WRITEUP_REPO_URL:     https://github.com/YOUR_GITHUB_USERNAME/THM-writeup
COMMANDS_RAW_URL:     https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/THM-writeup/main/COMMANDS.md
```

---

## SecLists Path

Set this to wherever SecLists is installed on your machine.

Common locations:
- Kali / ParrotOS (apt install): `/usr/share/seclists`
- Manual clone to home: `~/SecLists`

```
SECLISTS_PATH:    ~/SecLists
```

Update the symlinks in your working directory to match:

```bash
ln -sf ~/SecLists/Discovery/DNS/               DNS
ln -sf ~/SecLists/Passwords/                   Passwords
ln -sf ~/SecLists/Usernames/                   Usernames
ln -sf ~/SecLists/Discovery/Web-Content/       Web-Content
ln -sf /etc/hosts                              hosts
```

---

## Quick-Start Checklist

- [ ] Replace `YOUR_GITHUB_USERNAME` above with your actual GitHub username
- [ ] Confirm SecLists path is correct for your system
- [ ] Run the symlink commands above from your working directory
- [ ] (Optional) Create a `COMMANDS.md` in your repo — agents will fetch it live and add new techniques as you complete rooms
