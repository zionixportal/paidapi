import asyncio
from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.errors import FloodWaitError
import json
import os

# ---------------- CONFIG ----------------
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION = os.environ.get("SESSION", "user_session")
TARGET_BOT = "@crazy_num_info_bot"

MAX_WAIT_SECONDS = 20   # max wait for reply
POLL_INTERVAL = 1       # poll every 1 sec
# --------------------------------------

app = Flask(__name__)

# Create explicit loop (for Python 3.12+)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Telethon client
tele_client = TelegramClient(SESSION, API_ID, API_HASH, loop=loop)


async def forward_to_target_and_get_reply(number: str):
    """Send number to target bot and poll until reply arrives."""
    if not tele_client.is_connected():
        await tele_client.connect()

    try:
        # Send query to target bot
        await tele_client.send_message(TARGET_BOT, f"/num {number}")

        # Polling for reply
        for _ in range(int(MAX_WAIT_SECONDS / POLL_INTERVAL)):
            messages = await tele_client.get_messages(TARGET_BOT, limit=20)
            if messages and messages[0].from_id:  # ensure it's reply, not our own message
                text = messages[0].text or "📎 Media reply"
                if not text.startswith("/num"):   # ignore our own command
                    return [text], None
            await asyncio.sleep(POLL_INTERVAL)

        return None, f"⚠️ Timeout: No reply within {MAX_WAIT_SECONDS} seconds."

    except FloodWaitError as fe:
        return None, f"⏳ Flood wait: wait {fe.seconds} sec."
    except Exception as e:
        return None, f"❌ Error: {e}"


@app.route("/num", methods=["GET"])
def num_lookup():
    """API endpoint for number lookup"""
    number = request.args.get("number")
    if not number:
        return jsonify({"error": "⚠️ Missing 'number' param"}), 400

    replies, err = loop.run_until_complete(forward_to_target_and_get_reply(number))
    if err:
        return jsonify({"error": err}), 500

    # Try JSON parsing if reply looks like JSON
    final_result = []
    for r in replies:
        try:
            parsed = json.loads(r)
            final_result.append(parsed)
        except:
            final_result.append(r)

    return jsonify({"result": final_result})


if __name__ == "__main__":
    # Start Telethon client
    async def init_client():
        await tele_client.start()
        print("✅ Telethon client started")

    loop.run_until_complete(init_client())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
