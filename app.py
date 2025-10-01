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
MAX_WAIT_SECONDS = 20  # Maximum time to wait for Telegram reply
POLL_INTERVAL = 0.5    # Check every 0.5 seconds
# --------------------------------------

app = Flask(__name__)

# Create explicit loop for Python 3.12+ compatibility
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Telethon client
tele_client = TelegramClient(SESSION, API_ID, API_HASH, loop=loop)


async def forward_to_target_and_get_reply(number: str):
    if not tele_client.is_connected():
        await tele_client.connect()

    try:
        await tele_client.send_message(TARGET_BOT, f"/num {number}")

        # Polling instead of sleeping
        total_polls = int(MAX_WAIT_SECONDS / POLL_INTERVAL)
        for _ in range(total_polls):
            messages = await tele_client.get_messages(TARGET_BOT, limit=1)
            if messages:
                return [messages[0].text or "📎 Media reply"], None
            await asyncio.sleep(POLL_INTERVAL)

        return None, f"⚠️ Timeout: Target bot did not reply within {MAX_WAIT_SECONDS} seconds."

    except FloodWaitError as fe:
        return None, f"⏳ Flood wait: {fe.seconds} sec pause required."
    except Exception as e:
        return None, f"❌ Error: {e}"


@app.route("/num", methods=["GET"])
def num_lookup():
    number = request.args.get("number")
    if not number:
        return jsonify({"error": "⚠️ Missing 'number' param"}), 400

    replies, err = loop.run_until_complete(forward_to_target_and_get_reply(number))
    if err:
        return jsonify({"error": err}), 500

    final_result = []
    for r in replies:
        try:
            if "{" in r:
                json_part = r.split(":", 1)[1]
                parsed = json.loads(json_part)
                final_result.append(parsed)
            else:
                final_result.append(r)
        except:
            final_result.append(r)

    return jsonify({"result": final_result})


if __name__ == "__main__":
    # Start Telethon client
    async def init_client():
        await tele_client.start()
        print("✅ Telethon client started")

    loop.run_until_complete(init_client())
    # Debug Flask server (not for production on Render)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
