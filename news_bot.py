#!/usr/bin/env python3
import os, sys
from datetime import date
import anthropic, requests
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 8000
MAX_LOOP_ITERATIONS = 20
today = date.today().strftime("%A, %B %d, %Y")

PROMPT = f"""Today is {today}.
You are a daily news briefing assistant. Use web search to find real news stories published today or in the last 24 hours, then write a concise brief.
Cover exactly these 5 categories:
1. **Geopolitics & Politics** — Middle East, US policy, Arab world, regional conflicts
2. **AI** — new models, tools, business applications, funding, policy
3. **Barcelona** — local news, tech scene, startups, city developments
4. **Cairo & Egypt** — politics, economy, business, regional developments
5. **Startups & New Business Launches** — global focus with emphasis on EU and MENA
Rules:
- Search the web for each category separately to find today's actual stories
- 2–4 bullet points per category
- Each bullet: 1–2 sentences, cite the source name in parentheses
- Exclude: fashion, sports, entertainment, lifestyle
- Use *bold* for category headers (single asterisks for Telegram)
Start your response with:
📰 *Daily News Brief — {date.today().strftime("%B %d, %Y")}*
Then cover all 5 categories in order."""

def get_news_brief():
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    messages = [{"role": "user", "content": PROMPT}]
    tools = [{"type": "web_search_20250305", "name": "web_search"}]
    for _ in range(MAX_LOOP_ITERATIONS):
        response = client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, tools=tools, messages=messages)
        if response.stop_reason == "end_turn":
            return "".join(b.text for b in response.content if hasattr(b, "text"))
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": b.id, "content": ""} for b in response.content if b.type == "tool_use"]})
            continue
        raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")
    raise RuntimeError("Loop limit exceeded")

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > 4096:
            if current: chunks.append(current)
            current = line
        else:
            current += line
    if current: chunks.append(current)
    for chunk in chunks:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": chunk, "parse_mode": "Markdown"}, timeout=30).raise_for_status()

def main():
    missing = [k for k, v in {"ANTHROPIC_API_KEY": ANTHROPIC_API_KEY, "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN, "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID}.items() if not v]
    if missing: sys.exit(f"Missing: {', '.join(missing)}")
    print(f"[{today}] Fetching news brief...")
    brief = get_news_brief()
    print("Sending to Telegram...")
    send_telegram(brief)
    print("Done.")

if __name__ == "__main__":
    main()
