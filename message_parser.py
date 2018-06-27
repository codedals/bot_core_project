# [BEGIN IMPORTS Google NLP]
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types as ltypes

from google.cloud import vision
from google.cloud.vision import types as vtypes
import dialogflow
# [END IMPORTS Google NLP]

import logging
import pdb
import sys
import json
import os
import io
import yaml
import uuid

project_id='bot-core'
language_code='en-US'
nlp_client = language.LanguageServiceClient()
vision_client = vision.ImageAnnotatorClient()

#Generate a unique session ID per interaction, allowing for continuous conversations
session_id= str(uuid.uuid4())


#detects content from an image
#returns results of google image analysis
def analyze_image(image_uri):
    response = vision_client.annotate_image({
        'image': {'source': {'image_uri':image_uri}}
    })
    return response

#detects sentiment of a given message
#returns sentiment and confidence
def get_sentiment(input):
    text = input
    document = ltypes.Document(
        content=text,
        type=enums.Document.Type.PLAIN_TEXT)

    sentiment = nlp_client.analyze_sentiment(document=document).document_sentiment
    return sentiment

#detects intent and gets and fulfilment texts
#returns dialogflow intent and any fulfillment messages
def detect_intent_texts(texts):
    session_client = dialogflow.SessionsClient()

    session = session_client.session_path(project_id, session_id)
    print('Session path: {}\n'.format(session))

    for text in texts:
        text_input = dialogflow.types.TextInput(
            text=text, language_code=language_code)

        query_input = dialogflow.types.QueryInput(text=text_input)

        response = session_client.detect_intent(
            session=session, query_input=query_input)

        print('=' * 20)
        print('Query text: {}'.format(response.query_result))

        print('Detected intent: {} (confidence: {})\n'.format(
            response.query_result.intent.display_name,
            response.query_result.intent_detection_confidence))

        print('Fulfillment text: {}\n'.format(
            response.query_result.fulfillment_text))
        
        return response.query_result

#get information about the user thats interacting with the bot
#returns userId and groupId
def get_line_request_info(event):
    userId = None
    groupId = None

    try:
        #user sending the message
        userId = event.source.user_id
        if event.source.type == 'group':
            groupId = event.source.group_id
    finally:
        return {'userId': userId, 'groupId': groupId}
