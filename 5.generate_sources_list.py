
import os
from ki_functions import *

import re
import time
from datetime import datetime, timedelta
import pandas as pd

import tldextract
from urllib.parse import urlparse

file_path = r"C:\Users\andre\OneDrive\Desktop\Marketing\KI-Performance\KI-Performance Schuhe"
company_list = "Firmenliste_KI_Schuhe_20260320" + ".xlsx"
company_archive = r"C:\Users\andre\OneDrive\Desktop\Marketing\KI-Performance\Firmenliste_Archiv.xlsx"
source_file = "KI-Performance Schuhe_2026-01-20" + ".xlsx"
sheet_names = ["ChatGPT", "Claude", "Copilot", "DeepSeek", "Gemini", "Grok", "LLaMA", "Mistral", "Perplexity", "Qwen"]
########################################################################################################################
# pip install tldextract
# Im Rahmen dieser Analyse werden die Quellen-Urls aus den Promptdaten vereinheitlicht, indem aus allen Varianten einer
# Adresse die jeweilige Basis-URL (Hauptdomain) extrahiert wird.
# Anschließend erfolgt ein Ranking der meistgenutzten Quellen auf Basis aller Variationen der Basis-Urls

def get_distinct_sources(df_source, all_sources, col_list):
    # Spalte mit Quellen
    for c in col_list:
        if 'Quelle' in c:
            sc_name = c
    for ID, row in df_source.iterrows():
        source = str(extract_text(re, row[sc_name])).strip()
        if len(source) < 12 and not ('http' in source[:12] or 'www.' in source[:12]):
            continue
        if ' ' in source:
            sources = source.split()
            for s in sources:
                if ',' in s:
                    ss = s.split(',')
                    for e in ss:
                        e = str(e).strip()
                        if len(e) >= 12 and ('http' in e[:12] or 'www.' in e[:12]):
                            all_sources.add(e)
                else:
                    for s in sources:
                        s = str(s).strip()
                        if len(s) >= 12 and ('http' in s[:12] or 'www.' in s[:12]):
                            all_sources.add(s)
        elif ',' in source:
            ss = source.split(',')
            for e in ss:
                e = str(e).strip()
                if len(e) >= 12 and ('http' in e[:12] or 'www.' in e[:12]):
                    all_sources.add(e)
        else:
            if len(source) >= 12 and ('http' in source[:12] or 'www.' in source[:12]):
                all_sources.add(source)
    cleaned_sources = {l.rstrip(',') for l in all_sources}
    return cleaned_sources


def extract_main_domain(url: str) -> str:
    # Rückgabe der Hauptwebsite als 'https://domain.tld/' zurück.
    if not isinstance(url, str) or not url.strip():
        return "no url"
    raw = url.strip()
    # Falls Schema fehlt, ergänzen (z.B. "19grams.coffee/xyz" -> "http://19grams.coffee/xyz")
    if "://" not in raw:
        raw = "http://" + raw
    try:
        parsed = urlparse(raw)
        hostname = parsed.hostname
        if not hostname:
            return "no url"
        # tldextract kümmert sich um Subdomains, Domains und Public Suffix (.co.uk etc.)
        ext = tldextract.extract(hostname)
        if not ext.domain or not ext.suffix:
            return "no url"
        registrable_domain = f"{ext.domain}.{ext.suffix}"
        # Ausgabe immer als HTTPS-Root-URL mit Slash
        return f"https://{registrable_domain}/"
    except Exception:
        return "no url"


def find_category(df_companies, l_part, brand_search = False, company_search = False):
    found_brand = None
    found_category = None
    for ID, row in df_companies.iterrows():
        brand = str(row['Marke']).strip()
        company = str(row['Firma']).strip()
        website = str(row['Website'])
        category = row['Anbietergruppe']
        match = False
        # Website-Matching
        if len(l_part) > 3 and l_part in website:
            match = True
            # Brand-Matching
        elif brand_search and not company_search and (brand.lower() + '.') in l_part and len(brand) > 3:
            match = True
            # Company-Matching
        elif company_search:
            bvl = brand_variations(brand)
            cvl = get_company_keywords(company)
            cvl = [e for e in cvl if not(e.lower() == 'schuhe' or e.lower() == 'shoes' or e.lower() == 'shoe')]
            if '.' in l_part:
                if len(l_part.split('.')[0]) > 3:
                    l_part = l_part.split('.')[0]
            if any(b in l_part for b in bvl) or any(c in l_part for c in cvl):
                match = True
        if match:
            if not found_brand:
                found_brand = brand
                found_category = category
            else:
                found_brand = found_brand + ' | ' + brand
                found_category = found_category + ' | ' + category
    return found_brand, found_category
########################################################################################################################

if __name__ == '__main__':
    os.chdir(file_path)
    # Liste bzw. Set mit allen Quellen einzeln gelistet
    all_sources = set()
    for ID, s in enumerate(sheet_names):
        print(f'starting with {s}')
        df_source = pd.read_excel(source_file, sheet_name=s)
        col_list = list(df_source.columns)
        all_sources = get_distinct_sources(df_source, all_sources, col_list)
    all_sources_list = sorted(all_sources)

    df_all_sources = pd.DataFrame(all_sources_list, columns=['Quellen'])
    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    filename = 'Quellenliste_' + dt_str_now + '.xlsx'
    df_all_sources.to_excel(filename)

    # Erstellung der Basislink-Liste
    base_urls = set()
    for l in all_sources:
        l_ex = extract_main_domain(l)
        if not ('www.' in l_ex or 'http' in l_ex):
            continue
        base_urls.add(l_ex)
    base_url_list = sorted(base_urls)

    # Kategorisierung der Links auf Basis der Firmenlisten
    df_companies = pd.read_excel(company_list)
    df_company_archive = pd.read_excel(company_archive)
    df_companies = pd.concat([df_companies, df_company_archive], ignore_index=True)

    url_dict = {}
    for bl in base_url_list:
        l_part = bl.replace('https://','').replace('http://','').replace('www.','').strip('/').strip()
        brand, category = find_category(df_companies, l_part, brand_search=False, company_search=False)
        if not brand:
            brand, category = find_category(df_companies,l_part, brand_search=True, company_search=False)
        if not brand:
            brand, category = find_category(df_companies,l_part, brand_search=True, company_search=True)
        if brand:
            url_dict[bl] = [brand,category]
        else:
            url_dict[bl] = ['', '']
        print(bl)
    # Nach Kategorielänge sortieren
    url_dict = dict(sorted(url_dict.items(), key=lambda x: len(x[1][1])))

    url_df = pd.DataFrame([{"Basislink": bl, "Marke": vals[0], "Kategorie": vals[1]} for bl, vals in url_dict.items()])
    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    filename = 'Quellenliste_BasisURLs_' + dt_str_now + '.xlsx'
    url_df.to_excel(filename)
    print('finished')


# Nachrecherche per KI
'''
Recherchiere für die folgenden URLs den Markennamen sowie die passende Anbieterkategorie.
Die Kategorie muss aus dieser Liste stammen:
Schuhhändler
Schuhhersteller/-marken
Modehandel
Modemarken
Vergleichsportale
Universalhändler/Marktplätze
sonstiger Handel
sonstige Marken
Medien & Influencer
Arbeits-/Sicherheitsschuhe
Orthopädie und Sanitätshäuser
Outdoorbedarf
Outlet und Factory Stores
Sportschuhe

Erstelle anschließend eine Tabelle mit den Spalten:
Basislink
Marke
Kategorie

Dies sind die zu analysierenden URLs:
'''