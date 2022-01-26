# Eliza Chatbot for Amazon Alexa

This is the code for the Amazon Alexa Eliza Chatbot skill. This is a published skill so you can invoke it on Amazon Echo (or any other device which supports Alexa) by saying "Alexa, open Eliza Chatbot".

# How to use the code

Amazon Alexa skills consist of 2 parts: the backend code which can run as an AWS Lambda function, and the link to the Alexa service which is defined using the Amazon Alexa Developer console. As long as you host the skill as an AWS Lambda funtion you can currently access both from the Alexa Developer console (https://developer.amazon.com/alexa/console/ask).

You will need an Amazon Alexa developer account to start with (https://developer.amazon.com). First create your skill from the Alexa developer console through which you will have access to the Lambda function code to use. The skill is implemented in Python, so  create your Lambda function from an empty Python blueprint and paste the skill code. Then fill in the rest of the mandatory fields in console such as the name, intent schema, sample utterances etc. The latter two can be taken from the comment header of the Eliza.py file. You can then test the skill using the console, or on your real device.

# Final note

This skill is made available as a very simple example only and although it works, it's been implemented a few years ago and since then Alexa APIs and skill implementation guidelines evolved. So although it still works and you can use it as a starting point, it may not follow the latest Amazon's skill implementation guidelines. Anyway, enjoy!

