import requests
from bs4 import BeautifulSoup
import urllib3
import re
import subprocess
from datetime import datetime

# Suprimir avisos de pedidos inseguros
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CANTEENS = {
    "Santiago": "https://cms.ua.pt/ementas/santiago",
    "Grelhados": "https://cms.ua.pt/ementas/grelhados",
    "Crasto": "https://cms.ua.pt/ementas/crasto"
}

def scrape_all_menus():
    print("A recolher ementas... (Verifica o WIFI ou VPN!)")
    all_canteen_data = {}

    for name, url in CANTEENS.items():
        try:
            response = requests.get(url, timeout=15, verify=False)
            response.raise_for_status()
        except Exception as e:
            print(f"Erro no {name}: {e}")
            all_canteen_data[name] = []
            continue

        soup = BeautifulSoup(response.content, 'html.parser')
        menu_data = []
        rows = soup.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                day_text = cells[0].get_text(separator=' ', strip=True)
                menu_text = cells[1].get_text(separator='\n', strip=True)
                
                # Limpeza de caracteres e alergénios
                menu_text = menu_text.replace('\xa0', ' ').replace('\u200b', '')
                menu_text = menu_text.replace('—', ':').replace(' - ', ': ')
                menu_text = re.sub(r'[0-9]+(?:,[0-9]+)*', '', menu_text)
                
                lines = menu_text.split('\n')
                clean_lines = []
                for line in lines:
                    line = line.strip()
                    if "legendas relativas" in line.lower(): continue
                    
                    if line.lower().startswith("prato "):
                        line = line[6:].strip()
                        if line:
                            line = line[0].upper() + line[1:]
                    
                    if line: clean_lines.append(line)
                
                merged_lines = []
                for line in clean_lines:
                    lower_line = line.lower()
                    
                    is_title = lower_line in ['almoço', 'jantar']
                    is_main = lower_line.startswith(('sopa', 'carne', 'peixe', 'veg', 'dieta'))
                    
                    if is_title or is_main:
                        merged_lines.append(line)
                    elif merged_lines and merged_lines[-1].lower() not in ['almoço', 'jantar']:
                        merged_lines[-1] += f" e {line}"
                
                if day_text and day_text.lower() != "dia":
                    menu_data.append({'dia': day_text, 'linhas': merged_lines})

        all_canteen_data[name] = menu_data
    return all_canteen_data

def save_to_html(data):
    html_start = """
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        
        <meta property="og:title" content="Ementas UA : Cantinas">
        <meta property="og:description" content="Ementas atualizadas de Santiago, Grelhados e Crasto.">
        <meta property="og:type" content="website">
        
        <title>Ementas UA</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; padding: 15px; }
            h1 { text-align: center; color: #2c3e50; }
            .tabs { display: flex; justify-content: center; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
            .tab-btn { padding: 12px; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; background: #e0e6ed; flex: 1; max-width: 150px;}
            .tab-btn.active { background: #2980b9; color: white; }
            .menu-container { display: none; max-width: 800px; margin: 0 auto; }
            .menu-container.active { display: block; }
            .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
            h2 { color: #2980b9; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }
            .dish { margin: 10px 0; padding: 12px; border-radius: 6px; font-weight: bold; }
            .sopa { background: #fff8e1; border-left: 5px solid #ffc107; }
            .carne { background: #ffebee; border-left: 5px solid #e74c3c; }
            .peixe { background: #e3f2fd; border-left: 5px solid #3498db; }
            .veg { background: #e8f5e9; border-left: 5px solid #2ecc71; }
            .dieta { background: #f4f6f7; border-left: 5px solid #95a5a6; }
        </style>
    </head>
    <body>
        <h1>Ementas Universidade</h1>
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('Santiago', this)">Santiago</button>
            <button class="tab-btn" onclick="switchTab('Grelhados', this)">Grelhados</button>
            <button class="tab-btn" onclick="switchTab('Crasto', this)">Crasto</button>
        </div>
    """
    
    content = ""
    for name, days in data.items():
        active_class = " active" if name == "Santiago" else ""
        content += f"<div id='{name}' class='menu-container{active_class}'>"
        for dia in days:
            content += f"<div class='card'><h2>{dia['dia']}</h2>"
            for line in dia['linhas']:
                low = line.lower()
                if low in ['almoço', 'jantar']: content += f"<h3>{line}</h3>"
                elif 'sopa' in low: content += f"<div class='dish sopa'>{line}</div>"
                elif 'dieta' in low: content += f"<div class='dish dieta'>{line}</div>"
                elif 'carne' in low: content += f"<div class='dish carne'>{line}</div>"
                elif 'peixe' in low: content += f"<div class='dish peixe'>{line}</div>"
                elif 'veg' in low: content += f"<div class='dish veg'>{line}</div>"
            content += "</div>"
        content += "</div>"

    html_end = """
        <script>
            function switchTab(id, btn) {
                document.querySelectorAll('.menu-container').forEach(c => c.classList.remove('active'));
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.getElementById(id).classList.add('active');
                btn.classList.add('active');
            }
        </script>
    </body></html>
    """
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_start + content + html_end)

def git_push():
    print("A enviar atualizações para o GitHub...")
    try:
        subprocess.run(["git", "add", "index.html"], check=True)
        commit_msg = f"Update ementa {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("Sincronização concluída com sucesso!")
    except Exception as e:
        print(f"Erro ao sincronizar com GitHub: {e}")

if __name__ == "__main__":
    data = scrape_all_menus()
    save_to_html(data)
    git_push()