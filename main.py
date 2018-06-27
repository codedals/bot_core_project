from __future__ import unicode_literals
import os
import pyrebase

# [START import_libraries]
import argparse
import uuid

import dialogflow
# [END import_libraries]

# [START app]
import logging
import pdb
import sys
import yaml

# [START imports]
from flask import Flask, request, abort
# [END imports]

# [Start Import Line SDK]
from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)
#[End Import Line SDK]

import message_parser

config = {
    "apiKey": os.environ.get('BOT_CORE_API_KEY'),
    "authDomain": os.environ.get('BOT_CORE_AUTH_DOMAIN'),
    "databaseURL": os.environ.get('BOT_CORE_DB_URL'),
    "projectId": os.environ.get('BOT_CORE_PROJECT_ID'),
    "storageBucket": os.environ.get('BOT_CORE_STORAGE_BUCKET'),
    "messagingSenderId": os.environ.get('BOT_CORE_MESSAGING_ID'),
 }

firebase = pyrebase.initialize_app(config)

db = firebase.database()
storage = firebase.storage()

bot_speech = yaml.load(open('config/locales/en.yml'))

# [START create_app]
app = Flask(__name__)
# [END create_app]


line_bot_api = LineBotApi(os.environ.get('BOT_CORE_LINE_API_KEY'))
parser = WebhookParser(os.environ.get('BOT_CORE_LINE_PARSER_KEY'))

#My personal line ID so that the bot can recognize its creator
creator = os.environ.get('BOTE_CORE_CREATOR_LINE_ID')

def find_or_create_group_id(groupId):    
    #get the date
    target_group = db.child("groups").child(groupId).get()
    if target_group.val(): #group record exists, do nothing and return
        return target_group
    else:
        data = {'bot_state': DEFAULT_PERSONALITY}
        db.child("groups").child(groupId).set(data)
    return db.child("groups").child(groupId).get()

#TODO -- Move to Firebase, and also have this set per room, rather than global 
DEFAULT_PERSONALITY = {
    'humor': 5,
    'grit': 5,
    'intelligence': 5,
    'flippancy':5,
    'responseRate': 10
}

debug_mode = False

def get_attributes():
    str_val = "Debug Mode: {}\nPersonality:\nHumor: {}\nGrit: {}\nIntelligence: {}".format(str(debug_mode),str(working_personality['humor']), str(working_personality['grit']), str(working_personality['intelligence']))
    return str_val

def set_debug_mode(val):
    debug_mode = val

def set_personality(attribute, val):
    working_personality[attribute] = val

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)

    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    for event in events:
        id_results = message_parser.get_line_request_info(event)
        user_id = id_results['userId']
        group_id = id_results['groupId']
        profile = None

        if event.type == "join":
            if group_id:
                find_or_create_group_id(group_id)                
                line_bot_api.reply_message(event.reply_token,TextSendMessage(text=bot_speech["basic"]["join"]))
            continue 
        elif event.type == "leave":
            continue            
        elif event.type == "message":
            if user_id:            
                profile = line_bot_api.get_profile(user_id)
                senders_name = profile.display_name
            if event.message.type == 'image':
                file_path = "temp_img_" + event.message.id
                message_content = line_bot_api.get_message_content(event.message.id)

                storage.child("images/" + file_path).put(message_content.iter_content())
                image_uri = storage.child("images/" + file_path).get_url(None)
                img_results = message_parser.analyze_image(image_uri)

                #ADD some error checks here
                basic_description = img_results.web_detection.web_entities[0].description
                line_bot_api.reply_message(event.reply_token,TextSendMessage(text=bot_speech["basic"]["image_recog"].format(basic_description)))
            #TODO -- this is broken
            elif event.message.type == 'text':
                sentiment = message_parser.get_sentiment(event.message.text)

                if sentiment.score > 0:
                    sent_text = "positve" + event.message.text
                else:
                    sent_text = "negative" + event.message.text

                intent = message_parser.detect_intent_texts([event.message.text])

                if user_id == creator and event.message.text == 'debug mode':
                    set_debug_mode(True)
                    line_bot_api.reply_message(event.reply_token,TextSendMessage(text='debug on'))    

                else:
                    if intent.fulfillment_text != "":
                        line_bot_api.reply_message(event.reply_token,TextSendMessage(text=intent.fulfillment_text))
            else:
                line_bot_api.reply_message(event.reply_token,TextSendMessage(text=bot_speech["basic"]["fallback"].format(senders_name)))               

    return 'OK'

@app.errorhandler(500)                                                                           
def server_error(e):
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
