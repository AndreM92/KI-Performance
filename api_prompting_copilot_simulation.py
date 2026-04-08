
import os
import re
import pandas as pd
from datetime import datetime

from api_keys import ChatGPT_key
from openai import OpenAI, RateLimitError

# API-Key setzen
os.environ["OPENAI_API_KEY"] = ChatGPT_key

# OpenAI-Client
client = OpenAI()

# Modell (aktuell sinnvoll für Copilot-ähnliche Tasks)
llm_model = "gpt-4o"

file_path = r"C:\Users\andre\OneDrive\Desktop\KI-Performance Versicherungen 2026"
source_file = "KI-Performance Versicherungen_20260313.xlsx"
modify_response_filename = "normalize_response_s.txt"

system_prompt = """
Du bist ein neutraler Such- und Analyseassistent ähnlich Microsoft Copilot.
Arbeite in zwei Schritten:
1. Interpretiere die Anfrage wie eine Suchmaschine (Informationsbedarf erkennen)
2. Gib eine strukturierte, neutrale Marktübersicht

Regeln:
- Keine direkte Produktempfehlung
- Nenne konkrete Anbieter nur im Kontext einer Marktübersicht
- Schreibe sachlich und vergleichend
"""

introduction = """Beantworte zuerst ausschließlich inhaltlich die folgende Frage so,
wie du sie auch beantworten würdest, wenn es keine zusätzlichen Format-
oder Analyseanforderungen gäbe:"""

########################################################################################################################

def send_prompt(model, system_prompt, user_prompt):
    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.6
        )

        return response.output_text.strip()

    except RateLimitError as e:
        return f"Rate Limit überschritten: {e}"

    except Exception as e:
        return f"Fehler: {e}"

########################################################################################################################

def build_prompt(base_prompt, modify_response):
    return f"""
{introduction}
ANFRAGE:
{base_prompt}
ZUSATZANFORDERUNG:
{modify_response}
"""

########################################################################################################################

def main(row, number_name, prompt_name, modify_response):
    number = row[number_name]
    prompt = row[prompt_name]
    full_prompt = build_prompt(prompt, modify_response)
    print(f"{number}: {prompt}")
    response = send_prompt(llm_model, system_prompt, full_prompt)
    response_clean = re.sub(r"\n{2,}", "\n", response)
    response_final = f"{number}:\n{response_clean}"
    return response_final
########################################################################################################################

if __name__ == '__main__':
    os.chdir(file_path)
    with open(modify_response_filename, "r", encoding="utf-8") as f:
        modify_response = f.read()
    df_source_file = pd.read_excel(source_file, sheet_name="Suchanfragen")
    # Spalten erkennen
    number_name = None
    prompt_name = None
    for col in df_source_file.columns:
        if 'Nr' in col:
            number_name = col
        if 'Such' in col:
            prompt_name = col
    output_file = f"full_responses_{llm_model}.txt"

    for ID, row in df_source_file.iterrows():
        if ID <= 4:
            continue
        response = main(row, number_name, prompt_name, modify_response)
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(response + "\n\n")
        print(response)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))