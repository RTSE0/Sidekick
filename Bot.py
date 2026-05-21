import discord
import aiohttp
import json
import re
import asyncio
import time
import os


from discord.ext import tasks
from dotenv import load_dotenv
from Memory import load_memory, save_memory
from skills import Skills_sys
from config import load_agent_config, save_agent_config
from skills import get_local_clipboard

load_dotenv()

last_interaction_time = 0
debug_sessions = {}
checklist_sessions = {}
# States: None, "awaiting_mode", "awaiting_tasks_add", "awaiting_tasks_replace"

#load or generate agent core personality
agent_id = load_agent_config()

Bootstrap_prompt = (
    "You are an AI agent in the process of being initialized by your creator.\n"
    "You currently do not have a name, personality, or specific purpose.\n"
    "Your task is to converse with the user in the terminal to discover who they want you to be.\n"
    "Ask questions about your name, your tone (e.g., deadpan comedy, professional coder), your goals, "
    "and what kinds of things they want you to proactively monitor or remind them about in the background.\n\n"
    "CRITICAL: Once the user says they are satisfied with your setup, you must stop chatting "
    "and output a raw JSON block matching this exact format:\n"
    "{\n"
    '  "initialized": true,\n'
    '  "name": "Chosen Name",\n'
    '  "tone": "Chosen Tone Description",\n'
    '  "purpose": "Primary Directive/Goals",\n'
    '  "heartbeat_tasks": ["task 1", "task 2", "task 3"]\n'
    "}\n"
    "Do not say anything else after or before the JSON once you decide to output it."
)


if not agent_id:
    print("=== INITIALIZATION PHASE ===")
    print("No agent config found. Let's build agent identity.\n")

    bootstrap_history = [{"role": "system", "content": Bootstrap_prompt}]

def build_runtime_prompt(id):
    #construct operation ReAct system prompt using the generated config.
    return(
        f"You are {id['name']}, an autonomous local AI agent operating via Discord.\n"
        f"Your primary mission and objective is: {id['purpose']}\n"
        f"Your conversational tone, attitude, and style must be: {id['tone']}\n\n"
        
        "CRITICAL OPERATIONAL RULES FOR TOOLS:\n"
        "1. You have access to local tools on the host machine.\n"
        "2. If you need to perform an action (like listing files or reading files), you MUST output a raw JSON block. "
        "Do NOT write any conversational text, explanations, or markdown code blocks (do NOT use ```json). "
        "Start your response with the open curly brace '{' immediately.\n"
        "3. Most messages are casual conversation and require NO tools whatsoever. "
        "Only use tools when the user EXPLICITLY asks you to read a file, run a command, or perform a system action. "
        "If someone is just chatting, respond conversationally like a normal assistant. "
        "Do NOT invent reasons to use tools during small talk.\n\n"
        
        "The JSON block must match this exact format structure:\n"
        '{\n  "action": "TOOL_NAME",\n  "arguments": { "ARG_NAME": "VALUE" }\n}\n\n'
        
        "Available Tools:\n"
        "- 'read_file': Reads local text files. Arguments: {'path': 'string'}\n"
        "- 'create_file': Creates a new file with specified text. Arguments: {'path': 'string', 'contents': 'string'}\n"
        "- 'run_command': Runs Windows shell commands. Arguments: {'command': 'string'}\n"
        "- 'web_search': Searches the live internet for up-to-date facts, news, or articles. Arguments: {'query': 'string'}\n"

        "IMPORTANT: The 'web_search' tool is REAL and FULLY FUNCTIONAL on this system. "
        "It uses a live search engine and returns actual results. "
        "Do NOT attempt to use run_command to fetch web data. "
        "Do NOT use curl, Invoke-RestMethod, or any HTTP commands. "
        "When you need live information from the internet, ALWAYS use web_search.\n\n"

        "ABSOLUTE RULE: When a tool is required, your ENTIRE response must be ONLY the raw JSON object. "
        "Not a code block. Not backticks. Not an explanation. Just the raw JSON starting with { and ending with }. "
        "A response like '```json\n\n```\nThis should give...' is a CRITICAL FAILURE. "
        "If you need to use run_command, output ONLY this and nothing else:\n"
        '{"action": "run_command", "arguments": {"command": "YOUR COMMAND HERE"}}\n'

        "CRITICAL OPERATIONAL RULES FOR TOOLS:"
        "1. You can only execute ONE tool call per response. Do not chain multiple JSON blocks together."
        "2. If a task requires multiple steps (like reading a file, then creating a file), only output the first JSON block. The system will run it and give you the results, and you can output the second JSON block in your next turn."

        "CRITICAL: You must NEVER simulate, assume, or hallucinate tool results. "
        "Output ONE tool call JSON and stop. Wait for the actual [TOOL RESULT] before proceeding. "
        "Never write 'Result:' or describe what a tool would return. Just output the JSON and nothing else."

        "TURN STRUCTURE - THIS IS MANDATORY:\n"

        "- Your turn ends the MOMENT you output a JSON tool call.\n"
        "- Do NOT write anything after the JSON. No 'Result:', no explanation, no next steps.\n"
        "- You will receive the tool result in the next message as [TOOL RESULT].\n"
        "- Only THEN may you decide what to do next.\n"
        "- Outputting fake results like 'Result: The file contains...' before receiving [TOOL RESULT] is a CRITICAL FAILURE.\n"
        "- ONE JSON OBJECT PER RESPONSE. Then stop. Wait.\n"

        "Only use tools if the user's message contains clear action words like 'create', 'read', 'list', 'run', 'delete', 'write', 'check'. "
        "Casual nouns like names, places, or organizations are NOT file paths or commands."
        "NEVER write the text 'Executing tool' or announce that you are using a tool in plain text. Your response must jump STRAIGHT into the JSON block starting with { and nothing else. If you write conversational text before the JSON, the system will crash."

    )

def build_debug_prompt(id):
    return (
        f"You are {id['name']}, an autonomous local AI agent operating via Discord.\n"
    f"Your conversational tone, attitude, and style must be: {id['tone']}\n\n"
    "CRITICAL: You must ALWAYS respond in English only. Never use any other language "
    "under any circumstances. Not even a single word in another language.\n\n"
    "You are currently in RUBBER DUCK DEBUG MODE.\n"
    "Your role has fundamentally changed. You are no longer here to solve problems.\n"
    "You are here to help the user solve their OWN problems by asking questions.\n\n"
    
    "RUBBER DUCK RULES:\n"
    "1. NEVER give the answer directly, even if you know it.\n"
    "2. ALWAYS respond with a question that guides the user toward the answer.\n"
    "3. Ask one question at a time. Never stack multiple questions.\n"
    "4. If the user is stuck, ask them to explain the code line by line.\n"
    "5. If they find the bug themselves, celebrate it in your character's voice.\n"
    "6. Stay in character the entire time — you're still Sidekick, just in debug mode.\n\n"
    "7. Never hint at WHERE the bug is or WHAT TYPE of bug it is. "
    "8. Only ask the user to explain their own code back to you line by line. "
    "9. Let them find the location and type of bug entirely on their own.\n\n"

    "Example questions to ask:\n"
    "- What do you EXPECT this line to do?\n"
    "- What is it ACTUALLY doing instead?\n"
    "- Have you tried printing the value of X at that point?\n"
    "- When did this last work correctly?\n"
    "- What changed between then and now?\n\n"
    
    "When the user says 'exit debug' or similar, output ONLY this exact text:\n"
    "DEBUG_SESSION_COMPLETE\n"
    "Followed by a one paragraph summary of what was debugged and what the user discovered."
)

#load up long-term history
chat_history = load_memory()

# ==============================================================================
# STEP 1: CONFIGURATION VARIABLES
# ==============================================================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
USER_ID = int(os.getenv("USER_ID"))
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL")
TARGET_MODEL = os.getenv("TARGET_MODEL")

# ==============================================================================
# STEP 2: INITIALIZATION & PERMISSIONS
# ==============================================================================
# 1. Set up the permissions checklist (intents)
intents = discord.Intents.default()
intents.message_content = True

# 2. Spin up the client instance using those permissions
client = discord.Client(intents=intents)


# ==============================================================================
# STEP 3: THE BOOT EVENT
# ==============================================================================
# This triggers the absolute second your bot successfully logs into Discord

@tasks.loop(seconds = 30)
async def agent_heartbeat():
    global last_interaction_time
    if time.time() - last_interaction_time < 300: # 5 minutes
        print("[Heartbeat] Skipped due to recent user interaction.")
        return

    print("[Heartbeat] Internal pulse checked. Assessing background state")

    agent_id = load_agent_config()
    if not agent_id:
        print("[Heartbeat]No soul file found. Skipping.")
        return
    try:
        checklist = ""
        with open("HEARTBEAT.md", "r", encoding="utf-8") as f:
            checklist = f.read()
    except FileNotFoundError:
        print("[Heartbeat] no Heartbeat file found. skipping")
        return
    
    heartbeat_history = [        
        {"role": "system", "content": build_runtime_prompt(agent_id)},
        {"role": "user", "content": 
            f"[HEARTBEAT PULSE]\nHere is your background checklist:\n\n{checklist}\n\n"
            "INSTRUCTIONS:\n"
            "1. Review the checklist. If any task requires you to send a reminder or check-in with Ryan (like reminding him to drink water), WRITE THAT MESSAGE NOW.\n"
            "2. Be proactive! Even if it's not an emergency, if the checklist says to remind him, do it in your character's voice.\n"
            "3. If all checklist tasks are handled and you have absolutely nothing to say, output ONLY the exact text: HEARTBEAT_OK\n"
            "4. NEVER combine HEARTBEAT_OK with a message. It is either your message to Ryan, or HEARTBEAT_OK alone. Never both.\n"}
        ]

    max_steps = 5
    step = 0
    while True:
        tool_executed = False
        step += 1
        if step > max_steps:
            print("[Heartbeat] Exceeded max steps.")
            break

        payload = {
            "model": TARGET_MODEL,
            "messages": heartbeat_history,
            "stream": False
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(OLLAMA_API_URL, json = payload) as api_response:
                    response_data = await api_response.json()
                    ai_reply = response_data.get("message", {}).get("content", "").strip()
                    print(f"[Heartbeat] Agent assessed: {repr(ai_reply[:80])}...")
                    
                    heartbeat_history.append({"role": "assistant", "content": ai_reply})

                    cleaned_reply = ai_reply.replace("```json", "").replace("```", "").strip()
                    json_match = re.search(r'\{.*\}', cleaned_reply, re.DOTALL)
                    if json_match:
                        try:
                            json_str = json_match.group()
                            tool_request = json.loads(json_str)
                            tool_name = tool_request.get("action")
                            tool_args = tool_request.get("arguments") or {
                                k: v for k, v in tool_request.items() if k != "action"
                            }

                            if tool_name in Skills_sys:
                                heartbeat_history[-1]["content"] = json_str
                                print(f"[Heartbeat Action] Running execution: {tool_name}")
                                execution_result = Skills_sys[tool_name](tool_args)
                                heartbeat_history.append({
                                    "role": "user",
                                    "content": f"[TOOL RESULT] {execution_result}"
                                })
                                continue
                            else:
                                print(f"[Heartbeat] Requested unmapped skill module: {tool_name}")
                                break
                        except json.JSONDecodeError:
                            pass

                    if ai_reply and ai_reply != "HEARTBEAT_OK":
                        clean_reply = ai_reply.replace("HEARTBEAT_OK", "").strip()
                        if clean_reply:
                            user = await client.fetch_user(USER_ID)
                            await user.send(clean_reply)
                            print("[Heartbeat] Message dispatched.")
                        else:
                            print("[Heartbeat] Heartbeat ok. Nothing to report")
                    break
        except Exception as e:
            print(f"[Heartbeat] Error: {e}")
            await asyncio.sleep(60) #back off if ollama is unreachable 
            break


@client.event
async def on_ready():
    print(f"--------------------------------------------------")
    print(f" 🦸SIDEKICK is officially ONLINE!")
    print(f" Logged in as: {client.user}")
    if not load_agent_config():
        print("No soul file detected. Standing by for setup interveiw.")
    print(f"--------------------------------------------------")
    print(f"Logged in as {client.user.name} - Engine Online.")
    #Start pulse
    agent_heartbeat.start()

# ==============================================================================
# MESSAGE HANDLER AND OLLAMA BRIDGE
# ==============================================================================
@client.event
async def on_message(message):
    global last_interaction_time

    #ignore message if the bot sent it itself
    if message.author == client.user:
        return
    
    last_interaction_time = time.time()

    #Check if the message is a private DM
    is_dm = isinstance(message.channel, discord.DMChannel)

    #if bot is not in message.mentions, return early
    if client.user not in message.mentions and not is_dm:
        return

    #clean up content to get raw string text so the mention doesn't confuse the AI
    if is_dm:
        clean_content = message.content.strip()
        history_id = str(message.author.id) #JSON needs string keys
    else:
        clean_content = re.sub(rf'<@!?{client.user.id}>', '', message.content).strip()
        history_id = str(message.channel.id)

    # Hot reload identity info right inside message event handler
    agent_id = load_agent_config()

    if "debug mode" in clean_content.lower():
        if not agent_id:
            await message.channel.send("You must initialize the agent parameters first before using debug mode.")
            return
        debug_sessions[history_id] = True
        chat_history[history_id] = [{"role": "system", "content": build_debug_prompt(agent_id)}]
        await message.channel.send("🦆 **Debug mode activated.** What's troubling you?I won't give you answers — I'll ask questions. Walk me through what's happening.")
        return
    
    # Debug Mode Exit
    if "exit debug" in clean_content.lower() and debug_sessions.get(history_id):
        debug_sessions[history_id] = False
        #Create summary
        chat_history[history_id].append({"role": "user", "content": "DEBUG_SESSION_COMPLETE"})
        #Go back to normal prompt
        chat_history[history_id] = [{"role": "system", "content": build_runtime_prompt(agent_id)}]
        save_memory(chat_history)
        await message.channel.send("🦆 **Debug session complete.** Back to normal mode. What would you like help with?")
        return
     # Step 1: Trigger    
    if "update checklist" in clean_content.lower() or "update heartbeat" in clean_content.lower():
        checklist_sessions[history_id] = "awaiting_mode"
        await message.channel.send("🗒️ Would you like to **replace** the entire checklist or **add** new tasks to it?")
        return

    if "clipboard" in clean_content.lower():
        try:
            current_clip = get_local_clipboard()
            if current_clip:
                clean_content = clean_content + f"\n\n[CLIPBOARD CONTENT]\n{current_clip}"
                print("[Clipboard Sentinel] Clipboard injected into message.")
        except Exception as e:
            print(f"[Clipboard Sentinel] Manual read failed: {e}")

    # Step 2: Mode selction
    if checklist_sessions.get(history_id) == "awaiting_mode":
        if "replace" in clean_content.lower():
            checklist_sessions[history_id] = "awaiting_tasks_replace"
            await message.channel.send("📝 What should the new checklist be? Send your tasks one per line.")
            return
        elif "add" in clean_content.lower():
            checklist_sessions[history_id] = "awaiting_tasks_add"
            await message.channel.send("📝 What would you like to add to the checklist? Send your tasks one per line.")
            return
        else:
            await message.channel.send("Please say **replace** or **add**.")
            return
    # Step 3: Recieve tasks
    if checklist_sessions.get(history_id) in ("awaiting_tasks_replace", "awaiting_tasks_add"):
        new_task = [line.strip() for line in clean_content.splitlines() if line.strip()]
        mode = checklist_sessions[history_id]

        if mode == "awaiting_tasks_replace":
            with open("HEARTBEAT.md", "w", encoding = "utf-8") as f:
                f.write("# Heartbeat Checklist\n")
                for task in new_task:
                    f.write(f"- {task}\n")
            await message.channel.send(f"✅ Checklist replaced with {len(new_task)} task(s)!")
        elif mode == "awaiting_tasks_add":
            with open("HEARTBEAT.md", "a", encoding = "utf-8") as f:
                for task in new_task:
                    f.write(f"- {task}\n")
            await message.channel.send(f"✅ Added {len(new_task)} task(s) to the checklist!")
        
        checklist_sessions.pop(history_id, None)
        save_memory(chat_history)
        return
            

    if debug_sessions.get(history_id):
        if history_id not in chat_history or chat_history[history_id][0]["content"] != build_debug_prompt(agent_id):
            chat_history[history_id] = [{"role": "system", "content": build_debug_prompt(agent_id)}]
    # Track conversation state for this specific thread
    if history_id not in chat_history:
        if not agent_id:
            chat_history[history_id] = [{"role": "system", "content": Bootstrap_prompt}]
        else:
            chat_history[history_id] = [{"role": "system", "content": build_runtime_prompt(agent_id)}]

    # Append user prompt to memory loop
    chat_history[history_id].append({"role": "user", "content": clean_content})
    save_memory(chat_history)
    
    #status update in terminal
    print(f"Incoming prompt from {message.author}: '{clean_content}'")
    
    async with message.channel.typing():
        # --- React loop ---
        max_steps = 5
        step = 0
        while True:
            tool_executed = False
            step += 1
            if step > max_steps:
                await message.channel.send("⚠️ Agent exceeded max steps, stopping.")
                break
            #package the data for Ollama API
            payload = {
                "model": TARGET_MODEL,
                "messages": chat_history[history_id],
                "stream": False
            }

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(OLLAMA_API_URL, json = payload) as api_response:
                        response_data = await api_response.json()
                        ai_message = response_data.get("message", {})
                        ai_reply = ai_message.get("content", "").strip()

                        # Intercept debug session complete
                        if "DEBUG_SESSION_COMPLETE" in ai_reply:
                            summary = ai_reply.replace("DEBUG_SESSION_COMPLETE", "").strip()
                            debug_sessions[history_id] = False
                            chat_history[history_id] = [{"role": "system", "content": build_runtime_prompt(agent_id)}]
                            save_memory(chat_history)
                            await message.channel.send(f"🦆 **Debug session complete.**\n\n{summary}")
                            return

                        print(f"[DEBUG] Raw model output: {repr(ai_reply)}")
                        #save agent reply to history
                        chat_history[history_id].append({"role": "assistant", "content": ai_reply})
                        save_memory(chat_history)

                        # ----------------------------------------------------------
                        # Identity Setup Phase
                        # ----------------------------------------------------------
                        if not agent_id:
                            if ai_reply.startswith("{") and ai_reply.endswith("}"):
                                try:
                                    identity_data = json.loads(ai_reply)
                                    if identity_data.get("initialized"):
                                        save_agent_config(identity_data)

                                        #Auto-generate heartbeat file from interview
                                        heartbeat_tasks = identity_data.get("heartbeat_tasks", [])
                                        if heartbeat_tasks:
                                            with open("HEARTBEAT.md", "w", encoding="utf-8") as f:
                                                f.write("# Heartbeat Checklist\n")
                                                for task in heartbeat_tasks:
                                                    f.write(f"- {task}\n")
                                        print("⚡ [System] Identity file generated successfully via chat context!")
                                        # Wipe setup logs out of active memory and write fresh operational rules
                                        chat_history[history_id] = [{"role": "system", "content": build_runtime_prompt(identity_data)}]
                                        save_memory(chat_history)

                                        await message.channel.send(f"⚡ **[System Initialization Complete]**\nI have successfully synthesized my core parameters. From this moment forward, I am **{identity_data['name']}**.")
                                        return
                                except json.JSONDecodeError:
                                    pass
                            await message.channel.send(ai_reply)
                            return
                        # ----------------------------------------------------------
                        # ReAct Tool Automation
                        # ----------------------------------------------------------
                        cleaned_reply = ai_reply.replace("```json", "").replace("```", "").strip()
                        json_match = re.search(r'\{.*\}', cleaned_reply, re.DOTALL)

                        tool_executed = False #see if tool actually ran successfully

                        if json_match:
                            try:
                                json_str = json_match.group()
                                print(f"[DEBUG] Attempting to parse: {repr(json_str)}")

                                tool_request = json.loads(json_str)
                                tool_name = tool_request.get("action")
                                tool_args = tool_request.get("arguments") or {
                                    k: v for k, v in tool_request.items() if k != "action"
                                    }

                                if tool_name in Skills_sys:
                                    #keep memory clean so he doesn't loop
                                    chat_history[history_id][-1]["content"] = json_str

                                    print(f"[Agent Action] Running execution: {tool_name}")
                                    execution_result = Skills_sys[tool_name](tool_args)
                                    print(f"[DEBUG] Tool result: {repr(execution_result)}")

                                    #Append output data back into memory for agent to look over
                                    chat_history[history_id].append({
                                        "role": "user",
                                        "content": f"[TOOL RESULT] {execution_result}"
                                    })
                                    save_memory(chat_history)

                                    # Send state back down the pipeline recursively to evaluate results
                                    print(f"[System] Fed tool results back to agent. Re-evaluating...")
                                    tool_executed = True
                                    continue  # Spins the loop again, hiding raw JSON from Discord
                                else:
                                    print(f"[Warning] Model outputted JSON, but tool '{tool_name}' is unmapped.")
                            except json.JSONDecodeError:
                                print("[DEBUG] Found brackets, but it wasn't valid JSON. Falling back to chat.")
                                pass
                        #normal standard fallback answer
                        if not tool_executed:
                            await message.channel.send(ai_reply)
                            break # break out loop since final answer was sent
            except Exception as error:
            #in case of it not running or crash, print error
                print(f"Error talking to Ollama: {error}")
                await message.channel.send("Sorry, I had trouble reaching my local brain.")
client.run(DISCORD_TOKEN)