import requests
from datetime import datetime, timedelta
import pytz
import matplotlib.pyplot as plt
import numpy as np
import os

def degres_en_fleche(degres: float) -> str:
    if degres is None: return ""
    index = int((degres + 22.5) / 45) % 8
    return ["↓", "↙", "←", "↖", "↑", "↗", "→", "↘"][index]

def generer_et_envoyer_meteo(ville: str, telegram_token: str, telegram_chat_id: str):
    try:
        # 1. Données Météo
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={ville}&count=1&language=fr&format=json"
        geo_res = requests.get(geo_url, timeout=5).json()
        if not geo_res.get('results'): return
        lat, lon = geo_res['results'][0]['latitude'], geo_res['results'][0]['longitude']
        nom_complet = geo_res['results'][0]['name']
        
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
               f"&hourly=temperature_2m,apparent_temperature,precipitation,precipitation_probability,wind_speed_10m,wind_direction_10m"
               f"&forecast_days=2&timezone=auto")
        res = requests.get(url, timeout=5).json()
        
        tz_france = pytz.timezone('Europe/Paris')
        idx_depart = next((idx for idx, h in enumerate(res['hourly']['time']) if h >= (datetime.now(tz_france) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:00")), 0)
        
        nb_heures = 18
        temperatures = res['hourly']['temperature_2m'][idx_depart:idx_depart+nb_heures]
        ressenties = res['hourly']['apparent_temperature'][idx_depart:idx_depart+nb_heures]
        probas_pluie = res['hourly']['precipitation_probability'][idx_depart:idx_depart+nb_heures]
        hauteur_pluie = res['hourly']['precipitation'][idx_depart:idx_depart+nb_heures]
        vent_vitesse = res['hourly']['wind_speed_10m'][idx_depart:idx_depart+nb_heures]
        vent_direction = res['hourly']['wind_direction_10m'][idx_depart:idx_depart+nb_heures]
        heures_labels = [h.split('T')[1][:5] for h in res['hourly']['time'][idx_depart:idx_depart+nb_heures]]
        
        x = np.arange(len(heures_labels))
        
        # 2. Graphique
        fig, (ax0, ax1, ax2) = plt.subplots(3, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [0.6, 2, 1.2]}, dpi=120)
        fig.patch.set_facecolor('#ffffff')
        
        ax0.set_facecolor('#f1f5f9')
        ax0.set_xlim(-0.5, len(heures_labels) - 0.5)
        ax0.set_ylim(0, 10)
        ax0.axis('off')
            
        for i in range(len(heures_labels)):
            fleche = degres_en_fleche(vent_direction[i])
            ax0.text(x[i], 7.5, heures_labels[i], ha='center', va='center', fontsize=10, fontweight='bold', color='#2c3e50')
            ax0.text(x[i], 3.0, f"{fleche}\n{round(vent_vitesse[i])} km/h", ha='center', va='center', fontsize=9, color='#4b6584', fontweight='semibold', bbox=dict(boxstyle='circle,pad=0.2', facecolor='#ffffff', edgecolor='#cbd5e1', lw=1))

        ax1.set_facecolor('#f8f9fa')
        ax1.plot(x, temperatures, color='#ff4d4d', linewidth=2.5, label='Température (°C)', marker='o', markersize=4)
        ax1.plot(x, ressenties, color='#ff9f43', linewidth=1.5, linestyle='--', label='Ressentie (°C)')
        ax1.set_ylabel('Température (°C)', color='#ff4d4d', fontweight='bold')
        ax1.grid(True, linestyle=':', alpha=0.6, color='#cccccc')
        ax1.set_xticks(x)
        ax1.set_xticklabels(heures_labels, fontsize=10, color='#4a5568')
        
        for i in range(len(temperatures)):
            ax1.annotate(f"{round(temperatures[i],1)}°", (x[i], temperatures[i]), textcoords="offset points", xytext=(0,8), ha='center', fontsize=9, color='#cc0000', fontweight='bold')
        
        ax1.legend(loc='upper right')
        ax1.set_title(f"BULLETIN HORAIRE — {nom_complet.upper()}", fontsize=13, fontweight='bold', pad=15, color='#2c3e50', loc='left')

        ax2.set_facecolor('#f1f5f9')
        ax2.bar(x, probas_pluie, color='#74b9ff', alpha=0.4, width=0.7)
        ax2.set_ylabel('Probabilité Pluie (%)', color='#0984e3', fontweight='bold')
        ax2.set_ylim(0, 110)
        ax2.grid(True, axis='y', linestyle=':')
        
        ax2_mm = ax2.twinx()
        ax2_mm.set_ylabel('Précipitations (mm)', color='#2e5bff', fontweight='bold')
        ax2_mm.bar(x, hauteur_pluie, color='#2e5bff', alpha=0.7, width=0.3)
        ax2_mm.set_ylim(0, max(max(hauteur_pluie) + 0.5, 2)) 
        
        for i in range(len(probas_pluie)):
            if probas_pluie[i] > 0:
                texte_pluie = f"{probas_pluie[i]}%\n({hauteur_pluie[i]}mm)" if hauteur_pluie[i] > 0 else f"{probas_pluie[i]}%"
                ax2.text(x[i], probas_pluie[i] + 3, texte_pluie, ha='center', va='bottom', fontsize=8, color='#1e3799', fontweight='bold')

        ax2.set_xticks(x)
        ax2.set_xticklabels(heures_labels, fontsize=10, color='#4a5568')
        
        fig.tight_layout()
        
        # Sauvegarde temporaire de l'image
        chemin_image = "meteo_du_jour.png"
        plt.savefig(chemin_image, bbox_inches='tight')
        plt.close()

        # 3. Envoi sur Telegram
        url_telegram = f"https://api.telegram.org/bot{telegram_token}/sendPhoto"
        with open(chemin_image, 'rb') as photo:
            requests.post(url_telegram, data={'chat_id': telegram_chat_id, 'caption': f"📊 Voici ton bulletin météo pour {nom_complet} !"}, files={'photo': photo})
            
        # Nettoyage
        os.remove(chemin_image)
        print("✅ Bulletin envoyé avec succès !")
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")

# --- CONFIGURATION (Mets tes infos ici) ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
VILLE_CIBLE = "Meudon"

generer_et_envoyer_meteo(VILLE_CIBLE, TOKEN, CHAT_ID)
