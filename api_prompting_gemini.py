#!/usr/bin/env python3
"""
Iteratives Suchanfragen-Skript für Gemini mit automatischem Modell-Fallback bei Überlastung
"""
import os
import re
import time
import pandas as pd
from datetime import datetime

from api_keys import Gemini_key

from google import genai
from google.genai.errors import APIError

# API-Key in der von Gemini erwarteten Umgebungsvariable setzen
os.environ["GEMINI_API_KEY"] = Gemini_key
# Gemini-Client initialisieren (greift automatisch auf GEMINI_API_KEY zu)
client = genai.Client()
llm_model = "gemini-3.5-flash"

file_path = r"C:\Users\andre\OneDrive\Desktop\KI-Performance Arzneimittel 2026"
source_file = "KI-Performance Arzneimittel_20260715" + ".xlsx"
modify_response_filename = "normalize_response.txt"
introduction = "Beantworte zuerst ausschließlich inhaltlich die folgende Frage so, wie du sie auch beantworten würdest, wenn es keine zusätzlichen Format- oder Analyseanforderungen gäbe:"

# Dependencies
# pip install google-genai pandas openpyxl
########################################################################################################################
def send_prompt(prompt):
    # Liste der Modelle: Erst das Wunschmodell, dann das stabilere Backup-Modell
    models_to_try = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

    for model in models_to_try:
        wait_time = 10  # Konstante Wartezeit von 10 Sekunden bei Fehlern
        retries = 0
        max_retries = 3  # Versuche pro Modell, bevor gewechselt wird

        while retries < max_retries:
            try:
                print(f"   --> Sende Anfrage an Modell: {model} (Versuch {retries + 1}/{max_retries})...")
                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )
                # Erfolgreich! Wir geben den Text und das genutzte Modell zurück
                return response.text.strip(), model

            except APIError as e:
                retries += 1
                print(f"   [API-Fehler bei {model}]: {e.message if hasattr(e, 'message') else e}")
                if retries < max_retries:
                    print(f"   Warte {wait_time}s vor dem nächsten Versuch...")
                    time.sleep(wait_time)
                else:
                    print(f"   [INFO] {model} fehlgeschlagen nach {max_retries} Versuchen.")

            except Exception as e:
                retries += 1
                print(f"   [Unerwarteter Fehler bei {model}]: {e}")
                if retries < max_retries:
                    print(f"   Warte {wait_time}s vor dem nächsten Versuch...")
                    time.sleep(wait_time)

    # Extremfall: Beide Modelle haben nach je 3 Versuchen versagt
    print(
        "   [WARNUNG] Alle Modelle blockieren. Versuche es nun fortlaufend im 10-Sekunden-Takt mit gemini-2.5-flash...")
    while True:
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt
            )
            return response.text.strip(), "gemini-3.1-flash-lite (Dauer-Fallback)"
        except Exception:
            time.sleep(10)


def main(row, number_name, prompt_name):
    number = row[number_name]
    prompt = row[prompt_name]
    full_prompt = introduction + "\n" + prompt + "\n" + modify_response
    print(f"\n--- Start Anfrage {number}: {prompt[:60]}... ---")

    # Holt die Antwort und liefert zurück, welches Modell schlussendlich geantwortet hat
    response, used_model = send_prompt(full_prompt)
    response_final = str(number) + "::" + "\n" + response.replace("\n\n", "\n")
    return response_final, used_model
########################################################################################################################

if __name__ == '__main__':
    os.chdir(file_path)
    with open(modify_response_filename, "r", encoding="utf-8") as f:
        modify_response = f.read()

    df_source_file = pd.read_excel(source_file, sheet_name="Suchanfragen")

    number_name = None
    prompt_name = None
    for n in df_source_file.columns:
        if 'Nr' in n:
            number_name = n
        if 'Such' in n:
            prompt_name = n

    if not number_name or not prompt_name:
        raise ValueError(
            "Spalten für 'Nr' oder 'Such' konnten in der Excel-Tabelle nicht eindeutig identifiziert werden!")

    for ID, row in df_source_file.iterrows():
        if ID < 0:
            continue
        # main() gibt jetzt Antworttext und das genutzte Modell zurück
        response, used_model = main(row, number_name, prompt_name)

        # Speichern der echten Antwort mit angepasstem Dateinamen
        with open("full_responses_gemini_hybrid.txt", "a", encoding="utf-8") as f:
            f.write(response + "\n")

        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        print(f"--> Antwort {row[number_name]} erfolgreich gespeichert um {dt_str_now} (Generiert mit: {used_model})")

        # Kurze Pause zum Schutz vor IP/Rate-Limits
        time.sleep(1)
