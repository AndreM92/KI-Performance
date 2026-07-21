#!/usr/bin/env python3
"""
Iteratives Suchanfragen-Skript für Claude (Anthropic) API
"""
import os
from datetime import datetime

import pandas as pd

from api_keys import Claude_key
from anthropic import Anthropic, RateLimitError

# API-Key setzen
os.environ["ANTHROPIC_API_KEY"] = Claude_key

# Anthropic-Client initialisieren
client = Anthropic()
llm_model = "claude-sonnet-5"

file_path = r"C:\Users\andre\OneDrive\Desktop\KI-Performance Arzneimittel 2026"
source_file = "KI-Performance Arzneimittel_20260715" + ".xlsx"
modify_response_filename = "normalize_response.txt"
introduction = "Beantworte zuerst ausschließlich inhaltlich die folgende Frage so, wie du sie auch beantworten würdest, wenn es keine zusätzlichen Format- oder Analyseanforderungen gäbe:"

# Dependencies
# pip install anthropic
# pip install openpyxl
# pip install tabulate
# https://console.anthropic.com/settings/keys
########################################################################################################################
def send_prompt(llm_model, full_prompt):
    try:
        response = client.messages.create(
            model=llm_model,
            max_tokens=10000,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 5,
            }],
            messages=[{"role": "user", "content": full_prompt}]
        )
        text_parts = [block.text for block in response.content if block.type == "text"]
        return "".join(text_parts).strip()
    except RateLimitError as e:
        return f"Rate Limit überschritten: {e}"


def main(row, number_name, prompt_name):
    number = row[number_name]
    prompt = row[prompt_name]
    full_prompt = introduction + "\n" + prompt + "\n" + modify_response
    print(f"{number}: {prompt}")
    response = send_prompt(llm_model, full_prompt)
    response_final = str(number) + "::" + "\n" + response.replace("\n\n", "\n")
    return response_final
########################################################################################################################

if __name__ == '__main__':
    os.chdir(file_path)
    with open(modify_response_filename, "r", encoding="utf-8") as f:
        modify_response = f.read()
    # Quellendatei mit den 50 Suchanfragen
    df_source_file = pd.read_excel(source_file, sheet_name="Suchanfragen")
    for n in df_source_file.columns:
        if 'Nr' in n:
            number_name = n
        if 'Such' in n:
            prompt_name = n

    for ID, row in df_source_file.iterrows():
#        if ID < 0:
#            continue
        response = main(row, number_name, prompt_name)
        # Speichern der Antworten als Textdatei
        with open("full_responses_" + llm_model + ".txt", "a", encoding="utf-8") as f:
            f.write(response + "\n")
        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        print(dt_str_now)
