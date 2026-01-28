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

from api_keys import ChatGPT_key
from openai import OpenAI, RateLimitError
# API-Key setzen
os.environ["OPENAI_API_KEY"] = ChatGPT_key
# OpenAI-Client initialisieren (ohne Argumente!)
client = OpenAI()
llm_model = "gpt-5.2-chat-latest"
responses_synthesis_filename = "prompt_responses_synthesis" + ".txt"
file_path = r"C:\Users\andre\OneDrive\Desktop\Marketing\KI-Performance\KI-Performance Schuhe"

source_file_filename = "full_responses_gpt-5.2-chat-latest" + ".txt"
model_name = "gpt-5.2-chat-latest"
########################################################################################################################
#Dependencies
# pip install openai
#pip install openpyxl
#pip install tabulate

def gpt_chat(llm_model, prompt):
    try:
        response = client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except RateLimitError as e:
        return f"Rate Limit überschritten: {e}"

########################################################################################################################

if __name__ == '__main__':
    os.chdir(file_path)
    # Quellendatei mit den Responses im Textformat
    with open(source_file_filename, "r", encoding="utf-8") as f:
        source_file = f.read()
    with open(responses_synthesis_filename, "r", encoding="utf-8") as f:
        response_synthesis = f.read()
    final_table = []

    responses_list = re.split(r'(?:[1-9]|[1-4]\d|50):\n', source_file)

    if not len(responses_list) == 51:
        print(f'Abweichende Anzahl: {len(responses_list)}')
#        for n, l in enumerate(responses_list):
#            print(n,l)
#            if n > 3:
#                break

    for ID, response in enumerate(responses_list):
        if len(response) <= 3:
            continue
        if str(response).count('\n') >= 1:
            response_s = response.rsplit('\n',1)[0]
            if len(response) - len(response_s) < 4:
                response = response_s

        full_prompt = response_synthesis + "\n" + response
        print(f"{ID}: {response}")
        table_format = gpt_chat(llm_model, full_prompt)

        for line in table_format.split('\n'):
            if not str(line[0]).isdigit():
                continue
            row = line.split(';')
            if len(row) != 7:
                print(f'Abweichende Spalten: {len(row)}')
                break
            final_table.append([ID]+row)

#        for t in final_table:
#            print(t)

    header = ['Anfrage', 'Rang', 'Firmenname', 'Markenname', 'Website', 'Produkt', 'Quellen',
              'Wörtliche Beschreibung der Marke im Chat']
    df_perplexity_responses = pd.DataFrame(final_table,columns=header)
    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    filename = model_name + '_responses_table_' + dt_str_now + '.xlsx'
    df_perplexity_responses.to_excel(filename)