# !/usr/bin/env python3
"""
Iteratives Textverarbeitungs-Skript für ChatGPT API
Dabei werden die Angaben zu den Marken in den Antworten der LLMs extrahiert, durch weitere Recherchen ergänzt und
im Tabellenformat ausgegeben.
"""
import os
import re
from datetime import datetime
import pandas as pd
import requests
import json

from ki_functions import *
# API-Key setzen
os.environ["OPENAI_API_KEY"] = ChatGPT_key
# OpenAI-Client initialisieren (ohne Argumente!)
client = OpenAI()
llm_model = "gpt-5.4"
#llm_model = "sonar"
responses_synthesis_filename = "prompt_responses_synthesis" + ".txt"
file_path = r"C:\Users\andre\OneDrive\Desktop\Marketing\KI-Performance\KI-Performance Schuhe"
########################################################################################################################
#Dependencies
# pip install openai
#pip install openpyxl
#pip install tabulate
########################################################################################################################

if __name__ == '__main__':
    os.chdir(file_path)
    with open(responses_synthesis_filename, "r", encoding="utf-8") as f:
        response_synthesis = f.read()
    if '\n' in response_synthesis:
        response_synthesis = response_synthesis.replace('\n',' ')
    final_table = []
    os.chdir('./responses')
    file_list = sorted([f for f in os.listdir() if '.txt' in f and 'full_responses' in f])
    start_at = 0
    for n, source_file_filename in enumerate(file_list):
        print(source_file_filename)
        if n < start_at:
            continue
        model_name = source_file_filename.replace('full_responses','').replace('.txt','').replace('_','')
        # Quellendatei mit den Responses im Textformat
        with open(source_file_filename, "r", encoding="utf-8") as f:
            source_file = f.read()
        responses_list = re.split(r'(?:[1-9]|[1-4]\d|50):\n', source_file)
        if not len(responses_list) == 51:
            print(f'Abweichende Anzahl: {len(responses_list)}')
    #        for n, l in enumerate(responses_list):
    #            print(n,l)
    #            if n > 3:
    #                break
        break               ####
        for ID, response in enumerate(responses_list):
            if len(response) <= 3:
                continue
            if str(response).count('\n') >= 1:
                response_s = response.rsplit('\n',1)[0]
                if len(response) - len(response_s) < 4:
                    response = response_s

            full_prompt = response_synthesis + "\n" + response
            print(f"{ID}: {response}")
            table_format = gpt_chat(client, llm_model, full_prompt)
#            table_format = perplexity_chat(llm_model, full_prompt)

            for line in table_format.split('\n'):
                if not str(line[0]).isdigit():
                    continue
                row = line.split(';')
                if len(row) != 7:
                    print(f'Abweichende Spalten: {len(row)}')
                if len(row) < 7:
                    if 'http' in row[3]:
                        row.insert(4, '')
                    else:
                        row.insert(-1,'')
                if len(row) > 7 and row[-3] == '':
                    row.pop(-3)
                if len(row) > 7 and row[-2] == '':
                    row.pop(-2)
                print(len(row), row)
                final_table.append([ID]+row)

        header = ['Anfrage', 'Rang', 'Firmenname', 'Markenname', 'Website', 'Produkt', 'Quellen',
                  'Wörtliche Beschreibung der Marke im Chat']
        df_responses = pd.DataFrame(final_table,columns=header)
        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        filename = model_name + '_responses_table_' + dt_str_now + '.xlsx'
        df_responses.to_excel(filename)

'''
new_table = []
for row in final_table:
    if len(row) != 8:
        print(len(row), row)
    if len(row) < 8:
        if 'http' in row[3]:
            row.insert(4, '')
        else:
            row.insert(-1, '')
    if len(row) > 8 and row[-3] == '':
        row.pop(-3)
    if len(row) > 8 and row[-2] == '':
        row.pop(-2)
        print(len(row),row)
    new_table.append(row)
'''