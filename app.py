import os
from flask import Flask, request, abort, jsonify

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent

app = Flask(__name__)

# --- 環境変数の設定 ---
# ローカルでテストする場合は、ターミナルで環境変数を設定してください
YOUR_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
YOUR_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

# 環境変数が設定されていない場合にエラーを発生させる
if not YOUR_CHANNEL_ACCESS_TOKEN or not YOUR_CHANNEL_SECRET:
    raise ValueError("環境変数が設定されていません。'LINE_CHANNEL_ACCESS_TOKEN'と'LINE_CHANNEL_SECRET'を設定してください。")

configuration = Configuration(access_token=YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

# ユーザーIDを保存するための簡単なリスト（本番環境ではデータベースを推奨）
user_ids = set()

# --- 1. LINEからのWebhookを受け取るエンドポイント ---
@app.route("/callback", methods=['POST'])
def callback():
    """LINEからのWebhookイベントを処理する"""
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Check your channel secret.")
        abort(400)
    return 'OK'

# --- 2. ユーザーがメッセージを送った時の処理 ---
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """メッセージイベントを処理し、ユーザーIDをログに出力する"""
    user_id = event.source.user_id
    
    # ここでユーザーIDをログに出力
    print(f"メッセージを送信したユーザーID: {user_id}")
    
    # ユーザーIDをセットに追加
    if user_id not in user_ids:
        user_ids.add(user_id)
        print(f"新しいユーザーIDを追加しました: {user_id}")
        
    print(f"現在のユーザーIDリスト: {user_ids}")
    
    # ユーザーIDをそのまま返信
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            reply_token=event.reply_token,
            messages=[TextMessage(text=f"あなたのIDは {user_id} です。")]
        )

# --- 3. ユーザーが友達追加した時の処理 ---
@handler.add(FollowEvent)
def handle_follow(event):
    """フォローイベントを処理し、ユーザーIDをログに出力する"""
    user_id = event.source.user_id
    
    # ここでユーザーIDをログに出力
    print(f"新しく友達追加したユーザーID: {user_id}")

    # ユーザーIDをセットに追加
    if user_id not in user_ids:
        user_ids.add(user_id)
        print(f"新しいフォロワーのユーザーIDを追加しました: {user_id}")
    
    print(f"現在のユーザーIDリスト: {user_ids}")
    
    # 友達追加時に挨拶メッセージを返す
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            reply_token=event.reply_token,
            messages=[TextMessage(text="友達追加ありがとうございます！")]
        )

# --- 4. 別のアプリからプッシュメッセージの送信を指示されるエンドポイント ---
@app.route("/push", methods=['POST'])
def push_message():
    """指定されたユーザーIDにプッシュメッセージを送信する"""
    data = request.get_json()
    if not data or 'to' not in data or 'message' not in data:
        return jsonify({"status": "error", "message": "Invalid request body. 'to' and 'message' are required."}), 400

    user_id_to_push = data['to']
    message_text = data['message']

    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id_to_push,
                    messages=[TextMessage(text=message_text)]
                )
            )
        print(f"メッセージを送信しました: to={user_id_to_push}, message='{message_text}'")
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- 5. 保存されているユーザーIDのリストを確認するエンドポイント（確認用）---
@app.route("/users", methods=['GET'])
def get_users():
    """保存されている全ユーザーIDのリストを返す"""
    return jsonify(list(user_ids))


if __name__ == "__main__":
    app.run(port=5001, debug=True)