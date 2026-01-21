
import os
import re
import pandas as pd

from api_keys import ChatGPT_key
from openai import OpenAI, RateLimitError
# API-Key setzen
os.environ["OPENAI_API_KEY"] = ChatGPT_key
# OpenAI-Client initialisieren (ohne Argumente!)
client = OpenAI()
########################################################################################################################
#Dependencies
# pip install openai
#pip install openpyxl
#pip install tabulate
# https://platform.openai.com/api-keys

def gpt_chat(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except RateLimitError as e:
        return f"Rate Limit überschritten: {e}"

if __name__ == '__main__':
    while True:
        user_input = str(input("You: "))
        if user_input.lower() in ['exit', 'bye']:
            break
        response = gpt_chat(user_input)
        print(response)