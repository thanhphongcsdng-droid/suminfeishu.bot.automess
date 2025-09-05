from flask import Flask, request, jsonify
import os, requests, json, time

app = Flask(__name__)

# ===== Cấu hình App ID / Secret từ biến môi trường =====
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")

# ===== Cache token để tránh gọi API quá nhiều =====
_token = {"val": None, "exp": 0}

def get_tenant_access_token():
    now = time.time()
    if _token["val"] and now < _token["exp"]:
        return _token["val"]

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
    data = resp.json()
    if "tenant_access_token" not in data:
        print("Get token failed:", data)
        raise RuntimeError(f"Get token failed: {data}")
    _token["val"] = data["tenant_access_token"]
    _token["exp"] = now + data.get("expire", 3600) - 60
    return _token["val"]


# ===== Kịch bản trả lời =====
REPLIES = {
    ("hi", "hello", "xin chào", "xin chao", "ơi"): (
        "Đây là BOT tự động trả lời tin nhắn của anh, hiện anh đang off không trả lời tin nhắn được nhé"
    ),
    ("help", "hỗ trợ"): (
        "Đây là BOT tự động trả lời tin nhắn của anh, hiện anh đang off liên hệ bạn khác hoặc nhóm giúp anh. "
        "Tin nhắn sẽ trôi đó nhé. Nếu cần anh xử lý riêng thì nhắn zalo anh sẽ hỗ trợ sau."
    ),
}

DEFAULT_REPLY = (
    "Đây là BOT tự động trả lời tin nhắn của anh, hiện anh đang off liên hệ bạn khác hoặc nhóm giúp anh. "
    "Tin nhắn sẽ trôi đó nhé"
)


# ===== Flask Routes =====
@app.route("/", methods=["GET"])
def index():
    return "Feishu bot is running ✅", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json(silent=True) or {}

    # Xác thực challenge từ Feishu khi bật Event Subscription
    if "challenge" in payload:
        return jsonify({"challenge": payload["challenge"]})

    event = payload.get("event", {})
    msg = event.get("message")
    if not msg:
        return "ok", 200

    message_id = msg.get("message_id")
    content_raw = msg.get("content", "{}")

    try:
        content = json.loads(content_raw)
    except Exception:
        content = {}

    text = (content.get("text") or "").strip().lower()

    # ===== Xử lý kịch bản trả lời =====
    reply_text = DEFAULT_REPLY
    for keywords, response in REPLIES.items():
        if text in keywords:
            reply_text = response
            break

    # ===== Gửi trả lời qua API Feishu =====
    reply_url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"
    headers = {
        "Authorization": f"Bearer {get_tenant_access_token()}",
        "Content-Type": "application/json"
    }
    body = {"msg_type": "text", "content": {"text": reply_text}}

    r = requests.post(reply_url, headers=headers, json=body, timeout=10)
    if r.status_code >= 400:
        print("Reply failed:", r.status_code, r.text)

    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
