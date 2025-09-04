from flask import Flask, request, jsonify
import os, requests, json, time

app = Flask(__name__)

# Lấy thông tin từ biến môi trường (không viết thẳng App Secret trong code!)
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")

# Cache token đơn giản để đỡ gọi API liên tục
_token = {"val": None, "exp": 0}

def get_tenant_access_token():
    now = time.time()
    if _token["val"] and now < _token["exp"]:
        return _token["val"]

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
    data = resp.json()
    if "tenant_access_token" not in data:
        raise RuntimeError(f"Get token failed: {data}")
    _token["val"] = data["tenant_access_token"]
    _token["exp"] = now + data.get("expire", 3600) - 60
    return _token["val"]

@app.route("/", methods=["GET"])
def index():
    return "Feishu bot is running", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json(silent=True) or {}

    # Bước xác thực URL (Feishu gửi 'challenge')
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
    text = (content.get("text") or "").strip()

    # Logic trả lời cơ bản
    reply_text = "Xin chào 👋 Mình đã nhận được tin nhắn và sẽ phản hồi sớm nhất."
    lower = text.lower()
    if lower in ("hi", "hello", "xin chào", "xin chao"):
        reply_text = "Chào bạn! Hiện mình bận, mình sẽ liên hệ lại ngay khi rảnh."
    elif lower in ("help", "hỗ trợ"):
        reply_text = "Bạn để lại nội dung + số điện thoại nhé, mình sẽ hỗ trợ ngay khi có thể."

    reply_url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"
    headers = {"Authorization": f"Bearer {get_tenant_access_token()}", "Content-Type": "application/json"}
    body = {"msg_type": "text", "content": {"text": reply_text}}
    r = requests.post(reply_url, headers=headers, json=body, timeout=10)
    if r.status_code >= 400:
        print("Reply failed:", r.status_code, r.text)

    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
