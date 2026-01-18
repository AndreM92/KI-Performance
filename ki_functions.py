# pip install openai
import os
from api_keys import ChatGPT_key
from openai import OpenAI, RateLimitError
# API-Key setzen
os.environ["OPENAI_API_KEY"] = ChatGPT_key
# OpenAI-Client initialisieren (ohne Argumente!)
client = OpenAI()

import re


def gpt_chat(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except RateLimitError as e:
        return f"Rate Limit überschritten: {e}"

def create_table(response):
    for line in response.split('\n'):
        line = line.replace('"','')
        if not line[0].isdigit():
            continue
        first_elements = line.split(',')[:6]
        description = [','.join(line.split(',')[6:])]
        full_row = first_elements + description
        print(full_row)

# Extract text from elements
def extract_text(element):
    if element:
        if not isinstance(element,(str,int,float)):
            element = element.text.strip()
        element = str(element)
        if element == '':
            return element
        elif len(element) >= 1:
            repl_element = element.replace('\u200b','').replace('\xa0', ' ').replace('\n',' ')
            new_element = re.sub('\s+', ' ', repl_element).strip()
            return new_element
        else:
            return element
    return None


def brand_variations(brand):
    bv0 = brand.replace('-','')
    bv1 = brand.replace('’','')
    bv2 = brand.replace('`','')
    bv3 = brand.replace("'","")
    bv4 = brand.replace(' /','')
    bv5 = brand.replace('®','')
    bv6 = brand.replace('è','e').replace('é','e').replace('ö','oe')
    bv7 = brand.lower()
    bv8 = brand.upper()
    bv9 = brand.title()
    brand_var_list = [brand, bv0, bv1, bv2, bv3, bv4, bv5, bv6, bv7, bv8, bv9]
    brand_variations = list(set(brand_var_list))
    branch_exclude = ['kaffee', 'coffee', 'cafe', 'caffè','caffé', 'caffe', 'kaffeerösterei', 'roast', 'roasters', 'roaster']
    brand_variations_list = [e for e in brand_variations if not e.lower() in branch_exclude and len(e) > 3]
    return brand_variations_list


def get_company_keywords(company):
    comp_l1 = company.replace('-', '').replace('_', ' ').replace('.', '').replace('’','').replace("'","").split()
    comp_l2 = company.replace('-', '').replace('_', ' ').replace('.', '').split()
    comp_l3 = company.lower().replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').split()
    comp_l4 = company.split()
    comp_l = list(set(comp_l1 + comp_l2 + comp_l3 + comp_l4))
    comp_keywords_f = [str(e).lower() for e in comp_l if len(str(e).lower()) >= 3]
    appendix = ['gmbh', 'mbh', 'inc', 'limited', 'ltd', 'llc', 'co.', 'lda', 'a.s.', 'S.A.', ' OG', ' AG', ' SE',
                'GmbH & Co. KG', 'GmbH', 'B.V.', 'KG', 'LLC', 'NV', 'N.V.',
                '& Co.', 'S.L.U.', '(', ')', '.de', '.com', '.at', 'oHG', 'Ltd.', 'Limited',
                'Kaffee','kaffee']
    comp_keywords = list(set([e for e in comp_keywords_f if not any(a in e for a in appendix) and len(e) > 3] + [company]))
    return comp_keywords