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

def determiner_picto_texte(proba_pluie: int, temperature: float) -> str:
    if proba_pluie is None: proba_pluie = 0
    if proba_pluie > 50:
        return "[Pluie]" if temperature > 3 else "[Neige]"
    elif proba_pluie > 20:
        return "[Nuage/Pluie]"
    elif temperature > 22:
        return "[Soleil]"
    else:
        return "[Nuageux]"

def generer_et_envoyer_meteo(ville: str, telegram_token: str, telegram_chat_id: str):
    try:
        # 1. Géocodage de la ville
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={ville}&count=1&language=fr&format=json"
        geo_res = requests.get(geo_url, timeout=5).json()
        if not geo_res.get('results'): 
            print("❌ Ville non trouvée")
            return
        lat, lon = geo_res['results'][0]['latitude'], geo_res['results'][0]['longitude']
        nom_complet = geo_res['results'][0]['name']
        
        # URL optimisée : Modèle standard + Modèle Allemand ICON Global
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
               f"&hourly=temperature_2m,precipitation,precipitation_probability,wind_speed_10m,wind_direction_10m,temperature_2m_icon_global"
               f"&forecast_days=2&timezone=auto")
        res = requests.get(url, timeout=5).json()
        
        if 'hourly' not in res:
            print(f"❌ Réponse API invalide : {res}")
            return
        
        tz_france = pytz.timezone('Europe/Paris')
        idx_depart = next((idx for idx, h in enumerate(res['hourly']['time']) if h >= (datetime.now(tz_france) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:00")), 0)
        
        nb_heures = 18
        fin = idx_depart + nb_heures
        
        # Extraction et sécurisation des températures
        temp_standard = res['hourly']['temperature_2m'][idx_depart:fin]
        temp_icon = res['hourly']['temperature_2m_icon_global'][idx_depart:fin]
        
        temp_standard = [t if t is not None else 15.0 for t in temp_standard]
        temp_icon = [t if t is not None else temp_standard[i] for i, t in enumerate(temp_icon)]
        
        matrice_temps = np.array([temp_standard, temp_icon])
        temperatures_moyennes = np.mean(matrice_temps, axis=0)
        
        # Écart visuel pour la zone d'incertitude
        temperatures_max = np.maximum(np.max(matrice_temps, axis=0), temperatures_moyennes + 0.4)
        temperatures_min = np.minimum(np.min(matrice_temps, axis=0), temperatures_moyennes - 0.4)
        
        probas_pluie = [p if p is not None else 0 for p in res['hourly']['precipitation_probability'][idx_depart:fin]]
        hauteur_pluie = [p if p is not None else 0.0 for p in res['hourly']['precipitation'][idx_depart:fin]]
        vent_vitesse = [v if v is not None else 0 for v in res['hourly']['wind_speed_10m'][idx_depart:fin]]
        vent_direction = [d if d is not None else 0 for d in res['hourly']['wind_direction_10m'][idx_depart:fin]]
        heures_labels = [h.split('T')[1][:5] for h in res['hourly']['time'][idx_depart:fin]]
        
        x = np.arange(len(heures_labels))
        
        # 2. Construction de l'image
        fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [0.8, 2.5]}, dpi=120)
        fig.patch.set_facecolor('#ffffff')
        
        # --- BLOC 0 : VENT ET CIEL ---
        ax0.set_facecolor('#f1f5f9')
        ax0.set_xlim(-0.5, len(heures_labels) - 0.5)
        ax0.set_ylim(0, 10)
        ax0.axis('off')
            
        for i in range(len(heures_labels)):
            fleche = degres_en_fleche(vent_direction[i])
            label_meteo = determiner_picto_texte(probas_pluie[i], temperatures_moyennes[i])
            ax0.text(x[i], 8.0, heures_labels[i], ha='center', va='center', fontsize=10, fontweight='bold', color='#2c3e50')
            ax0.text(x[i], 5.5, label_meteo, ha='center', va='center', fontsize=8.5, color='#0abde3', fontweight='bold')
            ax0.text(x[i], 2.2, f"{fleche}\n{round(vent_vitesse[i])} km/h", ha='center', va='center', fontsize=9, color='#4b6584', fontweight='semibold', bbox=dict(boxstyle='circle,pad=0.2', facecolor='#ffffff', edgecolor='#cbd5e1', lw=1))

        # --- BLOC 1 : TEMPÉRATURES & PRÉCIPITATIONS ---
        ax1.set_facecolor('#f8f9fa')
        
        ax1_pluie = ax1.twinx()
        barres_pluie = ax1_pluie.bar(x, hauteur_pluie, color='#74b9ff', alpha=0.35, width=0.5, label='Pluie (mm)')
        ax1_pluie.set_ylabel('Précipitations (mm)', color='#0984e3', fontweight='bold')
        max_pluie = max(hauteur_pluie) if len(hauteur_pluie) > 0 else 0
        ax1_pluie.set_ylim(0, max(max_pluie + 1.0, 3.0))
        
        for i in range(len(probas_pluie)):
            if probas_pluie[i] > 0:
                texte_pluie = f"{probas_pluie[i]}%"
                if hauteur_pluie[i] > 0: texte_pluie += f"\n({hauteur_pluie[i]}mm)"
                ax1_pluie.text(x[i], hauteur_pluie[i] + 0.1, texte_pluie, ha='center', va='bottom', fontsize=8, color='#1e3799', fontweight='bold')

        # Zone d'incertitude ombrée
        ax1.fill_between(x, temperatures_min, temperatures_max, color='#ff4d4d', alpha=0.15, label="Marge d'incertitude des modèles")
        
        l1 = ax1.plot(x, temperatures_moyennes, color='#ff4d4d', linewidth=2.5, label='Température Moyenne (°C)', marker='o', markersize=5)
        ax1.set_ylabel('Température (°C)', color='#ff4d4d', fontweight='bold')
        ax1.grid(True, linestyle=':', alpha=0.6, color='#cccccc')
        
        for i in range(len(temperatures_moyennes)):
            ax1.annotate(f"{round(temperatures_moyennes[i],1)}°", (x[i], temperatures_moyennes[i]), textcoords="offset points", xytext=(0,8), ha='center', fontsize=9, color='#cc0000', fontweight='bold')
        
        ax1.set_xticks(x)
        ax1.set_xticklabels(heures_labels, fontsize=10, color='#4a5568')
        ax1.set_xlim(-0.5, len(heures_labels) - 0.5)
        
        lignes = l1 + [barres_pluie]
        labels = [l.get_label() for l in lignes]
        labels.append("Marge d'incertitude (ECMWF/ICON)")
        ax1.legend(lignes, labels, loc='upper right')
        
        ax1.set_title(f"BULLETIN COMPOSITE — {nom_complet.upper()} (Consensus Multi-Modèles)", fontsize=12, fontweight='bold', pad=15, color='#2c3e50', loc='left')
        fig.tight_layout()
        
        chemin_image = "meteo_du_jour.png"
        plt.savefig(chemin_image, bbox_inches='tight')
        plt.close()

        # 3. Rédaction et envoi du message Telegram
        max_temp = max(temperatures_moyennes)
        min_temp = min(temperatures_moyennes)
        global_rain = "Risque de pluie à prévoir 🌧️" if max(probas_pluie) > 30 else "Journée globalement sèche ☀️"
        
        texte_telegram = (
            f"📊 CONSENSUS METEO - {nom_complet}\n\n"
            f"🌡️ Températures : Min {round(min_temp,1)}°C / Max {round(max_temp,1)}°C\n"
            f"☁️ Tendance : {global_rain}\n\n"
            f"Découvre ton graphique horaire multi-modèles ci-dessous !"
        )

        url_telegram = f"https://api.telegram.org/bot{telegram_token}/sendPhoto"
        with open(chemin_image, 'rb') as photo:
            response = requests.post(url_telegram, data={'chat_id': telegram_chat_id, 'caption': texte_telegram}, files={'photo': photo})
            print(f"👉 Statut Telegram : {response.status_code} - {response.text}")
            
        os.remove(chemin_image)
        print("✅ Script multi-modèles terminé avec succès !")
        
    except Exception as e:
        print(f"❌ Erreur générale : {str(e)}")
        raise e

# --- DEMARRAGE AUTOMATIQUE ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
VILLE_CIBLE = os.environ.get("CITY_ID")

generer_et_envoyer_meteo(VILLE_CIBLE, TOKEN, CHAT_ID)
