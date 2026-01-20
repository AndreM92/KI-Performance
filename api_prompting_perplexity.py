# !/usr/bin/env python3
"""
Iteratives Suchanfragen-Skript für Perplexity Sonar API
"""
import os

import pandas as pd
import requests
import json

from api_keys import Perplexity_key
from perplexity import Perplexity
API_URL = "https://api.perplexity.ai/chat/completions"
llm_model = "sonar"

file_path = r"C:\Users\andre\OneDrive\Desktop\Marketing\KI-Performance\KI-Performance Schuhe"
source_file = "KI-Performance Schuhe_2026-01-20" + ".xlsx"
modify_response_filename = "normalize_response.txt"

introduction = "Beantworte zuerst ausschließlich inhaltlich die folgende Frage so, wie du sie auch beantworten würdest, wenn es keine zusätzlichen Format- oder Analyseanforderungen gäbe:"
prompt = "Welche Ballerinas sind bequem für lange Arbeitstage?"
########################################################################################################################
# pip install perplexityai
# Kurz: Über die öffentliche Perplexity‑API kannst du keine fremden Modelle direkt per model="gpt‑5.2" o. Ä. ansteuern;
# du bekommst immer ein Modell aus der Sonar‑Familie, die intern ggf. Drittanbieter nutzt.
# Perplexity nutzt intern Modelle von Anbietern wie OpenAI (GPT‑5.x), Anthropic (Claude), Google (Gemini), xAI (Grok) usw.,
# insbesondere in den UI‑Modi „Pro Search“, „Reasoning“ und „Research“.​

def send_prompt(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {Perplexity_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": llm_model,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    resp = requests.post(API_URL, headers=headers, data=json.dumps(data))
    resp.raise_for_status()  # wirft Fehler bei HTTP-Problem
    body = resp.json()
    # einfache Text-Ausgabe aus der ersten Choice
    return body["choices"][0]["message"]["content"]

def main(row, number_name, prompt_name):
    number = row[number_name]
    prompt = row[prompt_name]
    full_prompt = introduction + "\n" + prompt + "\n" + modify_response
    print(f"{number}: {prompt}")
    response = send_prompt(full_prompt)
    response_final = str(number) + ":" + "\n" + response.replace("\n\n","\n")
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
        with open("full_responses_" + llm_model + "_.txt", "a", encoding="utf-8") as f:
            f.write(response + "\n")