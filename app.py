import os
import sys
import json
import tweepy
import numpy as np
from textblob import TextBlob

import requests
from flask import Flask, request

app = Flask(__name__)

consumer_key = 'anF38Tu0Ln3Xdrtf2JoX14d5Q'
consumer_secret = 'Po6XOwa2PwE4HxyPLJQAQaNmCMGerkmdUnqJoNB0sKgWhk3Jjo'

access_token = '2286218053-ShtlhU0eayuqFhTUQFBbFJQVGIXLzwHCobDL8SP'
access_token_secret = 'qHDC0SWla6zPJ3xkC6AoQDknnykulVOkPLL49LH6ErEtb'



@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text

                    #help_button(sender_id)

                    if message_text.lower() == "help" or message_text.lower() == "hi" or message_text.lower() == "hello" or message_text.lower() == "hey":
                        send_message(sender_id, "Hi! Type in a phrase and I'll tell you how people are feeling about it by parsing through the last thousand tweets containing your phrase. Sentiment values range from 0 to 10, where 0 is super negative and 10 is super positive.")
                        break

                    send_message(sender_id, "Calculating sentiment for " + message_text + "...")

                    result = analyze(message_text)
                    try:
                        score = float(result)
                        send_message(sender_id, "People are feeling " + score_func(score) + ". The numeric value is " + str(scale(score)) + " out of 10.")
                    except ValueError:
                        send_message(sender_id, result)

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "ok", 200

def help_button(sender_id):
    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }

    data = json.dumps({
       "recipient": {
            "id": sender_id
        },
        "message":{
            "quick_replies":[
                {
                "content_type":"text",
                "title":"Help",
                "payload":"Help"
                }
            ]
        }
    })

    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)

def scale(score):
    return 5 * score + 5

def score_func(score):
    if score < -0.5:
        return "really negative"
    if score < -0.1:
        return "pretty negative"
    if score < -0.08:
        return "quite negative"
    if score < -0.04:
        return "negative"
    if score < 0:
        return "slightly negative"
    if score == 0:
        return "neutral"
    if score > 0.5:
        return "really positive"
    if score > 0.1:
        return "pretty positive"
    if score > 0.08:
        return "quite positive"
    if score > 0.04:
        return "positive"
    if score > 0:
        return "slightly positive"


def analyze(message_text):
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    api = tweepy.API(auth)

    query = message_text
    count = 100
    searched_tweets = []
    last_id = -1
    max_tweets = 1000
    while len(searched_tweets) < max_tweets:
        count = max_tweets - len(searched_tweets)
        try:
            new_tweets = api.search(q=query, count=count, max_id=str(last_id - 1))
            if not new_tweets:
                break
            searched_tweets.extend(new_tweets)
            last_id = new_tweets[-1].id
        except tweepy.TweepError as e:
            # depending on TweepError.code, one may want to retry or wait
            # to keep things simple, we will give up on an error
            break

    polarity = []
    subjectivity = []
    count = 0
    for tweet in searched_tweets:
      analysis = TextBlob(tweet.text)
      #print(analysis.sentiment)
      if not (analysis.sentiment.polarity == 0 and analysis.sentiment.subjectivity == 0):
          polarity.append(analysis.sentiment.polarity)
          subjectivity.append(analysis.sentiment.subjectivity)
          count += 1

    if count == 0:
      return ("No one's really tweeting about " + query + ".")
    else:
      return str(np.dot(polarity, subjectivity)/count)

def send_message(recipient_id, message_text):

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
