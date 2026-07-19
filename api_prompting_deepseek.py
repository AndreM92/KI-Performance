#!/usr/bin/env python3
"""
Iteratives Suchanfragen-Skript für DeepSeek API
"""
import os
import time
from datetime import datetime

import pandas as pd
from openai import OpenAI, RateLimitError

# API-Key aus separater Datei einlesen
from api_keys import DeepSeek_key

# OpenAI-Client für DeepSeek initialisieren
client = OpenAI(
    api_key=DeepSeek_key,
    base_url="https://api.deepseek.com",   # DeepSeek-Endpunkt
)

# Aktuellstes Chat-Modell von DeepSeek (immer die neueste Version)
# llm_model = "deepseek-chat"
llm_model = "deepseek-v4-flash"

file_path = r"C:\Users\andre\OneDrive\Desktop\KI-Performance Arzneimittel 2026"
source_file = "KI-Performance Arzneimittel_20260715" + ".xlsx"
modify_response_filename = "normalize_response.txt"
introduction = (
    "Beantworte zuerst ausschließlich inhaltlich die folgende Frage so, "
    "wie du sie auch beantworten würdest, wenn es keine zusätzlichen "
    "Format- oder Analyseanforderungen gäbe:")

# Dependencies
# pip install openpyxl
# pip install pandas
# https://platform.deepseek.com/api_keys
###############################################################################

def send_prompt(llm_model, prompt):
    """
    Sendet einen Prompt an die DeepSeek-API und gibt die Antwort als Text zurück.
    """
    try:
        response = client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        )
        # Antworttext aus der ersten (einzigen) Choice extrahieren
        return response.choices[0].message.content.strip()
    except RateLimitError as e:
        return f"Rate Limit überschritten: {e}"
    except Exception as e:
        # Allgemeiner Fallback, falls andere Fehler auftreten
        return f"Fehler bei API-Anfrage: {e}"


def main(row, number_name, prompt_name):
    number = row[number_name]
    prompt = row[prompt_name]
    full_prompt = introduction + "\n" + prompt + "\n" + modify_response
    print(f"{number}: {prompt}")
    response = send_prompt(llm_model, full_prompt)
    response_final = str(number) + "::" + "\n" + response.replace("\n\n", "\n")
    return response_final
###############################################################################

if __name__ == '__main__':
    os.chdir(file_path)

    # Zusätzliche Anweisung aus Datei lesen
    with open(modify_response_filename, "r", encoding="utf-8") as f:
        modify_response = f.read()

    # Quelldatei mit den Suchanfragen einlesen
    df_source_file = pd.read_excel(source_file, sheet_name="Suchanfragen")

    # Spaltennamen für Nummer und Prompt automatisch erkennen
    number_name = None
    prompt_name = None
    for n in df_source_file.columns:
        if 'Nr' in n:
            number_name = n
        if 'Such' in n:
            prompt_name = n

    for ID, row in df_source_file.iterrows():
        response = main(row, number_name, prompt_name)

        # Antwort an Textdatei anhängen
        with open("full_responses_" + llm_model + ".txt", "a", encoding="utf-8") as f:
            f.write(response + "\n")

        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        print(dt_str_now)

        # Kurze Pause zum Schutz vor IP/Rate-Limits
        time.sleep(1)