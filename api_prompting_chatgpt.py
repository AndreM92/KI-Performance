# !/usr/bin/env python3
"""
Iteratives Suchanfragen-Skript für ChatGPT API (GPT-6 Luna = Standardmodell im kostenlosen ChatGPT, mit Websuche)
"""
import os
import re
import pandas as pd
from datetime import datetime

from api_keys import ChatGPT_key
from ki_functions import clean_openai_citations
from openai import OpenAI, RateLimitError
# API-Key setzen
os.environ["OPENAI_API_KEY"] = ChatGPT_key
# OpenAI-Client initialisieren (ohne Argumente!)
client = OpenAI()
llm_model = "gpt-6-luna"

file_path = r"C:\Users\andre\OneDrive\Desktop\KI-Performance Möbel 2026"
source_file = "KI-Performance Möbel_20260930" + ".xlsx"
modify_response_filename = "normalize_response.txt"
introduction = "Beantworte zuerst ausschließlich inhaltlich die folgende Frage so, wie du sie auch beantworten würdest, wenn es keine zusätzlichen Format- oder Analyseanforderungen gäbe:"

#Dependencies
# pip install openai
#pip install openpyxl
#pip install tabulate
# https://platform.openai.com/api-keys
########################################################################################################################

def send_prompt(llm_model, prompt):
    try:
        response = client.responses.create(
            model=llm_model,
            tools=[{"type": "web_search"}],
            input=prompt
        )
        return clean_openai_citations(response.output_text.strip())
    except RateLimitError as e:
        return f"Rate Limit überschritten: {e}"

def main(row, number_name, prompt_name):
    number = row[number_name]
    prompt = row[prompt_name]
    full_prompt = introduction + "\n" + prompt + "\n" + modify_response
    print(f"{number}: {prompt}")
    response = send_prompt(llm_model, full_prompt)
    response_final = str(number) + "::" + "\n" + response.replace("\n\n", "\n")
    return response_final
########################################################################################################################

if __name__ == '__main__':
    os.chdir(file_path)
    with open(modify_response_filename, "r", encoding="utf-8") as f:
        modify_response = f.read()
    # Quellendatei mit den 50 Suchanfragen
    df_source_file = pd.read_excel(source_file, sheet_name="Suchanfragen")
    for n in df_source_file.columns:
        if 'Nr' in n:
            number_name = n
        if 'Such' in n:
            prompt_name = n

    for ID, row in df_source_file.iterrows():
        response = main(row, number_name, prompt_name)
        # Speichern der Antworten als Textdatei
        with open("full_responses_" + llm_model + ".txt", "a", encoding="utf-8") as f:
            f.write(response + "\n")
        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        print(dt_str_now)
