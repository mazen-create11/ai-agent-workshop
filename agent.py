"""
Tidy: a small AI agent that cleans a messy Downloads folder.

Run it:
    pip install anthropic
    export ANTHROPIC_API_KEY="your-key"      (Windows: $env:ANTHROPIC_API_KEY="your-key")
    python agent.py
"""
import os
import shutil

import anthropic

# ---------- 0. SETTINGS ----------
FOLDER = "my_downloads"      # the ONLY folder the agent can touch
MODEL = "claude-opus-5-5"    # the brain
MAX_ROUNDS = 15              # safety stop: never loop forever


# ---------- 1. THE TOOLS (the agent's hands) ----------
def list_files():
    """Return the files that are still loose in the folder."""
    files = [
        name for name in os.listdir(FOLDER)
        if os.path.isfile(os.path.join(FOLDER, name)) and not name.startswith(".")
    ]
    return "\n".join(sorted(files)) or "(no loose files left)"


def move_file(filename, folder):
    """Move one file into a sub-folder. Create the sub-folder if needed."""
    for name in (filename, folder):
        if "/" in name or "\\" in name or ".." in name:
            return "Refused: use simple names, no paths."
    source = os.path.join(FOLDER, filename)
    if not os.path.isfile(source):
        return f"Error: {filename} does not exist."
    os.makedirs(os.path.join(FOLDER, folder), exist_ok=True)
    shutil.move(source, os.path.join(FOLDER, folder, filename))
    return f"Moved {filename} -> {folder}/"


# ---------- 2. THE TOOL MENU (what the model reads) ----------
TOOLS = [
    {
        "name": "list_files",
        "description": "List the files that are still loose in the Downloads folder.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "move_file",
        "description": "Move one file into a sub-folder. The sub-folder is created if needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Exact file name, e.g. cv_2026.pdf"},
                "folder": {"type": "string", "description": "Sub-folder name, e.g. Documents"},
            },
            "required": ["filename", "folder"],
        },
    },
]


def run_tool(name, args):
    if name == "list_files":
        return list_files()
    if name == "move_file":
        return move_file(args["filename"], args["folder"])
    return f"Error: unknown tool {name}"


# ---------- 3. THE GOAL ----------
GOAL = (
    "Clean up my Downloads folder. Put every file into one of these folders: "
    "Images, Documents, Audio, Videos, Other. "
    "Check that no loose file is left, then tell me what you did in 3 short lines."
)


# ---------- 4. THE LOOP (think -> act -> see, until done) ----------
def run_agent():
    client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY
    messages = [{"role": "user", "content": GOAL}]

    for round_number in range(1, MAX_ROUNDS + 1):
        print(f"\n--- Round {round_number} ---")
        response = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive", "display": "summarized"},
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "thinking" and block.thinking:
                print(f"[THINK] {block.thinking}")
            elif block.type == "text":
                print(f"[AGENT] {block.text}")
            elif block.type == "tool_use":
                print(f"[ACT]   {block.name}({block.input})")
                result = run_tool(block.name, block.input)
                print(f"[SEE]   {result}")
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )

        if response.stop_reason != "tool_use":   # no tool asked = job finished
            print(f"\nStopped after {round_number} rounds. Reason: {response.stop_reason}")
            return
        messages.append({"role": "user", "content": tool_results})

    print(f"\nSafety stop: {MAX_ROUNDS} rounds reached.")


# ---------- 5. DEMO FOLDER + START ----------
DEMO_FILES = [
    "beirut_sunset.jpg", "screenshot_0412.png", "cv_2026.pdf",
    "lecture_3_notes.docx", "budget_november.xlsx", "manakish_recipe.txt",
    "fairuz_live.mp3", "voice_note.m4a", "graduation_speech.mp4", "project_backup.zip",
]


def make_demo_folder():
    """First run only: create a messy folder with 10 empty demo files."""
    if os.path.exists(FOLDER):
        return
    os.makedirs(FOLDER)
    for name in DEMO_FILES:
        open(os.path.join(FOLDER, name), "w").close()


if __name__ == "__main__":
    make_demo_folder()
    run_agent()
