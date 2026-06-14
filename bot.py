from instagrapi import Client
import json
import time
import requests

# ─── Config ───────────────────────────────────────────────────────────────────
TARGET_USER_ID = 99123456789
# PROXY = "http://ip:port"
LLM_API_URL = "https://api.kilo.ai/api/openrouter/chat/completions"
LLM_MODEL = "stepfun/step-3.7-flash:free"
SYSTEM_PROMPT = (
    "You are a helpful, friendly AI assistant chatting via Instagram DMs. "
    "Keep responses concise and natural. Use emojis occasionally but not excessively."
)
POLL_INTERVAL = 3       # seconds between checks
MAX_MSG_LENGTH = 900     # safety cap per Instagram DM
# ──────────────────────────────────────────────────────────────────────────────

# Initialize Instagram client
cl = Client()
# cl.set_proxy(PROXY)

with open('session.json', 'r') as f:
    cl.set_settings(json.load(f))

# Conversation memory — persists across messages so context remains
conversation_history = []  # [{"role": "user/assistant", "content": "..."}]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def find_thread():
    """Find existing DM thread with the target user."""
    threads = cl.direct_threads()
    for thread in threads:
        for user in thread.users:
            if str(user.pk) == str(TARGET_USER_ID):
                return thread
    return None


def call_llm(messages):
    """Send full conversation context to the LLM and return the reply."""
    try:
        resp = requests.post(
            LLM_API_URL,
            json={
                "model": LLM_MODEL,
                "messages": messages,
                "stream": False
            },
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"  ❌ LLM Error: {e}")
        return "Sorry, I encountered an error. Please try again."


def send_dm(text):
    """Send a DM, splitting into chunks if it exceeds the length limit."""
    if len(text) <= MAX_MSG_LENGTH:
        cl.direct_send(text, user_ids=[TARGET_USER_ID])
    else:
        chunk = text[:MAX_MSG_LENGTH]
        cl.direct_send(chunk, user_ids=[TARGET_USER_ID])
        remaining = text[MAX_MSG_LENGTH:]
        if remaining.strip():
            time.sleep(1)
            send_dm(remaining)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    # Find or create thread
    print("🔍 Looking for DM thread with user...")
    thread = find_thread()

    if not thread:
        print("  No thread found. Starting one...")
        cl.direct_send(
            "👋 Hi! I'm an AI assistant. Send me a message!",
            user_ids=[TARGET_USER_ID]
        )
        time.sleep(3)
        thread = find_thread()

    if not thread:
        print("❌ Could not find or create thread. Exiting.")
        return

    thread_id = thread.id
    print(f"  ✅ Thread found: {thread_id}")

    # Mark every existing message as already processed
    processed_ids = set()
    existing = cl.direct_messages(thread_id, amount=20)
    for msg in existing:
        processed_ids.add(msg.id)
    print(f"  ℹ️  {len(processed_ids)} existing messages marked as read.")
    print("\n🎧 Listening for new messages...")
    print("=" * 60)

    # Polling loop
    while True:
        try:
            messages = cl.direct_messages(thread_id, amount=10)

            for msg in reversed(messages):          # oldest → newest
                if msg.id in processed_ids:
                    continue
                processed_ids.add(msg.id)

                # Only react to TEXT messages FROM the target user
                if str(msg.user_id) != str(TARGET_USER_ID):
                    continue
                if msg.item_type != 'text':
                    continue

                user_text = msg.text
                print(f"\n📩 [USER]: {user_text}")

                # 1) Add user message to context
                conversation_history.append({
                    "role": "user",
                    "content": user_text
                })

                # 2) Instant "thinking" indicator
                send_dm("🤔 AI is thinking...")
                print("   🤔 Sent: AI is thinking...")

                # 3) Call LLM with full conversation context
                llm_messages = [
                    {"role": "system", "content": SYSTEM_PROMPT}
                ] + conversation_history

                ai_response = call_llm(llm_messages)

                # 4) Add assistant reply to context so future turns remember it
                conversation_history.append({
                    "role": "assistant",
                    "content": ai_response
                })

                # 5) Send the real response
                send_dm(ai_response)
                truncated = ai_response[:80] + ("..." if len(ai_response) > 80 else "")
                print(f"   🤖 [BOT]: {truncated}")

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n🛑 Stopped by user.")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
