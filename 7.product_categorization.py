
import os
import re
from datetime import datetime, timedelta
import pandas as pd

file_path = r"C:\Users\andre\OneDrive\Desktop\Marketing\KI-Performance\KI-Performance Schuhe"
source_file = "KI-Performance Schuhe_2026-01-20" + ".xlsx"
sheet_names = ["ChatGPT", "Claude", "Copilot", "DeepSeek", "Gemini", "Grok", "LLaMA", "Mistral", "Perplexity", "Qwen"]
########################################################################################################################
# Nach der Berechnung der Punkte für jede Marke und jeden ChatBot werden die Tabellen nach Produktkategorien zusammengefasst

def aggregate_groups(categories_table, score_cols, source_table, df_cat):
    category_cols = []
    col_pointer = 0
    for _, row in categories_table.iterrows():
        category = row['Produktkategorien']
        n_cols = int(row['Anzahl'])
        if category == 'Gesamt' or category == 'Summe':
            continue

        cols_to_sum = score_cols[col_pointer: col_pointer + n_cols]
        df_cat[category] = source_table[cols_to_sum].sum(axis=1)
        col_pointer += n_cols
        category_cols.append(category)
    # Validierung
    if col_pointer != len(score_cols):
        raise ValueError(
            f"[{s}] Spaltenzuordnung fehlerhaft: "
            f"{col_pointer} von {len(score_cols)} Spalten verarbeitet")

    df_cat["Gesamtpunkte"] = df_cat[category_cols].sum(axis=1)
    df_cat["Häufigkeit"] = (df_cat[category_cols] > 0).sum(axis=1)
    return df_cat, category_cols


def sum_tables(dict_tables, category_cols):
    df_all = None
    for s, df in dict_tables.items():
        if df_all is None:
            df_all = df.copy()
            df_all = df_all.drop(
        columns=["Gesamtpunkte", "Häufigkeit"])
        else:
            df_all[category_cols] = (
                df_all[category_cols]
                .add(df[category_cols], fill_value=0))

    df_all["Gesamtpunkte"] = df_all[category_cols].sum(axis=1)
    df_all["Häufigkeit"] = (df_all[category_cols] > 0).sum(axis=1)
    dict_tables["Insgesamt"] = df_all
    return dict_tables
########################################################################################################################

if __name__ == '__main__':
    os.chdir(file_path)
    categories_table = pd.read_excel(source_file,sheet_name='Suchanfragen_Statistik')
    dict_tables_brands = {}
    dict_tables_groups = {}
    df_llms_groups = pd.DataFrame()
    df_categories_llms = pd.DataFrame()
    score_cols = [str(i) for i in range(1, 51)]
    exclude_cols = ["Firma", "Website", "Quellen", "Beschreibung","Anzahl","Durchschnittsrang", "Gesamtpunkte", "Rang"]

    for file in os.listdir():
        if "Punkte_Marken" in file:
            agg_file_brands = file
        if "Punkte_Anbietergruppen" in file:
            agg_file_groups = file

    # Iteration über die LLMs
    for ID, s in enumerate(sheet_names):
        print(f'starting with {s}')
        # Für die Marken und Anbietergruppen werden neue, leere Tabellen angelegt
        source_table_brands = pd.read_excel(agg_file_brands, sheet_name=s)
        if 'ID' in source_table_brands.columns:
            source_table_brands.set_index('ID', inplace=True)
        source_table_groups = pd.read_excel(agg_file_groups, sheet_name=s)
        # Metadaten-Spalten identifizieren und Zusatzinformationen ausschließen
        meta_cols_brands = [c for c in source_table_brands.columns if c not in score_cols and c not in exclude_cols]
        meta_cols_groups = [c for c in source_table_groups.columns if c not in score_cols and c not in exclude_cols]
        df_cat_brands = source_table_brands[meta_cols_brands].copy()
        df_cat_groups = source_table_groups[meta_cols_groups].copy()

        # Kategorien aggregieren
        df_cat_brands, category_cols = aggregate_groups(categories_table, score_cols, source_table_brands, df_cat_brands)
        df_cat_groups, category_cols = aggregate_groups(categories_table, score_cols, source_table_groups, df_cat_groups)
        df_cat_groups = df_cat_groups.sort_values(by='Anbietergruppe', key=lambda col: col.str.lower()).reset_index(drop=True)

        dict_tables_brands[s] = df_cat_brands
        dict_tables_groups[s] = df_cat_groups

        # Zusammenfassende Tabelle mit LLMs nach Produktkategorien
        row = df_cat_brands[category_cols].sum()
        df_llms_groups.loc[s, category_cols] = row

        # Zusammenfassende Tabelle mit Anbietergruppen nach LLMs
        series = df_cat_groups.set_index('Anbietergruppe')['Gesamtpunkte']
        df_categories_llms = pd.concat([df_categories_llms, series.rename(s)], axis=1)

    # Punkte der LLMs aufsummieren
    dict_tables_brands = sum_tables(dict_tables_brands, category_cols)
    dict_tables_groups = sum_tables(dict_tables_groups, category_cols)
    # NaN vermeiden
    df_llms_groups = df_llms_groups.fillna(0).infer_objects(copy=False)
    # Gesamtspalten
    df_llms_groups['Gesamt'] = df_llms_groups.sum(axis=1)
    df_categories_llms['Gesamt'] = df_categories_llms.sum(axis=1)
    # Gesamtzeilen
    df_llms_groups.loc['Gesamt'] = df_llms_groups.sum(axis=0)
    df_categories_llms.loc['Gesamt'] = df_categories_llms.sum(axis=0)

    # Export in zwei Dateien mit jeweils 10 Tabs zu den LLMs sowie der Zusammenfassenden Tabelle
    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    agg_tables_brands = 'Punkte_Produktkategorien_Marken_' + dt_str_now + '.xlsx'
    with pd.ExcelWriter(agg_tables_brands, engine='xlsxwriter') as writer:
        for title, df in dict_tables_brands.items():
            df.to_excel(writer, sheet_name=title)
    agg_tables_groups = 'Punkte_Produktkategorien_Anbietergruppen_' + dt_str_now + '.xlsx'
    with pd.ExcelWriter(agg_tables_groups, engine='xlsxwriter') as writer:
        for title, df in dict_tables_groups.items():
            df.to_excel(writer, sheet_name=title)
        df_categories_llms.to_excel(writer, sheet_name='Anbietergruppen_LLMs')
        df_llms_groups.to_excel(writer, sheet_name='LLMs_Produktkategorien')

    print('finished')