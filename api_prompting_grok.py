#!/usr/bin/env python3
"""
Iteratives Suchanfragen-Skript für xAI Grok API (Grok 4.5)
Wiederholt Anfragen bei zu kurzen / ausbleibenden Antworten.
"""

import os
import time
from datetime import datetime
import pandas as pd
from openai import OpenAI, RateLimitError

# API-Key aus separater Datei einlesen
from api_keys import xAI_key

# OpenAI-Client für xAI initialisieren
client = OpenAI(
    api_key=xAI_key,
    base_url="https://api.x.ai/v1",  # xAI-Endpunkt
)

# Bestes aktuelles Modell
llm_model = "grok-4.5"

file_path = r"C:\Users\andre\OneDrive\Desktop\KI-Performance Arzneimittel 2026"
source_file = "KI-Performance Arzneimittel_20260715.xlsx"
modify_response_filename = "normalize_response.txt"

introduction = (
    "Beantworte zuerst ausschließlich inhaltlich die folgende Frage so, "
    "wie du sie auch beantworten würdest, wenn es keine zusätzlichen "
    "Format- oder Analyseanforderungen gäbe:")

# Konfiguration für Wiederholungsversuche
MIN_ANSWER_LENGTH = 100
MAX_RETRIES = 3

# Dependencies
# pip install xai-sdk
###############################################################################

def send_prompt(llm_model, prompt, min_length=MIN_ANSWER_LENGTH, max_retries=MAX_RETRIES):
    """Sendet einen Prompt an die xAI Grok API mit Retry-Logik."""
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=llm_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=8192,  # Grok 4.5 unterstützt deutlich mehr
#                temperature=0.7,  # Optional: leicht kreativer als DeepSeek-Default
            )
            text = response.choices[0].message.content.strip()

            if len(text) >= min_length:
                return text
            else:
                print(f"Antwort zu kurz ({len(text)} Zeichen), "
                      f"versuche erneut... (Versuch {attempt}/{max_retries})")

        except RateLimitError as e:
            print(f"Rate Limit überschritten – warte 5 Sekunden... ({attempt}/{max_retries})")
            time.sleep(5)
            if attempt == max_retries:
                return f"Rate Limit nach {max_retries} Versuchen: {e}"
        except Exception as e:
            print(f"Fehler bei API-Anfrage: {e}")
            if attempt == max_retries:
                return f"Fehler nach {max_retries} Versuchen: {e}"
            time.sleep(2)  # kurze Pause bei sonstigen Fehlern

    return f"Fehlgeschlagen: Keine ausreichend lange Antwort nach {max_retries} Versuchen."


def main(row, number_name, prompt_name):
    number = row[number_name]
    prompt = row[prompt_name]
    full_prompt = introduction + "\n\n" + prompt + "\n\n" + modify_response

    print(f"{number}: {prompt[:80]}...")  # kürzere Ausgabe
    response = send_prompt(llm_model, full_prompt)

    response_final = str(number) + "::\n" + response.replace("\n\n", "\n")
    return response_final
###############################################################################

if __name__ == '__main__':
    os.chdir(file_path)

    # Zusätzliche Anweisung aus Datei lesen
    with open(modify_response_filename, "r", encoding="utf-8") as f:
        modify_response = f.read()

    # Quelldatei einlesen
    df_source_file = pd.read_excel(source_file, sheet_name="Suchanfragen")

    # Spalten automatisch erkennen
    number_name = next((n for n in df_source_file.columns if 'Nr' in n), None)
    prompt_name = next((n for n in df_source_file.columns if 'Such' in n), None)

    if not number_name or not prompt_name:
        raise ValueError("Spalten 'Nr' und 'Such' konnten nicht automatisch gefunden werden.")

    start_at = 0
    for ID, row in df_source_file.iterrows():
        if ID < start_at - 1:
            continue

        response = main(row, number_name, prompt_name)
        # Antwort anhängen
        output_filename = f"full_responses_{llm_model}.txt"
        with open(output_filename, "a", encoding="utf-8") as f:
            f.write(response + "\n")

        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        print(f"[{dt_str_now}] Antwort für {ID} gespeichert.")

        # Kurze Pause zum Schutz vor IP/Rate-Limits
        time.sleep(1)