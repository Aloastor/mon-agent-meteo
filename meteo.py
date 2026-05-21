# --- BLOC 1 FUSIONNÉ : TEMPÉRATURES + PRÉCIPITATIONS ---
        ax1.set_facecolor('#f8f9fa')
        
        # En arrière-plan : Les barres de pluie
        ax1_pluie = ax1.twinx()
        barres_pluie = ax1_pluie.bar(x, hauteur_pluie, color='#74b9ff', alpha=0.4, width=0.5, label='Pluie (mm)')
        ax1_pluie.set_ylabel('Précipitations (mm)', color='#0984e3', fontweight='bold')
        
        # Sécurisation de l'échelle si hauteur_pluie est vide ou à 0
        max_pluie = max(hauteur_pluie) if len(hauteur_pluie) > 0 else 0
        ax1_pluie.set_ylim(0, max(max_pluie + 1.0, 3.0))
        
        # Affichage des probabilités et mm au-dessus des barres de pluie
        for i in range(len(probas_pluie)):
            if probas_pluie[i] > 0:
                texte_pluie = f"{probas_pluie[i]}%"
                if hauteur_pluie[i] > 0:
                    texte_pluie += f"\n({hauteur_pluie[i]}mm)"
                ax1_pluie.text(x[i], hauteur_pluie[i] + 0.1, texte_pluie, ha='center', va='bottom', fontsize=8, color='#1e3799', fontweight='bold')

        # En premier plan : Les courbes de température
        l1 = ax1.plot(x, temperatures, color='#ff4d4d', linewidth=2.5, label='Température (°C)', marker='o', markersize=4)
        l2 = ax1.plot(x, ressenties, color='#ff9f43', linewidth=1.5, linestyle='--', label='Ressentie (°C)')
        ax1.set_ylabel('Température (°C)', color='#ff4d4d', fontweight='bold')
        ax1.grid(True, linestyle=':', alpha=0.6, color='#cccccc')
        
        # Annotations des températures directement sur la courbe
        for i in range(len(temperatures)):
            ax1.annotate(f"{round(temperatures[i],1)}°", (x[i], temperatures[i]), textcoords="offset points", xytext=(0,8), ha='center', fontsize=9, color='#cc0000', fontweight='bold')
        
        # Configuration des axes de temps
        ax1.set_xticks(x)
        ax1.set_xticklabels(heures_labels, fontsize=10, color='#4a5568')
        ax1.set_xlim(-0.5, len(heures_labels) - 0.5)
        
        # Légende unique combinée
        lignes = l1 + l2 + [barres_pluie]
        labels = [l.get_label() for l in lignes]
        ax1.legend(lignes, labels, loc='upper right')
        
        ax1.set_title(f"BULLETIN HORAIRE — {nom_complet.upper()}", fontsize=13, fontweight='bold', pad=15, color='#2c3e50', loc='left')

        fig.tight_layout()
        
        # Sauvegarde temporaire de l'image
        chemin_image = "meteo_du_jour.png"
        plt.savefig(chemin_image, bbox_inches='tight')
        plt.close()

        # 3. Préparation du message Telegram (Texte brut ultra-compatible sans Markdown)
        max_temp = max(temperatures)
        min_temp = min(temperatures)
        global_rain = "Risque de pluie a prevoir 🌧️" if max(probas_pluie) > 30 else "Journee globalement seche ☀️"
        
        texte_telegram = (
            f"BULLETIN METEO - {nom_complet}\n\n"
            f"🌡️ Températures : Min {round(min_temp,1)}°C / Max {round(max_temp,1)}°C\n"
            f"☁️ Tendance : {global_rain}\n\n"
            f"Découvre ton graphique horaire complet ci-dessous !"
        )

        # Envoi sur Telegram (Sécurisé sans parse_mode qui fait planter)
        url_telegram = f"https://api.telegram.org/bot{telegram_token}/sendPhoto"
        with open(chemin_image, 'rb') as photo:
            response = requests.post(url_telegram, data={
                'chat_id': telegram_chat_id, 
                'caption': texte_telegram
            }, files={'photo': photo})
            
        # Nettoyage
        os.remove(chemin_image)
        print(f"👉 Statut Telegram : {response.status_code} - {response.text}")
        print("✅ Script terminé !")
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
