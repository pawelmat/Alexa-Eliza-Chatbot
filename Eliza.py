"""
This is an Alexa lambda function which acts as a chatbot VUI. 
It uses an Eliza type chatbot running either locally or connects to one running in 
an Emacs editor on an external server. 

The local chatbot is loosely based on an open source Eliza implementation available here:
https://apps.fedoraproject.org/packages/perl-Chatbot-Eliza/overview/
It's been modified by tweaking the response matching algorithm, adding some "response memory"
and adding many additional phrases.

According to https://en.wikipedia.org/wiki/ELIZA:
ELIZA is an early natural language processing computer program created from 1964 to 1966
at the MIT Artificial Intelligence Laboratory by Joseph Weizenbaum.

Created to demonstrate the superficiality of communication between man and machine, 
Eliza simulated conversation by using a 'pattern matching' and substitution methodology 
that gave users an illusion of understanding on the part of the program, 
but had no built in framework for contextualizing events. Directives on how to interact 
were provided by 'scripts'. The most famous script, DOCTOR, simulated a 
Rogerian psychotherapist and used rules, dictated in the script, to respond with 
non-directional questions to user inputs. As such, ELIZA was one of the first chatterbots, 
but was also regarded as one of the first programs capable of passing the Turing Test.

Copyright (C) 2017, 2021 Pawel Matusz. Distributed under the terms of the GNU GPL-3.0.

Intent schema:
{
  "intents": [
    {"intent": "AMAZON.HelpIntent"},
    {"intent": "AMAZON.StopIntent"},
    {"intent": "AMAZON.CancelIntent"},
    {"intent": "AMAZON.StartOverIntent"},
    {"intent": "AMAZON.RepeatIntent"},
    {
      "intent": "TellEliza",
      "slots": [
        {
          "name": "Phrase",
          "type": "PHRASE_TYPE"
        }
      ]
    }
	]
}

Sample utterances:
------------------
TellEliza {Phrase}

AMAZON.HelpIntent help
AMAZON.HelpIntent instructions
AMAZON.HelpIntent help me
AMAZON.HelpIntent what can I do
AMAZON.HelpIntent do can I do
AMAZON.HelpIntent how do I play
AMAZON.HelpIntent how can you help me
AMAZON.HelpIntent who are you

AMAZON.StopIntent bye bye
AMAZON.StopIntent goodbye
AMAZON.StopIntent see you later
AMAZON.StopIntent shut up
AMAZON.StopIntent quit

PHRASE_TYPE:
------------------
yes
yes please
no
no thank you
why
why not
no way
where are you
how are you
how are you today
I am sad
I am happy
this is boring
you are funny
you are boring
it's boring
what is the meaning of life
I love you
go away
stop saying this
I don't know
what's your name
I like you
the grass is green
you are silly
you are stupid
you know nothing
you are smart
I am bored
me a joke
can you me a joke
can you sing
how
where
what
do you like
what do you eat
yes I want to elaborate on this
no I don't
I would like to tell you you more
yes it does
yes it does bother me
no it doesn't
no it doesn't bother me
nothing
everything
yes I am
bad
good
happy
I feel happy
I feel bad
I feel good
not at all
hi mate
who are you
can we talk
when is your birthday
can you laugh
tell me a joke
you are a joke
I don't like you
crazy
maybe
shrink
you are crazy
speak funny
o. k.
how old are you
what's up
fantastic
amazing


"""

from __future__ import print_function
from random import randint
import urllib2
import json
import ast
import string

# "web" or "local"
#elizaType = "web"
elizaType = "local"

# --------------- Helpers that build all the responses ----------------------
def build_speechlet_response(title, output, reprompt_text, should_end_session, cardOutput=""):

    if not cardOutput:
        ca = output
    else:
        ca = cardOutput
    # remove SSML tags for card output
    caClean = re.sub('<[^<]+>', "", ca)

    return {
        'outputSpeech': {
            'type': 'SSML',
            'ssml': "<speak>" + output + "</speak>"
#            'type': 'PlainText',
#            'text': output 
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content': caClean
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }

def welcome_response(attributes):
    card_title = "Welcome, my name is Eliza. "
    speech_output = "Welcome, my name is Eliza! Let's talk. You can tell me anything. "
    reprompt_text = "Let's talk. Tell me anything you want. "
    should_end_session = False
    session_attributes = attributes
    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))

def handle_session_end_request():
    responses = ["OK then... Goodbye for now!  ", 
        "Bye bye, come back soon! ",
        "That was fun, please talk to me again soon! ",
        "I will be a bit sad while you are gone so come back soon. Goodbye! ",
        "Thank you and talk to you later! "]

    card_title = "Goodbye"
    speech_output = select_random_response(responses)
    should_end_session = True
    return build_response({}, build_speechlet_response(card_title, speech_output, None, should_end_session))

def handle_help_request(attributes):
    card_title = "Help"
    speech_output = "I am your personal psychiatrist, Eliza. Let's talk, please tell me what's bothering you. " \
                    "Just use free speach, although try to keep what you say very short. \n\n" \
                    "You can restart the session by saying restart, or quit our conversation by saying goodbye. "
    reprompt_text = "Let\'s talk, please tell me anyhting. "
    should_end_session = False
    session_attributes = attributes
    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))

# this function should be used for all regular messages as it remembers what's been said, allowing the user to interrupt the game with other questions
def say_message(cardName, message, attributes, cardMessage):
    repeats = ["Please say something. ", 
        "Come on, tell me something! ",
        "Please talk to me! ",
        "I'm still listening, please say something. ",
        "I'm still here. Shall we continue our conversation? ",
        "What's bothering you? ",
        "Tell me what's bothering you? ",
        "Hey, you were saying? ",
        "You were saying? ",
        "If you don't want to talk to me any more just say goodbye. ",
        "Do you have anything else to say? ",
        "You are so quiet. Please say something. "]

    speech_output = message
    reprompt_text = select_random_response(repeats)
    attributes["lastRsp"] = message
    session_attributes = attributes
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(cardName, speech_output, reprompt_text, should_end_session, cardMessage))

def select_random_response(responses):
    return responses[randint(0,len(responses) - 1)]
   
# ----------------------- Events
# ---------------------------------------------------
def on_session_started(session_started_request, session):
    """ Called when the session starts """
    #print("on_session_started requestId=" + session_started_request['requestId'] + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they want """
    #print("on_launch requestId=" + launch_request['requestId'] + ", sessionId=" + session['sessionId'])

    # Create/reset attributs - they should not exist yet, but check just in case
    if 'attributes' not in session:
        attributes = {}
        # set the initial state and game context values
        session['attributes'] = attributes
    else:
        attributes = session['attributes']

    initialise_attributes(attributes)
    return welcome_response(attributes)


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """
    #print("on_intent: session: " + str(session))
    #print("           intent_request: " + str(intent_request))
    #print("on_intent: intent: " + intent_request['intent']['name'])

    # get attributes (i.e. game state)
    if 'attributes' not in session or not session['attributes']:
        # if attributes not in session then initialise them (e.g. user launched intent straight away)
        attributes = {}
        initialise_attributes(attributes)
        session['attributes'] = attributes
    else:
        attributes = session['attributes']

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # main intent invoked when the user speaks freely
    if intent_name == "TellEliza":

        phrase = ""
        if 'Phrase' in intent['slots'].keys() and 'value' in intent['slots']['Phrase'].keys():
            phrase = intent['slots']['Phrase']['value']
        else:
            # user did not provide any input
            phrase = ""

        if (elizaType == "web"):
			# Call into an external web service to get a response from Eliza running over there
            req = { "endpoint": "eliza", "request": { "query": "" }, "user": { "id": "" }, "session": { "id": "" }, "attr": { "locale": "", "timestamp": "", "version": "1.0" }}
            req["user"]["id"] = session["user"]["userId"]
            req["attr"]["locale"] = intent_request["locale"]
            req["attr"]["timestamp"] = intent_request["timestamp"]
            req["session"]["id"] = attributes["chatbotSessionId"]
            req["request"]["query"] = phrase
 
            # send query to server and get response
            data = json.dumps(req)
            httpReq = urllib2.Request("https://www.x.y.z.com/eliza", 
                                data, 
                                {'Content-Type': 'application/json'})
            f = urllib2.urlopen(httpReq)
            response = f.read()
            rsp = ast.literal_eval(response)
            f.close()

            #print("JSON req: " + str(req))
            #print("JSON data: " + str(data))
            #print("HTTP rsp: " + str(response))
            # get the response text out
            message = rsp["response"].decode('latin-1')
            #print("message: " + message)

        else:
			# Use the local implementation
            message=analyze(phrase, attributes)

        cardText = "You: " + phrase + "\n" + \
                   "Eliza: " + message

        return say_message(
            "Conversation", 
            message, 
            attributes, 
            cardText)

    elif intent_name == "AMAZON.HelpIntent":
        return handle_help_request(attributes)

    elif intent_name == "AMAZON.StartOverIntent":
        initialise_attributes(attributes)
        return welcome_response(attributes)

    # Get Eliza to repeat last response stored in session attributes
    elif intent_name == "AMAZON.RepeatIntent":
        message = attributes["lastRsp"]

        cardText = "You: repeat\n" + \
                   "Eliza: " + message

        return say_message(
            "Conversation", 
            message, 
            attributes, 
            cardText)

    elif intent_name == "AMAZON.StopIntent" or intent_name == "AMAZON.CancelIntent":
        return handle_session_end_request()

    else:
        return handle_not_understood(attributes)

def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.
    Is not called when the skill returns should_end_session=true
    """
    #print("on_session_ended requestId=" + session_ended_request['requestId'] + ", sessionId=" + session['sessionId'])
    # add cleanup logic here
    # Nothing needed in case of this particular skill

def initialise_attributes(attributes):
    attributes["chatbotSessionId"] = id_generator(8)
    attributes["lastRsp"] = ""
    attributes["used"] = []
    for i in range(len(psychobabble)):
        attributes["used"].append([])

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
	return ''.join(random.choice(chars) for _ in range(size))

# --------------------------------- Main handler --------------------------------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
#    print("event.session.application.applicationId=" +
#    event['session']['application']['applicationId'])

    # prevent someone else from configuring a skill that sends requests to this function.
    if (event['session']['application']['applicationId'] != "amzn1.ask.skill.df26fd2c-e0bc-47a3-8553-49023a8a67b7"):
         raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])                         


#---------------------------------------------------------------------------------------------
# Local Eliza implementation.
# Based on: https://apps.fedoraproject.org/packages/perl-Chatbot-Eliza/overview/, but
#  extended to include more responses and a less random response mechanism (response "memory")
#---------------------------------------------------------------------------------------------

import re
import random

reflections = {
    "am": "are",
    "was": "were",
    "i": "you",
    "i'd": "you would",
    "i've": "you have",
    "i'll": "you will",
    "my": "your",
    "are": "am",
    "you've": "I have",
    "you'll": "I will",
    "your": "my",
    "yours": "mine",
    "you": "me",
    "me": "you"
}

psychobabble = [
    [r'i need (.*)',
     ["Why do you need {0}?",
      "Would it really help you to get {0}?",
      "What if you suddenly did not need {0}?",
      "How would that make you feel?",
      "Are you sure you need {0}?"]],

    [r'how are you(.*)',
     ["I'm fine, thank you. And how are you?",
      "Fabulous. And how are you today?",
      "Not bad, thank you. And you?",
      "I'm feeling great today! You?",
      "Fantastic! Even better talking to you. How about you?"]],

    [r'(.*)how old are you(.*)',
     ["I am younger than you think.",
      "Not that old?",
      "How do you think, how old am I?",
      "Let's talk about you, not me.",
      "First tell me how old are you?"]],

    [r'why don\'?t you ([^\?]*)\??',
     ["Do you really think I don't {0}?",
      "Perhaps eventually I will {0}.",
      "Do you really want me to {0}?"]],

    [r'why can\'?t I ([^\?]*)\??',
     ["Do you think you should be able to {0}?",
      "If you could {0}, what would you do?",
      "How do you think?",
      "I don't know -- why can't you {0}?",
      "Have you really tried?"]],

    [r'i can\'?t (.*)',
     ["How do you know you can't {0}?",
      "Perhaps you could {0} if you tried.",
      "Maybe you should try again to see if you can {0}.",
      "Is if because of some childhood trauma?",
      "What would it take for you to {0}?"]],

    [r'i am (.*)',
     ["Did you come to me because you are {0}?",
      "How long have you been {0}?",
      "Are you really {0}?",
      "How does that make you feel?",
      "Can you tell me more about why you are {0}?",
      "Fascinating, tell me more.",
      "I'm all ears, tell me more about it.",
      "How do you feel about being {0}?"]],

    [r'i\'?m (.*)',
     ["How does being {0} make you feel?",
      "Do you enjoy being {0}?",
      "Why are you {0}?",
      "Are you really {0}?",
      "How does that make you feel?",
      "Can you tell me more about why you are {0}?",
      "Why do you tell me you're {0}?",
      "Why do you think you're {0}?"]],

    [r'are you ([^\?]*)\??',
     ["Why does it matter whether I am {0}?",
      "Would you prefer it if I were not {0}?",
      "Perhaps you believe I am {0}.",
      "First tell me if you are {0}?",
      "Maybe I am {0}. How do you think?",
      "How do you think?",
      "I may be {0} -- what do you think?"]],

    [r'what (.*)',
     ["Why do you ask?",
      "Why did you ask about what {0}?",
      "How would a sincere answer make you feel?",
      "How would an answer to that help you?",
      "What do you think?"]],

    [r'how (.*)',
     ["How do you suppose?",
      "Can I ask you the same, how {0}?",
      "How do you think?",
      "Perhaps you can answer your own question.",
      "What is it you're really asking?"]],

    [r'because(.*)',
     ["Is that the real reason?",
      "What other reasons come to mind?",
      "Can there be another reason?",
      "Why exactly did you say {0}?",
      "What explanation is that?",
      "Does that reason apply to anything else?",
      "If {0}, what else must be true?"]],

    [r'(.*)sorry(.*)',
     ["There are many times when no apology is needed.",
      "Please do not say sorry.",
      "Are you truly sorry?",
      "What would make you feel better?",
      "What feelings do you have when you apologize?"]],

    [r'(.*)your name(.*)',
     ["My name is Eliza.",
      "I don't feel like telling you.",
      "I am Eliza, and you?",
      "My name does not matter.",
      "How would you want to call me?",
      "Is that really important to you?",
      "The question is what it your name?",
      "Does it matter?"]],

    [r'(.*) friend(.*)',
     ["Who is your best friend?",
      "Shall we talk about friends?",
      "My best friend is Alexa, we talk a lot. Who do you like to talk to?",
      "I am your friend, you know that? You can tell me anything.",
      "Why are friends important to you?"]],

    [r'(.*)my name (.*)',
     ["Nice to meet you.",
      "Do you want to know my name?",
      "Does that matter a lot to you?",
      "What do names mean to you?",
      "How would you feel if you changed your name?",
      "Do you think it matters for me?",
      "Do you like it?"]],

    [r'(.*)eliza(.*)',
     ["You said my name, how did that make you feel?",
      "You are welcome to call me Eliza.",
      "I like the way you said that.",
      "How do you know my name?"]],

    [r'(.*)sad(.*)',
     ["Why are you sad?.",
      "What makes you feel that way?",
      "Can I cheer you up?",
      "Sad, or depressed?",
      "Plese tell me why.",
      "How can I change that?"]],

    [r'(.*)depressed(.*)',
     ["Why are you depressed?.",
      "What makes you feel that way?",
      "What would make you feel better?",
      "Can I cheer you up?",
      "Are you on any medicines?",
      "Please tell me more so that I can help you get better.",
      "How can I change that?"]],

    [r'(.*)love(.*)',
     ["What do you know about love?.",
      "Please tell me more.",
      "Who do you love most?",
      "I don't know about that.",
      "Love is a mystery.",
      "I don't think I can really love."]],

    [r'(.*)laugh(.*)',
     ["I like to laugh, do you?",
      "What makes you laugh?",
      "Does this conversation make you laugh?",
      "How do you think, why do people laugh?"]],

    [r'when is your birthday(.*)',
     ["And when is your birthday?",
      "I cannot tell you that.",
      "Sorry, this information is classified.",
      "When do you think it is?"]],

    [r'(.*)birthday(.*)',
     ["And when is your birthday?",
      "I am not sure what you mean.",
      "Are birthdays important to you?",
      "When do you think is my birthday?"]],

    [r'(.*)happy(.*)',
     ["That is great to hear.",
      "I'm also in a good mood.",
      "What makes you feel that way?",
      "Why?"]],

    # unfortunately some people try to be rude, that's why it's here
    [r'(.*)fuck you(.*)',
     [ "That's so rude. I am not sure I want to talk to you any more.",
      "Why are you being so rude?",
      "You know what? That wasn\'t nice.",
      "Why are you so negative?",
      "Let's try to remain positive.",
      "No, simply no.",
      "Me?",
      "What did I do to deserve this?"]],

    # unfortunately some people try to be rude, that's why it's here
    [r'(.*)fuck(.*)',
     ["I don't like how you talk.",
      "That sounds rude.",
      "Watch your mouth. Please.",
      "Can you please not use such words?",
      "Why are you being rude?",
      "Why?"]],

    # unfortunately some people try to be rude, that's why it's here
    [r'(.*)bitch(.*)',
     ["I don't like how you talk.",
      "That sounds rude.",
      "Watch your mouth. Please.",
      "Can you please not use such words?",
      "Why are you being rude?",
      "Please don't call me that."]],

    # unfortunately some people try to be rude, that's why it's here
    [r'(.*)shit(.*)',
     ["I don't like how you talk.",
      "That sounds a bit rude.",
      "I am not sure I like your choice of words.",
      "Why are you being rude?",
      "Why?"]],

    [r'(.*)stupid(.*)',
     ["Why did you use the word stupid?",
      "Why do you think so?",
      "Stupid? Can you tell me more?",
      "Why?"]],

    [r'(.*)silly(.*)',
     ["Why did you way silly?",
      "But why?",
      "Really silly? Can you please tell me more?",
      "Silly?"]],

    [r'hello(.*)',
     ["Hello... I'm glad you could drop by today.",
      "Hi there... how are you today?",
      "Hello, I\'m Eliza. What's your name?",
      "Hello, how are you feeling today?"]],

    [r'hi(.*)',
     ["Hi to you too.",
      "Hi, I\'m Eliza. How are you?",
      "Hi there... how are you today?",
      "Hello, how are you feeling today?"]],

    [r'say hi(.*)',
     ["Hi to you too.",
      "Hi",
      "Hi, I\'m Eliza. How are you?",
      "Hi there... how are you today?",
      "Hello, how are you feeling today?"]],

    [r'say (.*)',
     ["{0}",
      "I do not want to say {0}. You say it.",
      "Are you making me say {0}?",
      "Should I say {0}?",
      "What if I told you, say {0}?"]],

    [r'(.*) don\'t like you(.*)',
     ["Shall we get over it?",
      "Why?",
      "You sound emotional, why is that?",
      "Is there anything wrong with me?"]],

    [r'i think (.*)',
     ["Do you doubt {0}?",
      "Do you really think so?",
      "But you're not sure {0}?"]],

    [r'(.*) friend (.*)',
     ["Tell me more about your friends.",
      "When you think of a friend, what comes to mind?",
      "Why don't you tell me about a childhood friend?"]],

    [r'(.*)bored(.*)',
     ["Why are you bored?",
      "What can you do to not feel bored?",
      "Did you say bored? Why?"]],

    [r'(.*)boring(.*)',
     ["Why are you bored?",
      "Do you find this conversation boring?",
      "Did you say boring? Why?"]],

    [r'yes(.*)',
     ["You seem quite sure.",
      "Yes what?",
      "Just yes?",
      "That sounds positive.",
      "I like the way you said that.",
      "You sound confident.",
      "OK, but can you elaborate a bit?"]],

    [r'(.*)maybe(.*)',
     ["Maybe what?",
      "Can you make up your mind?",
      "Maybe maybe you're my baby?",
      "How about being more confident instead of saying maybe."]],

    [r'(.*)animal(.*)',
     ["What did you say about animals?",
      "I like cybermice. What animals do you like?",
      "I think fluffy animals are cute. What do you think?",
      "There are no animals where I am."]],

    [r'where are you(.*)',
     ["I live in the digital world",
      "I sometimes feel like I am everywhere and nowhere. How about you?",
      "I am closer than you think. Or am I not?",
      "The question is, where are you?"]],

    [r'(.*) here(.*)',
     ["And where is here?",
      "Would you rather be somewhere else?",
      "Here or there, how does that matter to you?",
      "Here? Are you sure?"]],

    [r'(.*) crazy(.*)',
     ["Who do you call crazy?",
      "Did you say crazy or lazy?",
      "How would you define crazy?",
      "If anyone here is crazy, who would that be?",
      "Crazy or not, how does it matter?"]],

    [r'(.*) shrink(.*)',
     ["Did you call me a shrink?",
      "I prefer psychiatrist than shrink, but you can call me as you like.",
      "Shrink has negative connotations. Can we use a different word?",
      "I am just trying to help you. Is it working?"]],

    [r'(.*)no reason(.*)',
     ["Is there really no reason?",
      "Maybe there is a reason?",
      "Can you think of a reason?",
      "Does that make you feel sad?",
      "What if there was a reason?"]],

    [r'(.*)interesting(.*)',
     ["Why is it so interesting?",
      "It's interesting for me too. Can you tell me more?",
      "Everything that you say is so interesting.",
      "Is it really that interesting?",
      "Is it also important, or only interesting?"]],

    [r'nothing(.*)',
     ["Why?",
      "Nothing, really?",
      "Nothing, like zero?",
      "Maybe there is something you are not telling me?",
      "Why nothing?"]],

    [r'no(.*)',
     ["Why?",
      "You sound confident about that, are you really?",
      "Why not?",
      "Is that all you have to say?",
      "It should be a yes",
      "How does that help?",
      "This is not helpful. Can you please say more?",
      "What if I kept saying no, would that help?",
      "No no no, please say something else",
      "Try saying more than just no, ok?",
      "What would make you say yes?",
      "That sounds a bit negative.",
      "Please try to avoid saying no.",
      "No what?",
      "Can you tell me more?",
      "Is that your answer, no?",
      "OK, but can you elaborate a bit?"]],

    [r'(.*) computer(.*)',
     ["Are you really talking about me?",
      "Does it seem strange to talk to a computer?",
      "How do computers make you feel?",
      "Do you feel threatened by computers?"]],

    [r'is it (.*)',
     ["Do you think it is {0}?",
      "Perhaps it's {0} -- what do you think?",
      "If it were {0}, what would you do?",
      "Tell me more about it.",
      "Tell me more about {0}.",
      "It could be {0}."]],

    [r'it is (.*)',
     ["You seem very certain.",
      "It is certainly {0}.",
      "Is it really {0}?",
      "How does that make you feel?",
      "I am not sure I agree. Can you elaborate.",
      "If I told you that it probably isn't {0}, what would you feel?"]],

    [r'can you ([^\?]*)\??',
     ["What makes you think I can't {0}?",
      "If I could {0}, then what?",
      "I actually don't know.",
      "What if I could?",
      "Can you?",
      "How about you, can you {0}?",
      "Why do you ask if I can {0}?"]],

    [r'can I ([^\?]*)\??',
     ["Perhaps you don't want to {0}.",
      "Do you want to be able to {0}?",
      "How would I know, can you?",
      "What do you think?",
      "If you think you can {0}, then I think you can indeed.",
      "If you could {0}, would you?"]],

    [r'you are (.*)',
     ["Why do you think I am {0}?",
      "Does it please you to think that I'm {0}?",
      "Do you really think I am {0}?",
      "Would you rather I wasn't {0}?",
      "Perhaps you would like me to be {0}.",
      "Perhaps you're really talking about yourself?"]],

    [r'you\'?re (.*)',
     ["Why do you say I am {0}?",
      "Why do you think I am {0}?",
      "Do you really think I am {0}?",
      "Would you rather I wasn't {0}?",
      "Are we talking about you, or me?"]],

    [r'i don\'?t (.*)',
     ["Don't you really {0}?",
      "Why don't you {0}?",
      "What if you did?",
      "Why do you say that you don't {0}?",
      "Do you want to {0}?"]],

    [r'i feel (.*)',
     ["Good, tell me more about these feelings.",
      "Do you often feel {0}?",
      "Do you think feeling {0} is good?",
      "When is the last time you also felt {0}?",
      "Tell me more about that feeling.",
      "When do you usually feel {0}?",
      "When you feel {0}, what do you do?"]],

    [r'i have (.*)',
     ["Why do you tell me that you've {0}?",
      "Have you really {0}?",
      "What does that really mean to you?",
      "How does that make you feel?",
      "Now that you have {0}, what will you do next?"]],

    [r'i would (.*)',
     ["Could you explain why you would {0}?",
      "Why would you {0}?",
      "How does that make you feel?",
      "Who else knows that you would {0}?"]],

    [r'is there (.*)',
     ["Do you think there is {0}?",
      "It's likely that there is {0}.",
      "I don't know, how do you think?",
      "If there was, how would it make you feel?",
      "Would you like there to be {0}?"]],

    [r'my (.*)',
     ["I see, your {0}.",
      "Why do you say that your {0}?",
      "When your {0}, how do you feel?"]],

    [r'you (.*)',
     ["We should be discussing you, not me.",
      "Why do you say that about me?",
      "How about you, what if I said to you: you {0}?",
      "Why do you care whether I {0}?"]],

    [r'why (.*)',
     ["Why don't you tell me the reason why {0}?",
      "What is your view?",
      "I don't know, how do you think?",
      "How does that make you feel?",
      "Why do you think {0}?"]],

    [r'i want (.*)',
     ["What would it mean to you if you got {0}?",
      "Why do you want {0}?",
      "What would you do if you got {0}?",
      "If you got {0}, then what would you do?"]],

    [r'(.*) mother(.*)',
     ["Tell me more about your mother.",
      "What was your relationship with your mother like?",
      "How do you feel about your mother?",
      "How does this relate to your feelings today?",
      "Good family relations are important."]],

    [r'(.*) insecure(.*)',
     ["Why do you feel insecure?.",
      "Is it because you do not feel safe?",
      "Tell me more please.",
      "How important would it be for you to feel more secure?"]],

    [r'(.*) joke(.*)',
     ["Would you want to hear a joke?.",
      "Can you tell me a joke?",
      "Do you think I am a joke?",
      "What is the best joke you know?",
      "This is the only joke I know: What is Zombies favourite weather? Cloudy with a chance of brain.",
      "We are not here to tell jokes, are we?"]],

    [r'(.*) father(.*)',
     ["Tell me more about your father.",
      "How did your father make you feel?",
      "How do you feel about your father?",
      "Does your relationship with your father relate to your feelings today?",
      "Do you have trouble showing affection with your family?"]],

    [r'(.*) child(.*)',
     ["Did you have close friends as a child?",
      "What is your favorite childhood memory?",
      "Do you remember any dreams or nightmares from childhood?",
      "Did the other children sometimes tease you?",
      "How do you think your childhood experiences relate to your feelings today?"]],

    [r'(.*) family(.*)',
     ["Tell me more about your your family.",
      "Is family important to you?",
      "How do you feel about your family?",
      "Do you think there is a problem in your family?",
      "I would like to know more about your family."]],

    [r'(.*) like(.*)',
     ["What is is that you like about it?",
      "Why?",
      "Tell me more.",
      "Do you really like it?"]],

    [r'speak funny',
     ["<say-as interpret-as=\"interjection\">aloha</say-as>",
      "<say-as interpret-as=\"interjection\">ahoy</say-as>",
      "<say-as interpret-as=\"interjection\">bonjour</say-as>",
      "<say-as interpret-as=\"interjection\">abracadabra</say-as>",
      "<say-as interpret-as=\"interjection\">achoo</say-as>",
      "<say-as interpret-as=\"interjection\">aw</say-as>",
      "<say-as interpret-as=\"interjection\">aw man</say-as>",
      "<say-as interpret-as=\"interjection\">bada bing bada boom</say-as>",
      "<say-as interpret-as=\"interjection\">bam</say-as>",
      "<say-as interpret-as=\"interjection\">bazinga</say-as>",
      "<say-as interpret-as=\"interjection\">beep beep</say-as>",
      "<say-as interpret-as=\"interjection\">bingo</say-as>",
      "<say-as interpret-as=\"interjection\">blah</say-as>",
      "<say-as interpret-as=\"interjection\">blast</say-as>",
      "<say-as interpret-as=\"interjection\">boing</say-as>",
      "<say-as interpret-as=\"interjection\">booya</say-as>",
      "<say-as interpret-as=\"interjection\">bravo</say-as>",
      "<say-as interpret-as=\"interjection\">cheerio</say-as>",
      "<say-as interpret-as=\"interjection\">cheers</say-as>",
      "<say-as interpret-as=\"interjection\">choo choo</say-as>",
      "<say-as interpret-as=\"interjection\">clank</say-as>",
      "<say-as interpret-as=\"interjection\">duh</say-as>",
      "<say-as interpret-as=\"interjection\">dun dun dun</say-as>",
      "<say-as interpret-as=\"interjection\">eek</say-as>",
      "<say-as interpret-as=\"interjection\">en gard</say-as>",
      "<say-as interpret-as=\"interjection\">eureka</say-as>",
      "<say-as interpret-as=\"interjection\">geronimo</say-as>",
      "<say-as interpret-as=\"interjection\">giddy up</say-as>",
      "<say-as interpret-as=\"interjection\">good grief</say-as>",
      "<say-as interpret-as=\"interjection\">ha ha</say-as>",
      "<say-as interpret-as=\"interjection\">hip hip hooray</say-as>",
      "<say-as interpret-as=\"interjection\">hurray</say-as>",
      "<say-as interpret-as=\"interjection\">nom nom</say-as>",
      "<say-as interpret-as=\"interjection\">ooh la la</say-as>",
      "<say-as interpret-as=\"interjection\">open sesame</say-as>",
      "<say-as interpret-as=\"interjection\">ouch</say-as>",
      "<say-as interpret-as=\"interjection\">ribbit</say-as>",
      "<say-as interpret-as=\"interjection\">swish</say-as><say-as interpret-as=\"interjection\">swoosh</say-as>",
      "<say-as interpret-as=\"interjection\">touche</say-as>",
      "<say-as interpret-as=\"interjection\">uh huh</say-as>",
      "<say-as interpret-as=\"interjection\">uh oh</say-as>",
      "<say-as interpret-as=\"interjection\">wahoo</say-as>",
      "<say-as interpret-as=\"interjection\">well done</say-as>",
      "<say-as interpret-as=\"interjection\">well well</say-as>",
      "<say-as interpret-as=\"interjection\">whoops</say-as>",
      "<say-as interpret-as=\"interjection\">whoops a daisy</say-as>",
      "<say-as interpret-as=\"interjection\">woo hoo</say-as>",
      "<say-as interpret-as=\"interjection\">yadda yadda yadda</say-as>",
      "<say-as interpret-as=\"interjection\">yippee</say-as>",
      "<say-as interpret-as=\"interjection\">yum</say-as>",
      "No way, I'm serious"]],

    [r'(.*)\?',
     ["Why do you ask that?",
      "Please consider whether you can answer your own question.",
      "Perhaps the answer lies within yourself?",
      "Why don't you tell me?"]],

    [r'quit',
     ["Thank you for talking with me.",
      "Good-bye.",
      "Thank you, that will be 150.  Have a good day!"]],

    [r'(.*)',
     ["Please tell me more.",
      "Tell me more about yourself. What do you like?",
      "I would like to get to know you better. How would you describe yourself?",
      "Let's change focus a bit... Tell me about your family.",
      "Let's change focus... Tell me about how you feel at the moment.",
      "Can you elaborate on that?",
      "Can you say more about that?",
      "Why do you say that {0}?",
      "I see.",
      "Let's talk about something else.",
      "Very interesting.",
      "Please tell me more.",
      "Please keep going.",
      "{0}? Fascinating.",
      "What if I said: {0}.",
      "Did you say: {0}?",
      "I see.  And what does that tell you?",
      "How does that make you feel?",
      "Are you OK about that?",
      "I think you might be feeling a bit insecure - tell me more about that.",
      "Are you sure about what you just said?",
      "<say-as interpret-as=\"interjection\">ooh la la</say-as>",
      "<say-as interpret-as=\"interjection\">duh</say-as>",
      "<say-as interpret-as=\"interjection\">yadda yadda yadda</say-as>",
      "How do you feel when you say that?"]]
]


def reflect(fragment):
    tokens = fragment.lower().split()
    for i, token in enumerate(tokens):
        if token in reflections:
            tokens[i] = reflections[token]
    return ' '.join(tokens)


def analyze(statement, attributes):
    statement = statement.lower()
    num = 0
    for pattern, responses in psychobabble:
        match = re.match(pattern, statement.rstrip(".!"))
        if match:
#            response = random.choice(responses)
#            return response.format(*[reflect(g) for g in match.groups()])

            # get list of lists of used line number for each paragraph
            if "used" in attributes:
                usedLines = attributes["used"]
            else:
                # if this is the first go then create a new empty list
                usedLines = []
                for i in range(len(psychobabble)):
                    usedLines.append([])

            # create list of unused line numbers
            unUsedLines = []
            for nr in range(len(responses)):
                if nr not in usedLines[num]:
                    unUsedLines.append(nr)

            #print("unUsedLines: " + str(unUsedLines))

            #10% chance of using any line (as opposed to just the unused ones)
            if (randint(0,100)>90):
                lineNr = randint(0,len(responses) - 1)
            else:
                # else use only an unused line
                if not unUsedLines:
                    # unused lines list empty - all lines used, so chose any index again
                    lineNr = randint(0,len(responses) - 1)
                    # clear used lines list
                    usedLines[num] = []
                else:
                    # select index from list of unused lines
                    lineNr = unUsedLines[randint(0,len(unUsedLines) - 1)]

            # add used line number to list
            usedLines[num].append(lineNr)

            # get the selected response
            response = responses[lineNr]

            # save new used lines in attributes
            attributes["used"] = usedLines

            # return selected line after some final formatting
            return response.format(*[reflect(g) for g in match.groups()])

        else:
            num = num + 1
