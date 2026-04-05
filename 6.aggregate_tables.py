
import os
from ki_functions import *
import re
from datetime import datetime, timedelta
import pandas as pd
# pip install xlsxwriter

file_path = r"C:\Users\andre\OneDrive\Desktop\Marketing\KI-Performance\KI-Performance Schuhe"
company_list = "Firmenliste_KI_Schuhe_20260320" + ".xlsx"
company_archive = r"C:\Users\andre\OneDrive\Desktop\Marketing\KI-Performance\Firmenliste_Archiv.xlsx"
source_file = "KI-Performance Schuhe_2026-01-20" + ".xlsx"
sheet_names = ["ChatGPT", "Claude", "Copilot", "DeepSeek", "Gemini", "Grok", "LLaMA", "Mistral", "Perplexity", "Qwen"]
########################################################################################################################
# Nach Erstellung und Bereinigung der vollständigen Anbieterliste (inklusive erneuter Zuordnung zu den Anbietergruppen)
# wird diese Liste importiert und mit allen Promptergebnissen abgeglichen.
# Der Code erstellt eine Tabelle, in der die Punkte bei jeder Marke für jeden ChatBot und jede Anfragen berechnet werden.
# Zusätzlich wird die Liste mit den Quellen importiert

def aggregate_table(df_source, df_agg, c_rows):
    for ID, row_d in df_agg.iterrows():
        b_source = str(row_d['Marke']).strip()
        c_source = str(row_d['Firma']).replace('(kein deutscher Rechtsträger', '').strip()
        ck = get_company_keywords(c_source)
        bvsl = brand_variations(b_source)
        request_prev = ''
        for r, row in df_source.iterrows():
            request = str(row['Anfrage']).strip()
            if request != request_prev:
                points = 0
                found = False
            request_prev = request
            try:
                r_p = 12 - int(row['Rang'])
                if r_p < 1:
                    r_p = 1
            except:
                continue
            brand = str(row['Marke']).strip()
            bvl = brand_variations(brand)
            company = str(row['Firma']).strip()
            cvl = get_company_keywords(company)
            for h in df_source.columns:
                if "Beschreibung" in str(h):
                    desc_name = str(h)
                    break
            desc = request + ': ' + str(row[desc_name]).strip()
            if (b_source in bvl or b_source in brand or \
                    (any(b in bvsl for b in bvl) and \
                     (any(c.lower() in company.lower() for c in ck) or any(
                         c.lower() in c_source.lower() for c in cvl)))) and not 5 > brand.lower().find(b_source.lower()) > 0\
                    and not 4 > len(brand) - len(b_source) > 0 :
                if found == False:
                    df_agg.at[ID, request] = r_p
                    found = True

                # Beschreibungstext ergänzen
                if len(desc) > 8:
                    if not df_agg.at[ID, 'Beschreibung']:
                        df_agg.at[ID, 'Beschreibung'] = desc
                    else:
                        df_agg.at[ID, 'Beschreibung'] += " | " + desc

                # Quellen ergänzen
                source = str(row['Quellen']).strip()
                if ',' in source:
                    sources_list = source.split(',')
                elif ' ' in source:
                    sources_list = source.split()
                else:
                    sources_list = [source]
                for s in sources_list:
                    if len(s) <= 3:
                        continue
                    if not df_agg.at[ID, 'Quellen']:
                        df_agg.at[ID, 'Quellen'] = request + ': ' + s
                    else:
                        df_agg.at[ID, 'Quellen'] += " | " + request + ': ' + s

    df_agg['Anzahl'] = (df_agg[c_rows] > 0).sum(axis=1)
    #    df_agg['Durchschnittspunkte'] = (df_agg[c_rows].where(df_agg[c_rows] > 0).mean(axis=1).fillna(0))
    # Alle Platzierungen unter den Top 10 werden mit 11 berechnet
    df_agg['Durchschnittsrang'] = ((12 - df_agg[c_rows]).where(df_agg[c_rows] > 0).mean(axis=1).fillna(0))
    df_agg['Gesamtpunkte'] = df_agg[c_rows].sum(axis=1)

    return df_agg
########################################################################################################################

if __name__ == '__main__':
    os.chdir(file_path)
    dict_tables_brands = {}
    dict_tables_groups = {}

    for ID, s in enumerate(sheet_names):
        print(f'starting with {s}')
        df_source = pd.read_excel(source_file, sheet_name=s)
        col_list = list(df_source.columns)
        #        if ID > 1:
        #           break

        # DataFrame mit den Anbieternamen laden
        df_agg = pd.read_excel(company_list)
        if 'Unnamed: 0' in df_agg.columns:
            df_agg.drop(columns='Unnamed: 0', inplace=True)
        if 'ID' in df_agg.columns:
            df_agg.set_index('ID', inplace=True)
        else:
            df_agg.index.name = 'ID'

        # Spalte mit den Quellen
        df_agg['Quellen'] = ""
        # Spalte mit Markenbeschreibungen
        df_agg['Beschreibung'] = ""

        # Zusätzliche Spalten für die Suchanfragen von "1" bis "50" mit Nullen befüllen
        c_rows = [str(c) for c in range(1, 51)]
        df_agg = df_agg.assign(**{col: 0 for col in c_rows})

        # Aggregierte Tabelle für die Marken
        df_agg_brands = aggregate_table(df_source, df_agg, c_rows)

        # Aggregierte Tabelle für die Anbietergruppen
        df_agg_groups = df_agg.groupby('Anbietergruppe')[c_rows + ['Anzahl', 'Gesamtpunkte']].sum()

        # Speichern der Tabellen in einem dictionary mit dem LLM als key
        dict_tables_brands[s] = df_agg_brands
        dict_tables_groups[s] = df_agg_groups

    # Zusammenfassende Tabellen über die LLMs
    df_brands_all = None
    df_brands_all_f = None
    df_brands_all_r = None
    for s, df in dict_tables_brands.items():
        if df_brands_all is None:
            df_brands_all = pd.DataFrame({
                "Marke": df["Marke"],
                "Firma": df["Firma"],
                "Website": df["Website"],
                "Anbietergruppe": df["Anbietergruppe"],
            })
            df_brands_all_f = df_brands_all.copy()
            df_brands_all_r = df_brands_all.copy()
            df_brands_all[s] = df["Gesamtpunkte"]
            df_brands_all_f[s] = df["Anzahl"]
            df_brands_all_r[s] = df["Durchschnittsrang"]
            df_brands_all["Alle Quellen"] = df["Quellen"].astype(str).where(
                df["Quellen"].notna() & (df["Quellen"].astype(str).str.strip() != ""), "")
            df_brands_all["Alle Beschreibungen"] = df["Beschreibung"].astype(str).where(
                df["Beschreibung"].notna() & (df["Beschreibung"].astype(str).str.strip() != ""), "")
        else:
            df_brands_all[s] = df['Gesamtpunkte']
            df_brands_all_f[s] = df["Anzahl"]
            df_brands_all_r[s] = df["Durchschnittsrang"]
            mask = df["Quellen"].notna() & (df["Quellen"].astype(str).str.strip() != "")
            df_brands_all.loc[mask, "Alle Quellen"] = (
                df_brands_all.loc[mask, "Alle Quellen"].where(df_brands_all.loc[
                                                                  mask, "Alle Quellen"] != "", df["Quellen"]).where(
                    df_brands_all.loc[
                        mask, "Alle Quellen"] == "", df_brands_all.loc[mask, "Alle Quellen"] + " | " +
                    df["Quellen"]))
            mask = df["Beschreibung"].notna() & (df["Beschreibung"].astype(str).str.strip() != "")
            df_brands_all.loc[mask, "Alle Beschreibungen"] = (
                df_brands_all.loc[mask, "Alle Beschreibungen"].where(df_brands_all.loc[
                                                                         mask, "Alle Beschreibungen"] != "",
                                                                     df["Beschreibung"]).where(df_brands_all.loc[
                                                                                                   mask, "Alle Beschreibungen"] == "",
                                                                                               df_brands_all.loc[
                                                                                                   mask, "Alle Beschreibungen"] + " | " +
                                                                                               df["Beschreibung"]))

    df_brands_all['Gesamtpunkte'] = df_brands_all[sheet_names].sum(axis=1)
    df_brands_all['Gesamtanzahl'] = df_brands_all_f[sheet_names].sum(axis=1)
    df_brands_all['Durchschnittsrang'] = (
        df_brands_all_r[sheet_names].where(df_brands_all_r[sheet_names] > 0).mean(axis=1))
    df_brands_all = df_brands_all[['Marke', 'Firma', 'Website', 'Anbietergruppe'] + sheet_names +
                                  ['Gesamtpunkte', 'Gesamtanzahl', 'Durchschnittsrang', 'Alle Quellen',
                                   'Alle Beschreibungen']]
    dict_tables_brands['Insgesamt'] = df_brands_all

    df_groups_all = None
    df_groups_all_f = None
    for s, df in dict_tables_groups.items():
        if df_groups_all is None:
            df_groups_all = pd.DataFrame({s: df['Gesamtpunkte']})
            df_groups_all_f = pd.DataFrame({s: df['Anzahl']})
        else:
            df_groups_all[s] = df['Gesamtpunkte']
            df_groups_all_f[s] = df['Anzahl']
    df_groups_all['Gesamtpunkte'] = df_groups_all[sheet_names].sum(axis=1)
    df_groups_all['Gesamtanzahl'] = df_groups_all_f[sheet_names].sum(axis=1)
    dict_tables_groups['Insgesamt'] = df_groups_all

    # Export in zwei Dateien mit jeweils 10 Tabs zu den LLMs
    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    agg_tables_brands = 'Punkte_Marken_' + dt_str_now + '.xlsx'
    with pd.ExcelWriter(agg_tables_brands, engine='xlsxwriter') as writer:
        for title, df in dict_tables_brands.items():
            df.to_excel(writer, sheet_name=title)
    agg_tables_groups = 'Punkte_Anbietergruppen_' + dt_str_now + '.xlsx'
    with pd.ExcelWriter(agg_tables_groups, engine='xlsxwriter') as writer:
        for title, df in dict_tables_groups.items():
            df.to_excel(writer, sheet_name=title)
    print(dt_str_now)

    # Überprüfung auf doppelte Werte
    cols = [str(i) for i in range(1, 51)]
    for llm, t in dict_tables_brands.items():
        if llm in sheet_names:
            print(llm)
            result = []
            for c in cols:
                vals = t[c]
                vals = vals[vals > 1]
                result.append({
                    "Spalte": c,
                    "Hat doppelte Werte > 1": vals.duplicated().any(),
                    "Doppelte Werte": list(vals[vals.duplicated()].unique())
                })
            df_check = pd.DataFrame(result)
            print(df_check)