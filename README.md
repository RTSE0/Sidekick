<h1 align="center">🦸 SIDEKICK</h1>

<h3 align="center"> A self-hosted autonomous AI agent. Give it a soul, give it tools, and let it rip.</h3>


Sidekick is a local AI agent that lives in your Discord. It can read and write files, run shell commands, search the web, remember your conversations, and check in on you proactively in the background. 
All powered by a local LLM running on your machine via Ollama. No cloud. No subscriptions. Just you and your machine, alone at last. 😉

Inspired by <a href="https://github.com/openClaw">OpenClaw</a>.

---

## ✨ Features

- **Soul System** — On first run, Sidekick interviews you to build its own identity: name, personality, purpose, and tasks for heartbeat. It becomes whoever you want it to be.
- **Persistent Memory** — Remembers every conversation across sessions, per channel and per DM.
- **ReAct Tool Loop** — Reasons about tasks and executes tools step by step, feeding results back to itself until the job is done.
- **Proactive Heartbeat** — Runs in the background every 30 seconds. Checks in on you more than my parents have, sends reminders, and monitors your system — all via Discord DM.
- **Local & Private** — Everything runs on your machine. Your data never leaves.
- **Extensible Skills** — Add new tools to `skills.py` and the agent can use them immediately.
- **🦆 Rubber Duck Debugger** — Activates a Socratic debug mode that asks questions instead of giving answers. Guided by your agent's personality. Saves a summary of every session.
- **🗒️ Conversational Checklist Editor** — Add or replace heartbeat tasks through a guided conversation. No commands to memorize.
- **📋 Clipboard Sentinel** — Reads your clipboard on demand and injects the content directly into the conversation. Useful for pasting tracebacks or code for analysis.

### Built-in Skills
| Skill | Description |
|---|---|
| `read_file` | Reads any local text file |
| `create_file` | Creates or overwrites a file with specified content |
| `run_command` | Executes Windows shell commands |
| `web_search` | Searches the live web via DuckDuckGo |

## 🛠️ Prerequisites
 
- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- A Discord bot token ([guide](https://discord.com/developers/applications))
- A GPU with at least 8GB VRAM recommended (tested on RTX 5070)

<sup>*note, if you have 3.10+ pythons in your house, you should stop reading this and run</sub>
### Recommended Models
| Model | VRAM | Notes |
|---|---|---|
| `qwen2.5:14b` | ~10GB | Best balance of speed and instruction following |
| `llama3.1:8b` | ~6GB | Lighter option, less reliable for tool use |

### System Recommendations 
- **PROCESSOR:** AMD Ryzen 5 7600
- **MEMORY:** 32 GB RAM
- **GRAPHICS:** RTX 5070
- **STORAGE:** 1 TB of available space\
<sub>*Just kidding, I have no idea what the minimum recommendation is, I just wanted to show my system off. 😉</sub>

## 🚀 Setup
 
### 1. Clone the repo
```bash
git clone https://github.com/RTSE0/sidekick.git
cd sidekick
```
### 2. Install dependencies
```bash
pip install -r requirements.txt
```
 
### 3. Pull your model
```bash
ollama pull qwen2.5:14b
```
 
### 4. Configure your environment
Copy the example env file and fill in your values:
```bash
# Windows
copy .env.example .env
# Mac/Linux
cp .env.example .env
```

Open `.env` and set:
```
DISCORD_TOKEN=your_discord_bot_token_here
USER_ID=your_discord_user_id_here
OLLAMA_API_URL=http://127.0.0.1:11434/api/chat
TARGET_MODEL=qwen2.5:14b
```
**How to get your User ID:** In Discord, go to Settings → Advanced → enable Developer Mode. Then right-click your username and click "Copy User ID."
 
### 5. Start Ollama
Run `ollama serve` in a separate terminal window. If you get a port error, Ollama is already running in the background — you're good to go.
 
### 6. Run Sidekick
```bash
python bot.py
```
 
---
## 🎭 First Run — The Soul Interview
 
On first launch with no `soul.json`, Sidekick will prompt you to set up its identity via Discord. Just mention it or DM it to begin:
 
> **You:** Hello!
>
> **Sidekick:** I don't have a name yet. Let's fix that. What would you like to call me?
 
Answer its questions about name, tone, purpose, and what you want it to monitor in the background. When you're happy, tell it you're done — it'll generate its identity config and `HEARTBEAT.md` automatically and come online.
 
To reset and start a fresh identity, delete `soul.json` and `agent_memory.json`.
 
---
 
## 💬 Usage
 
**Mention it in a server channel:**
```
@Sidekick search the web for the latest AI news
@Sidekick create a file called notes.txt that says "remember to ship"
@Sidekick list the files in C:\Users\me\Documents

✨NEW

### 🦆 Rubber Duck Debug Mode
Say `debug mode` to activate. Sidekick switches into a Socratic mode — it asks questions instead of giving answers, guiding you to find the bug yourself. When you're done, say `exit debug` and it summarizes what you discovered.

### 🗒️ Update Your Checklist
Say `update checklist` and Sidekick will ask whether you want to **add** tasks or **replace** the whole list. Then just type your tasks one per line.

### 📋 Clipboard Sentinel
Say anything with the word **clipboard** in it and Sidekick will read your current clipboard and inject it into the conversation. Useful for sharing error messages or code without manually pasting.
```
 
**Or DM it directly** — no mention needed in DMs.
 
**The heartbeat** runs every 30 seconds in the background and will DM you based on your configured checklist. It skips automatically if you've been active in the last 5 minutes.
 
---
## 📁 Project Structure
 
```
sidekick/
├── bot.py              # Main agent runtime and Discord gateway
├── skills.py           # Tool definitions (add new skills here)
├── Memory.py           # Persistent conversation history
├── config.py           # Soul config load/save
├── .env                # Your secrets (never committed)
├── .env.example        # Template for new users
├── soul.json           # Generated identity config (never committed)
├── agent_memory.json         # Conversation history (never committed)
└── HEARTBEAT.md        # Generated background task checklist
```
 
---
 
## ➕ Adding New Skills
 
Open `skills.py` and add a new function:
 
```python
def skill_your_tool(arguments):
    value = arguments.get("your_arg") or ""
    # do something
    return "result string"
```
 
Then register it in `Skills_sys`:
```python
Skills_sys = {
    ...
    "your_tool": skill_your_tool
}
```
 
Finally, add it to the tools list in `build_runtime_prompt()` in `bot.py` so the agent knows it exists.
 
---
 
## ⚠️ Security Notes
 
- Sidekick can run shell commands on your machine. Only run it on hardware you trust and control.
- Never share your `.env` file or commit it to GitHub.
- The `run_command` skill has a basic blocklist for destructive commands but is not a full sandbox. Use with care.
---
 
## 📋 Requirements
 
```
discord.py>=2.3.0
aiohttp>=3.9.0
python-dotenv>=1.0.0
ddgs>=9.0.0
```
 
---
 
## 📄 License
 
MIT — do whatever you want with it, I don't care. I really don't...really.
 
---
 
*Built with Python, Ollama, and way too much time debugging JSON parsing.*
