#!/usr/bin/env python3
"""
Iteratives Suchanfragen-Skript für Meta über OpenRouter API
Wiederholt Anfragen bei zu kurzen / ausbleibenden Antworten.
"""

import os, time, pandas as pd
from datetime import datetime
from openai import OpenAI, RateLimitError

from api_keys import openrouter_key

client = OpenAI(
    api_key=openrouter_key,
    base_url="https://openrouter.ai/api/v1", # OpenRouter Endpoint
    default_headers={
        "HTTP-Referer": "https://localhost", # Pflichtfeld bei OpenRouter
        "X-Title": "KI-Performance Arzneimittel Benchmark"
    }
)

# Für Kimi K3:
llm_model = "moonshotai/kimi-k3"
# Für Meta/ LLaMA
llm_model = "meta-llama/llama-4-maverick"
# Für Mistral
llm_model = "mistralai/mistral-medium-3-5"
# Für Qwen
llm_model = "qwen/qwen3.7-max"

file_path = r"C:\Users\andre\OneDrive\Desktop\KI-Performance Arzneimittel 2026"
source_file = "KI-Performance Arzneimittel_20260715.xlsx"
modify_response_filename = "normalize_response.txt"
introduction = "Beantworte zuerst ausschließlich inhaltlich die folgende Frage so, wie du sie auch beantworten würdest, wenn es keine zusätzlichen Format- oder Analyseanforderungen gäbe:"

MIN_ANSWER_LENGTH = 100
MAX_RETRIES = 3

# Dependencies
# pip install openai pandas openpyxl python-dotenv
###############################################################################

# wird in main() gefüllt
modify_response = ""

def send_prompt(model, prompt):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
#                max_tokens=8192,
#                temperature=0.7
            )
            text = resp.choices[0].message.content.strip()
            if len(text) >= MIN_ANSWER_LENGTH:
                return text
            print(f"Antwort zu kurz ({len(text)} Zeichen), Retry {attempt}/{MAX_RETRIES}")
        except RateLimitError:
            print(f"Rate Limit, warte 10s... Versuch {attempt}/{MAX_RETRIES}")
            time.sleep(10)
        except Exception as e:
            print(f"Fehler: {e} - Versuch {attempt}/{MAX_RETRIES}")
            time.sleep(2)
    return f"Fehlgeschlagen nach {MAX_RETRIES} Versuchen."


def main(row, number_name, prompt_name):
    number = row[number_name]
    prompt = row[prompt_name]
    full_prompt = introduction + "\n\n" + str(prompt) + "\n\n" + modify_response
    print(f"{number}: {str(prompt)[:80]}...")
    response = send_prompt(llm_model, full_prompt)
    response_final = str(number) + "::\n" + response.replace("\n\n", "\n")
    return response_final

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

    # Dateiname für Windows bereinigen
    safe_model_name = llm_model.replace("/", "_").replace(":", "_").replace("-", "_")
    output_filename = f"full_responses_{safe_model_name}.txt"

    start_at = 1
    for ID, row in df_source_file.iterrows():
        if ID < start_at - 1:
            continue

        response = main(row, number_name, prompt_name)

        with open(output_filename, "a", encoding="utf-8") as f:
            f.write(response + "\n")

        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        print(f"[{dt_str_now}] Antwort für {ID} in {output_filename} gespeichert.")
        time.sleep(1)
