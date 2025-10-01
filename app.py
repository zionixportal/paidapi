import asyncio
from flask import Flask, request, jsonify
from telethon import TelegramClient, events, errors
import json

# ---------------- CONFIG ----------------
API_ID = 29132892                 # apna API_ID
API_HASH = "7a48045cdced2a55c85d19342a6b3a48"
SESSION = "user_session"          # .session file name
TARGET_BOT = "@crazy_num_info_bot"
REPLY_TIMEOUT = 15                # seconds
# --------------------------------------

app = Flask(__name__)

# Create event loop explicitly for Python 3.12 compatibility
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Telegram client
tele_client = TelegramClient(SESSION, API_ID, API_HASH, loop=loop)


async def forward_to_target_and_get_reply(number: str):
    """
    Send query to TARGET_BOT in correct format: /num <number>
    Returns: (list of replies, error)
    """
    if not tele_client.is_connected():
        await tele_client.connect()

    try:
        # ✅ Send in correct format
        query = f"/num {number}"
        await tele_client.send_message(TARGET_BOT, query)

        all_msgs = []

        @tele_client.on(events.NewMessage(from_users=TARGET_BOT))
        async def handler(event):
            all_msgs.append(event.message)

        # Wait for reply
        await asyncio.sleep(REPLY_TIMEOUT)
        tele_client.remove_event_handler(handler)

        if not all_msgs:
            return None, "⚠️ Timeout: Target bot ne reply nahi diya."

        # Return text only or media placeholder
        return [m.text or "📎 Media reply" for m in all_msgs], None

    except errors.FloodWaitError as fe:
        return None, f"⏳ Flood wait: {fe.seconds} sec rukna padega."
    except Exception as e:
        return None, f"❌ Error: {e}"


@app.route("/num/<number>", methods=["GET"])
def num_lookup(number):
    """
    API endpoint: /num/9876543210
    Returns JSON response from target bot.
    """
    replies, err = loop.run_until_complete(forward_to_target_and_get_reply(number))
    if err:
        return jsonify({"error": err}), 500

    # Try to parse string response as JSON (if bot returns JSON string)
    final_result = []
    for r in replies:
        try:
            # Sometimes bot returns "Result for 9876543210:{...}"
            if "{" in r:
                json_part = r.split(":", 1)[1]  # remove prefix
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

    # Start Flask server
    print("🌐 API running on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000)