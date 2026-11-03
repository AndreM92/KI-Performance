#!/usr/bin/env python3
"""
Iteratives Suchanfragen-Skript für DeepSeek API
Wiederholt Anfragen bei zu kurzen / ausbleibenden Antworten.
"""
import json
import os
import re
import time
from datetime import datetime

import pandas as pd
import requests
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
# deepseek-flash = V4-Flash = Standardmodus "Instant" in der kostenlosen App; deepseek-v4-pro = Modus "Expert"
# Websuche wie in der App ("Search") über die Such-API von DeepSeek als Funktionsaufruf
llm_model = "deepseek-v4-pro"
llm_model = "deepseek-flash"

file_path = r"C:\Users\andre\OneDrive\Desktop\KI-Performance Möbel 2026"
source_file = "KI-Performance Möbel_20260930" + ".xlsx"
modify_response_filename = "normalize_response.txt"
introduction = (
    "Beantworte zuerst ausschließlich inhaltlich die folgende Frage so, "
    "wie du sie auch beantworten würdest, wenn es keine zusätzlichen "
    "Format- oder Analyseanforderungen gäbe:")

# Konfiguration für Wiederholungsversuche
MIN_ANSWER_LENGTH = 100   # Mindestlänge der Antwort (in Zeichen)
MAX_RETRIES = 3          # Maximale Anzahl zusätzlicher Versuche

# Konfiguration für die Websuche
SEARCH_URL = "https://api.deepseek.com/v1/tools/search"
SEARCH_RESULTS = 10      # Anzahl der Treffer pro Suche
MAX_SEARCH_ROUNDS = 5    # Maximale Anzahl der Suchrunden pro Antwort
SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Durchsucht das Internet und liefert Titel, URL, Datum und Zusammenfassung der Treffer.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Suchbegriffe, maximal 128 Zeichen"},
            },
            "required": ["query"],
        },
    },
}

# Dependencies
# pip install openpyxl
# pip install pandas
# https://platform.deepseek.com/api_keys
###############################################################################

def web_search(query):
    """Führt eine Suche über die Such-API von DeepSeek aus und gibt die Treffer als JSON-Text zurück."""
    response = requests.post(
        SEARCH_URL,
        headers={"Authorization": f"Bearer {DeepSeek_key}"},
        json={"query": query[:128], "count": SEARCH_RESULTS},
        timeout=60,
    )
    response.raise_for_status()
    results = [{key: result.get(key) for key in ("title", "url", "date", "summary")}
               for result in response.json()["results"]]
    print(f"   Suche: {query} ({len(results)} Treffer)")
    return json.dumps(results, ensure_ascii=False)


def complete_with_search(llm_model, prompt):
    """Lässt das Modell suchen, bis es antwortet. Eine Pflichtsuche (tool_choice="required") lehnt die API im Thinking-Modus ab."""
    messages = [{"role": "user", "content": prompt}]
    for search_round in range(MAX_SEARCH_ROUNDS + 1):
        response = client.chat.completions.create(
            model=llm_model,
            messages=messages,
            tools=[SEARCH_TOOL],
            tool_choice="auto" if search_round < MAX_SEARCH_ROUNDS else "none",
            max_tokens=32000,  # Überlegungen des Modells zählen mit
        )
        message = response.choices[0].message
        if not message.tool_calls:
            return message.content
        # model_dump behält die Überlegungen (reasoning_content), die DeepSeek in Folgerunden erwartet
        messages.append(message.model_dump(exclude_none=True))
        for call in message.tool_calls:
            query = json.loads(call.function.arguments)["query"]
            messages.append({"role": "tool", "tool_call_id": call.id, "content": web_search(query)})


def send_prompt(llm_model, prompt, min_length=MIN_ANSWER_LENGTH, max_retries=MAX_RETRIES):
    """
    Sendet einen Prompt an die DeepSeek-API.
    Wiederholt die Anfrage, wenn die Antwort kürzer als min_length ist.
    """
    for attempt in range(1, max_retries + 1):
        try:
            # Das Modell hängt an URLs teils eigene Quellennummern an, z. B. "#1#4#1"
            text = re.sub(r'(https?://[^\s,)\]]*?)(?:#\d+)+(?=[\s,)\]]|$)', r'\1',
                          complete_with_search(llm_model, prompt)).strip()

            if len(text) >= min_length:
                return text
            else:
                print(f"Antwort zu kurz ({len(text)} Zeichen), "
                      f"versuche erneut... (Versuch {attempt}/{max_retries})")
                # Nur wiederholen, wenn noch Versuche übrig
                if attempt == max_retries:
                    return (f"Hinweis: Keine ausreichend lange Antwort "
                            f"nach {max_retries} Versuchen.\nLetzte Antwort:\n{text}")
        except RateLimitError as e:
            return f"Rate Limit überschritten: {e}"
        except Exception as e:
            return f"Fehler bei API-Anfrage: {e}"

    # Wenn alle Versuche fehlschlugen, letzte (kurze) Antwort zurückgeben oder Hinweis
    return f"Fehlgeschlagen: Keine ausreichend lange Antwort nach {max_retries} Versuchen."


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

    start_at = 1
    for ID, row in df_source_file.iterrows():
        if ID < start_at - 1:
            continue
        response = main(row, number_name, prompt_name)

        # Antwort an Textdatei anhängen
        with open("full_responses_" + llm_model + ".txt", "a", encoding="utf-8") as f:
            f.write(response + "\n")

        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        print(dt_str_now)

        # Kurze Pause zum Schutz vor IP/Rate-Limits
        time.sleep(1)