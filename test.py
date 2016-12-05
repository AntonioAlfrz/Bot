import ConfigParser
import logging
import requests
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters
from subprocess import call
import uuid
import sqlite_data
import datetime
from os import remove

# APIs
api_token_url = "https://api.cognitive.microsoft.com/sts/v1.0/issueToken"
api_url = "https://speech.platform.bing.com/recognize"
luis_url = "https://api.projectoxford.ai/luis/v2.0/apps"
luis_lang = "appid_en" #appid_es
speech_lang = "en-US" #es-ES

# Intents
availability = "builtin.intent.calendar.check_availability"
create = "builtin.intent.calendar.create_calendar_entry"
delete = "builtin.intent.calendar.delete_calendar_entry"
show = "builtin.intent.calendar.find_calendar_entry"
intents = [
    availability,
    create,
    delete,
    show
]
# Entities
start_date = "builtin.calendar.start_date"
start_time = "builtin.calendar.start_time"
title = "builtin.calendar.title"

# Credentials
Config = ConfigParser.ConfigParser()
Config.read("credentials.ini")
# LUIS
luis_key = Config.get("LUIS", "key")
luis_appid = Config.get("LUIS", luis_lang)
luis_url += "/"+luis_appid
# Speech API
api_key = Config.get("Azure", "speech_key")
# Telegram
telegram_token = Config.get("Telegram", "token")
updater = Updater(token=telegram_token)

# Bot wrapper
dispatcher = updater.dispatcher
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# Commands
def start(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="I am able to store appointments, update and delete them and "
                                                         "show your calendar. Talk to me or write an order!")


# Echo
def echo(bot, update):
    # bot.sendMessage(chat_id=update.message.chat_id, text=update.message.text)
    data = luis_request(update.message.text)
    logger.info(data)
    printing = process_intents(str(update.message.from_user.id), data["intents"][0]["intent"], data["entities"])
    for item in printing:
        bot.sendMessage(chat_id=update.message.chat_id, text=item)


# Default
def unknown(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, I didn't understand that")


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


# Voice
def audio(bot, update):
    user = str(update.message.from_user.id)
    bot.getFile(update.message.voice.file_id).download(user+".ogg")
    text = speech_to_text(user)
    bot.sendMessage(chat_id=update.message.chat_id, text="You said: "+text)
    intent = luis_request(text)
    logger.info(intent)
    printing = process_intents(user, intent["intents"][0]["intent"], intent["entities"])
    if printing:
        for item in printing:
            bot.sendMessage(chat_id=update.message.chat_id, text=item)


def speech_to_text(name):
    wav = name+".wav"
    ogg = name+".ogg"
    # DEBUG
    call(["ffmpeg", "-loglevel", "quiet", "-i", ogg, wav])
    result = speech_request(wav)
    remove(wav)
    remove(ogg)
    # result = speech_request("test.wav")
    return result


def process_intents(user, intent, entities):

    if intent not in intent:
        return None

    # Availability
    if intent == availability:
        date = None
        for ent in entities:
            if ent["type"] == start_date:
                date = ent["entity"]
        result = sqlite_data.query(user, date)
        return result if result else ["You are free!"]

    # Create
    elif intent == create:
        date = "-"
        time = "-"
        text = "-"
        for ent in entities:
            if ent["type"] == start_date:
                date = ent["entity"]
            if ent["type"] == start_time:
                time = ent["entity"]
            if ent["type"] == title:
                text = ent["entity"]
        sqlite_data.insert(user, date, time, text)
        result = sqlite_data.all(user)
        return result
    # Delete
    elif intent == delete:
        for ent in entities:
            if ent["type"] == start_date:
                date = ent["entity"]
                sqlite_data.delete(user, date)
        result = sqlite_data.all(user)
        return result
    # Show
    elif intent == show:
        date = None
        for ent in entities:
            if ent["type"] == start_date:
                date = ent["entity"]

        result = sqlite_data.query(user, date) if date else sqlite_data.all(user)
        return result if result else ["No Appointments"]
    else:
        return ["I did not understand you!"]


def luis_request(query):
    params = {
        "subscription-key": luis_key,
        "q": query
    }
    result = requests.get(luis_url, params=params)
    if result.status_code == 200:
        result = result.json()
        return result
    else:
        return None



def speech_request(file_name):
    # Token
    headers = {
        'Ocp-Apim-Subscription-Key': api_key,
        'Content-Length': "0",
        "Content-type": "application/x-www-form-urlencoded"
    }
    api_token = requests.post(api_token_url, headers=headers).text
    # Speech to Text
    params = {
        "scenarios": "smd",
        "appid": "D4D52672-91D7-4C74-8AD8-42B1D98141A5",
        "locale": speech_lang,
        "device.os": "bot",
        "version": "3.0",
        "format": "json",
        "instanceid": uuid.uuid4(),
        "requestid": uuid.uuid4()
    }
    headers = {
        'Authorization': 'Bearer ' + api_token,
        'Content-Type': "audio/wav; codec=audio/pcm; samplerate=48000"
    }
    with open(file_name, 'rb') as obj:
        data = requests.post(api_url, params=params, headers=headers, data=obj)
    if data.status_code == 200:
        results = data.json()["results"][0]["name"]
    else:
        results = None
    return results


# Start
def main():

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(MessageHandler(Filters.text, echo))
    dispatcher.add_handler(MessageHandler(Filters.voice, audio))

    dispatcher.add_handler(MessageHandler(Filters.all, unknown))

    # log all errors
    dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
