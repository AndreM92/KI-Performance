# !/usr/bin/env python3
"""
Iteratives Textverarbeitungs-Skript für ChatGPT API
Dabei werden die Angaben zu den Marken in den Antworten der LLMs extrahiert, durch weitere Recherchen ergänzt und
im Tabellenformat ausgegeben.
"""
import os
import re
import time
from datetime import datetime
import pandas as pd
import requests
import json

from ki_functions import *
# API-Key setzen
os.environ["OPENAI_API_KEY"] = ChatGPT_key
# OpenAI-Client initialisieren (ohne Argumente!)
client = OpenAI()
llm_model = "gpt-5.5"

# Verzeichnis für die gesicherten Rohantworten (wird unter ./Responses angelegt)
RAW_DIR = "raw_tables"

# Maximale Anzahl an Fortsetzungs-Anfragen, falls eine Antwort abgeschnitten wurde.
# Verhindert Endlosschleifen, falls das Modell nie zum Ende kommt.
MAX_FORTSETZUNGEN = 5

responses_synthesis_filename = "prompt_responses_synthesis" + ".txt"
file_path = r"C:\Users\andre\OneDrive\Desktop\KI-Performance Arzneimittel 2026"
########################################################################################################################
# Dependencies
# pip install openai
# pip install openpyxl
# pip install tabulate
########################################################################################################################


def gpt_chat_vollstaendig(client, model, prompt, max_retries=3):
    """
    Ruft die API direkt auf (statt über gpt_chat), um Zugriff auf finish_reason
    zu erhalten. Kombiniert zwei Sicherheitsmechanismen:

    1. Retry mit Backoff: Bei transienten Fehlern (Rate-Limit, Timeout,
       Netzwerkfehler) wird der Aufruf bis zu max_retries-mal wiederholt.
    2. Fortsetzung bei Abschneidung: Endet die Antwort mit
       finish_reason == "length", wird das Gespräch fortgesetzt und die
       Teilantworten werden nahtlos zusammengefügt, bis finish_reason == "stop"
       erreicht ist. Damit gehen keine Tabellenzeilen am Ende verloren,
       auch wenn die Tabelle länger ausfällt als erwartet.

    Rückgabe: (vollstaendiger_text, wurde_fortgesetzt) oder (None, False) bei
    endgültigem Fehlschlag.
    """
    messages = [{"role": "user", "content": prompt}]
    gesamt_text = ""
    wurde_fortgesetzt = False

    for fortsetzung in range(MAX_FORTSETZUNGEN + 1):
        response = None
        for versuch in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                )
                break
            except Exception as e:
                wartezeit = 5 * (versuch + 1)  # 5s, 10s, 15s Backoff
                print(f'API-Fehler (Versuch {versuch + 1}/{max_retries}): {e}')
                if versuch < max_retries - 1:
                    print(f'Warte {wartezeit}s vor erneutem Versuch...')
                    time.sleep(wartezeit)

        if response is None:
            print('Alle Retry-Versuche fehlgeschlagen.')
            # Falls bereits Teiltext vorliegt, diesen zurückgeben statt alles zu verwerfen
            return (gesamt_text if gesamt_text else None), wurde_fortgesetzt

        choice = response.choices[0]
        teil_text = choice.message.content or ""
        finish_reason = choice.finish_reason

        # Teiltexte OHNE Trennzeichen zusammenfügen: die Abschneidung erfolgt
        # mitten in einer Zeile, ein eingefügtes '\n' würde die Zeile zerreißen.
        gesamt_text += teil_text

        if finish_reason == "length":
            wurde_fortgesetzt = True
            print(f'Antwort abgeschnitten (finish_reason=length), '
                  f'fordere Fortsetzung an ({fortsetzung + 1}/{MAX_FORTSETZUNGEN})...')
            messages.append({"role": "assistant", "content": teil_text})
            messages.append({"role": "user", "content":
                "Deine Antwort wurde abgeschnitten. Fahre EXAKT an der Stelle fort, "
                "an der du aufgehört hast. Wiederhole nichts, keine Einleitung, "
                "keine Kopfzeile - nur die restlichen Tabellenzeilen im selben Format."})
            continue

        # finish_reason == "stop" (oder anderes reguläres Ende): fertig
        return gesamt_text, wurde_fortgesetzt

    print(f'WARNUNG: Maximale Fortsetzungen ({MAX_FORTSETZUNGEN}) erreicht, '
          f'Tabelle ist möglicherweise trotzdem unvollständig.')
    return gesamt_text, wurde_fortgesetzt


def pruefe_letzte_zeile(table_format):
    """
    Heuristische Zusatzprüfung: Endet die letzte Datenzeile mit der erwarteten
    Spaltenzahl (7 Felder = 6 Semikolons)? Falls nicht, ist die Tabelle
    vermutlich mitten in einer Zeile abgebrochen.
    """
    zeilen = [z.strip() for z in table_format.strip().split('\n') if z.strip()]
    daten_zeilen = [z for z in zeilen if z.lstrip('|').strip()[:1].isdigit()]
    if not daten_zeilen:
        return True  # keine Datenzeilen - wird an anderer Stelle abgefangen
    letzte = daten_zeilen[-1]
    return letzte.count(';') >= 6
########################################################################################################################

if __name__ == '__main__':
    os.chdir(file_path)
    with open(responses_synthesis_filename, "r", encoding="utf-8") as f:
        response_synthesis = f.read()
    if '\n' in response_synthesis:
        response_synthesis = response_synthesis.replace('\n', ' ')
    os.chdir('./Responses')

    # Verzeichnis für Rohantworten anlegen
    os.makedirs(RAW_DIR, exist_ok=True)

    file_list = sorted([f for f in os.listdir() if '.txt' in f and 'full_responses' in f])
    start_at = 1

    for n, source_file_filename in enumerate(file_list):
        print(n, source_file_filename)
        if n < start_at:
            continue
#        break

        final_table = []
        model_name = source_file_filename.replace('full_responses', '').replace('.txt', '').replace('_', '')
        # Quellendatei mit den Responses im Textformat
        with open(source_file_filename, "r", encoding="utf-8") as f:
            source_file = f.read()
        patterns = re.findall(r'(?:[1-9]|[1-4]\d|50)::\n', source_file)
        responses_list = re.split(r'(?:[1-9]|[1-4]\d|50)::\n', source_file)
        if not len(responses_list) == 51:
            print(f'Abweichende Anzahl: {len(responses_list)}')
            print(patterns)
            continue

        for ID, response in enumerate(responses_list):
            if ID <= 0:
                continue
            if len(response) <= 3:
                continue
            if str(response).count('\n') >= 1:
                response_s = response.rsplit('\n', 1)[0]
                if len(response) - len(response_s) < 4:
                    response = response_s

            full_prompt = response_synthesis + "\n" + response
            print(f"{ID}: {response[:100]}")

            # Retry und Fortsetzung bei Abschneidung
            table_format, wurde_fortgesetzt = gpt_chat_vollstaendig(client, llm_model, full_prompt)
            if not table_format:
                print(f'No results for Response {ID}')
                continue

            # Zusatzprüfung: letzte Zeile vollständig?
            if not pruefe_letzte_zeile(table_format):
                print(f'WARNUNG: Response {ID} - letzte Tabellenzeile wirkt '
                      f'unvollständig (weniger als 7 Spalten).')

            # Rohantwort sofort sichern
            raw_filename = os.path.join(RAW_DIR, f'{model_name}_ID{ID:02d}.txt')
            with open(raw_filename, 'w', encoding='utf-8') as f_raw:
                f_raw.write(table_format)
            if wurde_fortgesetzt:
                print(f'Hinweis: Response {ID} wurde aus mehreren Teilantworten '
                      f'zusammengesetzt (gesichert unter {raw_filename}).')

            # Toleranteres Parsing + Zeilenzähler
            zeilen_count = 0
            for line in table_format.split('\n'):
                # Führende Leerzeichen, Markdown-Pipes und Aufzählungszeichen entfernen
                line = line.strip().lstrip('|').lstrip('-').strip()
                if not line or not line[0].isdigit():
                    continue
                # Nach der 7. Spalte nicht weiter trennen: Semikolons im
                # Beschreibungstext zerreißen die Zeile sonst.
                row = line.split(';', 6)
                if len(row) != 7:
                    print(f'Abweichende Spalten: {len(row)}:')
                    print(row)
                if len(row) < 7:
                    # Heuristik: Steht in Spalte 4 eine URL, fehlt vermutlich
                    # die Website-Spalte an Position 5 -> dort einfügen.
                    if len(row) > 3 and 'http' in row[3]:
                        row.insert(4, '')
                    # Restliche fehlende Spalten mit Leerstrings auffüllen,
                    # damit jede Zeile exakt 7 Felder hat.
                    row += [''] * (7 - len(row))
                final_table.append([ID] + row)
                zeilen_count += 1

            # WICHTIG: Diese Prüfung steht AUSSERHALB der Zeilen-Schleife,
            # auf derselben Einrückungsebene wie 'zeilen_count = 0'.
            if zeilen_count == 0:
                # Unterscheiden: legitim leere Response (keine Marken genannt)
                # vs. echter Parsing-/Formatfehler.
                tf_lower = table_format.lower()
                keine_marken_indikatoren = ('keine_marken', 'keine marken',
                                            'keine marke', 'keine produkte',
                                            'keine nennung', 'no brands')
                if any(ind in tf_lower for ind in keine_marken_indikatoren):
                    print(f'Hinweis: Response {ID} enthält laut Modell keine '
                          f'Markennennungen - Platzhalterzeile wird eingetragen.')
                    final_table.append([ID, '', '', 'Keine Marken genannt',
                                        '', '', '', ''])
                else:
                    print(f'WARNUNG: Response {ID} lieferte keine parsbaren Zeilen! '
                          f'Rohantwort prüfen: {raw_filename}')
#            break

        new_table = []
        for row in final_table:
#            print(len(row), row)
            if len(row) > 8:
                overhang = [str(e).strip() for e in row[7:] if len(str(e).strip()) > 4]
                row = row[:7] + ['; '.join(overhang)]
            # Sicherheitsnetz: Sollte trotz Auffüllung im Parsing eine Zeile
            # mit weniger als 8 Feldern durchrutschen, hier auf 8 auffüllen.
            if len(row) < 8:
                if len(row) > 3 and 'http' in row[3]:
                    row.insert(4, '')
                row += [''] * (8 - len(row))
            new_table.append(row)

        header = ['Anfrage', 'Rang', 'Firma', 'Marke', 'Website', 'Produkt', 'Quellen',
                  'Wörtliche Beschreibung der Marke im Chat']
        df_responses = pd.DataFrame(new_table, columns=header)
        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        filename = model_name + '_responses_table_' + dt_str_now + '.xlsx'
        df_responses.to_excel(filename)