import os
import sys

from flask import Flask, request, abort

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from dotenv import load_dotenv

import deepl
import opencc

app = Flask(__name__)

load_dotenv()

channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
deepl_auth_key = os.getenv('DEEPL_AUTH_KEY', None)

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)
if deepl_auth_key is None:
    print('Specify DEEPL_AUTH_KEY as environment variable.')
    sys.exit(1)

handler = WebhookHandler(channel_secret)
configuration = Configuration(
    access_token=channel_access_token
)

translator = deepl.Translator(deepl_auth_key)
converter = opencc.OpenCC('s2t.json')

def translate(text):
    en_text = translator.translate_text(text, target_lang="EN-US")
    result = en_text.text + "\n\n"

    if (en_text.detected_source_lang == "ZH" or en_text.detected_source_lang == "EN"):
        app.logger.info("Detected Chinese text")
        id_text = translator.translate_text(text, target_lang="ID")
        result += id_text.text
    else:
        app.logger.info("Detected Indonesian text")
        zh_text = translator.translate_text(text, target_lang="ZH")
        zh_text = converter.convert(zh_text.text)
        result += zh_text

    return result


@app.route("/callback", methods=["POST"])
def callback():
    # get X-Line-Signature header value
    signature = request.headers["X-Line-Signature"]

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info(
            "Invalid signature. Please check your channel access token/channel secret."
        )
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        message = translate(event.message.text)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=message)],
            )
        )


if __name__ == "__main__":
    from waitress import serve
    serve(app, host='0.0.0.0', port=8000)
