
import pandas as pd

def gpt_chat(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except RateLimitError as e:
        return f"Rate Limit überschritten: {e}"

if __name__ == '__main__':
    while True:
        user_input = str(input("You: "))
        if user_input.lower() in ['exit', 'bye']:
            break
        response = gpt_chat(user_input)
        print(response)

########################################################################################################################

'''
    for line in response.split('\n'):
        line = line.replace('"','')
        if not line[0].isdigit():
            continue
        first_elements = line.split(',')[:6]
        description = ','.join(line.split(',')[6:])
        print(line_elements)

# Links durch Semikolons trennen

# https://platform.openai.com/api-keys
# python ChatGPTAI
'''
Gib deine Antwort anschließend in einer Tabelle aus, die von Python ausgelesen werden kann. In der Tabelle sollen alle in dieser Antwort namentlich genannten Marken (oder deren Produkte) mit folgenden Informationen aufgelistet werden: Rang der Nennung im Chat, Anzahl der Nennungen im gesamten Text, Firmenname (recherchieren, falls nicht explizit genannt), Markenname, Produkt (Name des spezifischen Produkts, z. B. Modellbezeichnung), Quellen (alle Quellen als vollständige URLs, durch Kommas getrennt), wörtliche Beschreibung der Marke im Chat (der gesamte Kontext, in dem du in deiner Antwort über die Marke schreibst). Entferne alle Einträge aus der Tabelle, die nicht explizit als Marke, Firma oder Produkt im Fließtext der Antwort erwähnt wurden. Erwähnungen ausschließlich in den Quellen werden nicht berücksichtigt. Sortiere die Tabelle abschließend nach der Reihenfolge der erstmaligen Erwähnung von Marken und Produkten im Fließtext und passe die Rangliste entsprechend an. Gib mir am Ende ausschließlich die Tabelle aus.

'''

#Dependencies
#pip install openpyxl
#pip install tabulate