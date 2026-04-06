
import os
from ki_functions import *
import re
from datetime import datetime, timedelta
import pandas as pd

file_path = r"C:\Users\andre\OneDrive\Desktop\Marketing\KI-Performance\KI-Performance Schuhe"
data_file = "KI-Performance Schuhe_2026-01-20" + ".xlsx"
company_file = "Firmenliste_KI_Schuhe_20260320" + ".xlsx"
source_file = "Quellenliste_BasisURLs_2026-04-01" + ".xlsx"
sheet_names = ["ChatGPT", "Claude", "Copilot", "DeepSeek", "Gemini", "Grok", "LLaMA", "Mistral", "Perplexity", "Qwen"]
########################################################################################################################
# Nach der Extraktion der Basis-URLs und deren Kategorisierung erfolgt ein Ranking der meistgenutzten Quellen
# auf Basis der Gesamtdaten. Die Zuordnung erfolgt durch die Basislink-Liste. Nicht erfasste Links werden ergänzt.

# Im zweiten Schritt werden die Quellen analysiert, aus denen Informationen zu den Anbietern bezogen wurden.
# Dies erfolgt auf Basis der gefilterten Firmenliste.

def get_brandlink_variations(brand):
    bl = brand.lower()
    bls = bl.replace(' ', '-')
    bld = bl.replace(' ', '')
    bldd = bld.replace('.','')
    bl_parts_a = bl.split() + bl.split('.')
    bl_parts = [e.strip() for e in bl_parts_a if len(e) >= 4]
    bl_list = [brand, bl, bls, bld, bldd]
    bl_list_all = ['.' + e for e in bl_list] + ['//' + e for e in bl_list] + [e + '-' for e in bl_list]
    return bl_list_all

if __name__ == '__main__':
    # 1. Erstellung des Quellenrankings
    os.chdir(file_path)
    # Datei der Basislinks inklusive Markenname und Kategorie
    df_sources = pd.read_excel(source_file)
    # Die Datei der Befragungsdaten wird in einem Dictionary gespeichert, um sie nicht jedes Mal erneut laden zu müssen
    dict_data_tables = {}
    for ID, s in enumerate(sheet_names):
        df_data = pd.read_excel(data_file, sheet_name=s)
        dict_data_tables[s] = df_data

    # Für die Erstellung des URL-Rankings wird über die Datentabelle iteriert.
    # Für jede Quelle erfolgt ein Durchlauf der Basis-URL Datei, um den Link oder den Markennamen abzugleichen
    dict_base_urls_points = {}
    for _, row in df_sources.iterrows():
        dict_base_urls_points[row['Basislink']] = {
            'Marke': row['Marke'],
            'Kategorie': row['Kategorie'],
            'Anzahl': 0}

    # Erstellung einer Liste mit allen Anbietergruppen
    df_sources_categories = pd.read_excel(company_file, sheet_name='Anbietergruppen')
    all_sources_categories = df_sources_categories.iloc[:, 0].tolist()
    sources_categories = [e for e in all_sources_categories if not e == 'Gesamt' and not e == 'Gesamtergebnis'] + ['Sonstiges']

    results = []
    for llm, table in dict_data_tables.items():
        print('starting with ' + llm)
        for ID, row in table.iterrows():
            brand = str(row['Marke']).strip()
            company = row['Firma']
            sources = str(row['Quellen']).strip()
            if ',' in sources:
                sources_l = sources.split(',')
            else:
                sources_l = [sources]
            sources_lf = [e for e in sources_l if len(e) > 3]

            for s in sources_lf:
                s = str(s).strip()
                found = False
                # Quellenliste mit Basis-URLs
                for _, brow in df_sources.iterrows():
                    bl = brow['Basislink']
                    bm = str(brow['Marke']).strip()
                    bml = bm.lower()
                    if 'google.com/search' in s and 'google' in bml:
                        continue
                    bcat = str(brow['Kategorie']).strip()
                    brandlink_variations = get_brandlink_variations(bm)
                    bl_part = bl.replace('https://', '').replace('http://', '').replace('www.', '').strip('/').strip()
                    if len(s) < 12 or not ('http' in s[:12] or 'www.' in s[:12]):
                        if bml == brand.lower() and ('Produkt' in s or 'Product' in s or brand in s):
                            found = True
                            results.append([bm + ';' + bl + ';' + s])
                            dict_base_urls_points[bl]['Anzahl'] += 1
                    else:
                        if '.' + bl_part in s or '/' + bl_part in s:
                            found = True
                            results.append([bm + ';' + bl + ';' + s])
                            dict_base_urls_points[bl]['Anzahl'] += 1
                if not found:
                    for _, brow in df_sources.iterrows():
                        bl = brow['Basislink']
                        bm = str(brow['Marke']).strip()
                        if 'google.com/search' in s and 'google' in bm.lower():
                            continue
                        bcat = str(brow['Kategorie']).strip()
                        brandlink_variations = get_brandlink_variations(bm)
                        bl_part = bl.replace('https://', '').replace('http://', '').replace('www.', '').strip('/').strip()
                        if '.' in bl_part:
                            bl_part_alt = bl_part.rsplit('.', 1)[0] + '.'
                            if len(bl_part_alt) >= 4:
                                bl_part = bl_part_alt
                        if any(b in s for b in brandlink_variations) \
                                or '.' + bl_part in s or '/' + bl_part in s or '-' + bl_part in s:
                            found = True
                            results.append([bm + ';' + bl + ';' + s])
                            dict_base_urls_points[bl]['Anzahl'] += 1
                if not found and len(s) > 12 and ('http' in s[:12] or 'www.' in s[:12]):
                    s = s.strip('/').strip()
                    if s not in dict_base_urls_points:
                        dict_base_urls_points[s] = {
                            'Marke': '(bei) ' + brand,
                            'Kategorie': bcat,
                            'Anzahl': 1}
                    else:
                        dict_base_urls_points[s]['Anzahl'] += 1

    # Export der URL-Ranking-Datei
    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    dict_ranking_sources = dict(sorted(dict_base_urls_points.items(), key=lambda item: item[1]['Anzahl'], reverse=True))
    df_ranking_sources = pd.DataFrame.from_dict(dict_ranking_sources, orient='index')
    # Basislink aus dem Index in eine Spalte überführen
    df_ranking_sources = df_ranking_sources.reset_index().rename(columns={'index': 'Basislink'})
    # Optional: saubere Reihenfolge
    df_ranking_sources = df_ranking_sources[['Basislink', 'Marke', 'Kategorie', 'Anzahl']]
    # Neue laufende Nummer als Index
    df_ranking_sources.index = range(1, len(df_ranking_sources) + 1)
    filename = 'Quellenliste_Ranking_' + dt_str_now + '.xlsx'
    df_ranking_sources.to_excel(filename)

    df_results = pd.DataFrame(results,columns=['Zuordnung'])
    df_results.to_excel('results.xlsx')
    len(results)

    # 2. Erstellung der Quellenliste für die Marken
    # Finde die aktuelle zusammenfassende Tabelle der Marken
    f_name = ''
    os.chdir(file_path)
    for e in os.listdir():
        if 'Punkte_Marken' in e:
            f_name = e
            break
    if not f_name:
        print('Punkte_Marken not found')
    df_agg = pd.read_excel(f_name, sheet_name='Insgesamt')
    data = []
    for ID, row in df_agg.iterrows():
        if 'ID' in df_agg.columns:
            ID = row['ID']
        brand = str(row['Marke']).strip()
        brand_l = brand.lower()
        company = str(row['Firma'])
        website = str(row['Website'])
        category = row['Anbietergruppe']
        sources = str(row['Alle Quellen'])
        brand_sources = [ID, brand, company, website, category]
        category_count = [0 for _ in range(len(sources_categories))]
        own_page = 0
        if len(sources) <= 4:
            full_row = brand_sources + [own_page] + category_count
            data.append(full_row)
            print(full_row)
            continue

        sources_list = [s.strip() for s in sources.split('|')]
        for s in sources_list:
            s = str(s).strip()
            if len(s) <= 7:
                continue
            found = False
            if len(s) < 12 or not ('http' in s[:12] or 'www.' in s[:12]):
                if 'Produkt' in s or 'Product' in s or brand_l in s.lower():
                    found = True
                    own_page += 1
            if not found:
                for bl, bvalues in dict_ranking_sources.items():
                    bm = str(bvalues['Marke']).strip()
                    bml = bm.lower()
                    if 'google.com/search' in s and 'google' in bml:
                        continue
                    bc = bvalues['Kategorie']
                    bl_part = bl.replace('https://','').replace('http://','').replace('www.','').strip('/').strip()
                    if '.' + bl_part in s or '/' + bl_part in s or \
                            not ('http' in s or 'www' in s) and bl_part in s.lower():
                        found = True
                        brandlink_variations = get_brandlink_variations(bm)
                        if brand_l == bml or bl_part in website or any(b in website for b in brandlink_variations):
                            print(brand, website, bl, s )
                            own_page += 1
                        else:
                            for pos, c in enumerate(sources_categories):
                                if c == bc:
                                    print(s, bm, bc)
                                    category_count[pos] += 1
                        break
            if not found:
                for bl, bvalues in dict_ranking_sources.items():
                    bm = str(bvalues['Marke']).strip()
                    bml = bm.lower()
                    if 'google.com/search' in s and 'google' in bml:
                        continue
                    bc = bvalues['Kategorie']
                    brandlink_variations = get_brandlink_variations(bm)
                    bl_part = bl.replace('https://', '').replace('http://', '').replace('www.', '').strip('/').strip()
                    if not ('http' in s or 'www' in s) and (bm in s or bl_part in s.lower()):
                        found = True
                        if brand_l == bml or '.' + bl_part in website or '//' + bl_part in website \
                            or any(b in website for b in brandlink_variations):
                            print(brand, website, bl, s)
                            own_page += 1
                        else:
                            for pos, c in enumerate(sources_categories):
                                if c == bc:
                                    print(s, bm, bc)
                                    category_count[pos] += 1
                        break
                    if any(b in s for b in brandlink_variations):
                        found = True
                        if brand_l == bml or '.' + bl_part in website or '//' + bl_part in website \
                            or any(b in website for b in brandlink_variations):
                            own_page += 1
                        else:
                            for pos, c in enumerate(sources_categories):
                                if c == bc:
                                    print(s, bm, bc)
                                    category_count[pos] += 1
                        break
            if not found:
                    category_count[-1] += 1

        full_row = brand_sources + [own_page] + category_count
        data.append(full_row)
        print(full_row)

    # Dataframes
    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    col_names = ['ID', 'Marke', 'Firma', 'Website', 'Branche'] + ['Eigene Website'] + sources_categories
    df_brand_sources = pd.DataFrame(data, columns=col_names)
    df_brand_sources = df_brand_sources.set_index("ID")
    # Neues DataFrame mit Anteilen
    df_brand_sources_perc = df_brand_sources.copy()
    # Berechnungen
    df_brand_sources['Summe'] = (df_brand_sources[['Eigene Website'] + sources_categories].sum(axis=1))
    df_brand_sources_perc[['Eigene Website'] + sources_categories] = (
    df_brand_sources[['Eigene Website'] + sources_categories]
            .div(df_brand_sources['Summe'], axis=0).mul(100).round(1).fillna(0))
    # Export als xlsx
    filename2 = 'Quellenliste_Marken_' + dt_str_now + '.xlsx'
    with pd.ExcelWriter(filename2, engine='xlsxwriter') as writer:
        df_brand_sources.to_excel(writer, sheet_name='Punkte')
        df_brand_sources_perc.to_excel(writer, sheet_name='Anteile')