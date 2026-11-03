#!/usr/bin/env python3
"""
Iteratives Suchanfragen-Skript für Gemini mit automatischem Modell-Fallback bei Überlastung
"""
import os
import re
import time
import requests
import pandas as pd
from datetime import datetime

from api_keys import Gemini_key

from google import genai
from google.genai import types
from google.genai.errors import APIError

# API-Key in der von Gemini erwarteten Umgebungsvariable setzen
os.environ["GEMINI_API_KEY"] = Gemini_key
# Gemini-Client initialisieren (greift automatisch auf GEMINI_API_KEY zu)
client = genai.Client()
# Kostenlose Gemini-App nutzt seit 09.10.2026 nur noch Flash-Lite (Gemini 3.8 Flash nur für Google AI Pro/Ultra)
llm_model = "gemini-3.5-flash-lite"
# Websuche wie in der App (Grounding mit Google Search)
search_config = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])

file_path = r"C:\Users\andre\OneDrive\Desktop\KI-Performance Möbel 2026"
source_file = "KI-Performance Möbel_20260930" + ".xlsx"
# Eigener Prompt ohne URL-Vorgaben: Mit den URL-Vorgaben verfälscht Gemini die Links und liefert keine Suchdaten
modify_response_filename = "normalize_response_gemini.txt"
introduction = "Beantworte zuerst ausschließlich inhaltlich die folgende Frage so, wie du sie auch beantworten würdest, wenn es keine zusätzlichen Format- oder Analyseanforderungen gäbe:"
# Ohne diesen Satz sucht Gemini 3.5 Flash-Lite bei vielen Fragen auch nach wiederholten Versuchen nicht
search_instruction = "Nutze für deine Antwort die Google-Suche."
MAX_SEARCH_RETRIES = 3  # Wiederholungen, wenn eine Antwort keine Suchdaten enthält

# Dependencies
# pip install google-genai pandas openpyxl
########################################################################################################################
REDIRECT_PATTERN = re.compile(r'https://vertexaisearch\.cloud\.google\.com/grounding-api-redirect/[^\s,)\]]+')
# Interne Quellennummern der Google-Suche, z. B. "(1.1.1, 1.2.3)"
INDEX_MARKER_PATTERN = re.compile(r'\s*\(\d+(?:\.\d+)+(?:,\s*\d+(?:\.\d+)+)*\)')


def resolve_redirect(url):
    """Liefert die echte Ziel-URL eines Google-Weiterleitungslinks oder None, wenn er nicht auflösbar ist."""
    try:
        return requests.get(url, allow_redirects=False, timeout=15).headers.get("Location")
    except requests.RequestException:
        return None


def replace_redirects(text):
    """Ersetzt Weiterleitungslinks im Text durch die echten URLs und entfernt nicht auflösbare Links."""
    text = REDIRECT_PATTERN.sub(lambda m: resolve_redirect(m.group(0)) or "", text)
    text = re.sub(r'\(\s*(?:,\s*)+', '(', text)
    text = re.sub(r'(?:,\s*)+\)', ')', text)
    text = re.sub(r',\s*,', ',', text)
    return re.sub(r'\s*\(\s*\)', '', text)


def clean_response(response):
    """Gibt den Antworttext mit echten Quellen-URLs zurück: Die Quellen aus den Suchdaten werden am Ende
    des jeweils belegten Textabschnitts in runden Klammern eingefügt (Position in Bytes laut API)."""
    text = response.text
    metadata = response.candidates[0].grounding_metadata
    if metadata and metadata.grounding_chunks and metadata.grounding_supports:
        chunks = metadata.grounding_chunks
        chunk_urls = {}
        positions = {}
        for support in metadata.grounding_supports:
            if support.segment and support.segment.end_index:
                positions.setdefault(support.segment.end_index, []).extend(support.grounding_chunk_indices or [])
        data = text.encode("utf-8")
        for end in sorted(positions, reverse=True):
            for i in positions[end]:
                if i not in chunk_urls:
                    chunk_urls[i] = resolve_redirect(chunks[i].web.uri) if chunks[i].web else None
            urls = list(dict.fromkeys(chunk_urls[i] for i in positions[end] if chunk_urls[i]))
            if not urls:
                continue
            # Klammer vor das Satzzeichen des belegten Satzes setzen
            pos = end
            while pos > 0 and data[pos - 1:pos] in (b".", b"!", b"?", b":", b" ", b"\n", b"\r"):
                pos -= 1
            data = data[:pos] + f" ({', '.join(urls)})".encode("utf-8") + data[pos:]
        text = data.decode("utf-8")
    return replace_redirects(INDEX_MARKER_PATTERN.sub('', text)).strip()


def has_search_data(response):
    """Prüft, ob die Antwort auf einer Google-Suche beruht und Quellen zugeordnet sind."""
    metadata = response.candidates[0].grounding_metadata
    return bool(metadata and metadata.grounding_chunks and metadata.grounding_supports)


def send_prompt(prompt):
    # Liste der Modelle: Erst das Wunschmodell, dann das stabilere Backup-Modell
    models_to_try = [llm_model, "gemini-3.1-flash-lite"]

    for model in models_to_try:
        wait_time = 10  # Konstante Wartezeit von 10 Sekunden bei Fehlern
        retries = 0
        max_retries = 3  # Versuche pro Modell, bevor gewechselt wird
        search_retries = 0

        while retries < max_retries:
            try:
                print(f"   --> Sende Anfrage an Modell: {model} (Versuch {retries + 1}/{max_retries})...")
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=search_config
                )
                # Ohne Suchdaten wiederholen; nach MAX_SEARCH_RETRIES zählt die letzte Antwort
                if not has_search_data(response) and search_retries < MAX_SEARCH_RETRIES:
                    search_retries += 1
                    print(f"   Keine Suchdaten, Wiederholung {search_retries}/{MAX_SEARCH_RETRIES}...")
                    continue
                # Erfolgreich! Wir geben den Text und das genutzte Modell zurück
                return clean_response(response), model

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
        "   [WARNUNG] Alle Modelle blockieren. Versuche es nun fortlaufend im 10-Sekunden-Takt mit gemini-3.1-flash-lite...")
    while True:
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
                config=search_config
            )
            return clean_response(response), "gemini-3.1-flash-lite (Dauer-Fallback)"
        except Exception:
            time.sleep(10)


def main(row, number_name, prompt_name):
    number = row[number_name]
    prompt = row[prompt_name]
    full_prompt = introduction + "\n" + prompt + "\n" + search_instruction + "\n" + modify_response
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
