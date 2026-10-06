import json
import time
import random
import paho.mqtt.client as mqtt

# Paramètres MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "aircraft/actuator/ema_1"

class EMASimulator:
    def __init__(self):
        # États physiques du système (basés sur le modèle REPRISE)
        self.position = 0.0          # x_ema (mm)
        self.velocity = 0.0          # Vitesse linéaire / angulaire normalisée
        self.omega = 0.0             # w : Vitesse angulaire du moteur (rad/s)
        self.current = 5.0           # I_q (A) - Courant nominal en quadrature
        self.temperature = 25.0      # Température interne du boîtier (°C)
        self.health_index = 100.0    # HI (%) de 100 à 0
        
        # Paramètres physiques et géométriques de l'EMA
        self.J_m = 0.0001            # Inertie équivalente au niveau moteur (kg·m²)
        self.K_t = 0.5               # Constante de couple du moteur (N·m/A)
        self.N_red = 50.0            # Rapport de réduction total (réducteur + vis à billes)
        self.resistance = 0.5        # Résistance interne pour l'effet Joule (Ohms)
        
        # Paramètres de frottement (Modèle Wauthion et al., 2021)
        self.Cc = 0.1                # Couple de Coulomb (frottement sec)
        self.Be = 0.02               # Coefficient de frottement visqueux
        self.p_L = 0.05              # Paramètre dépendant de la charge
        
        # Indicateur d'état de dégradation / panne (ex: perte de lubrification)
        self.degraded = False        

    def step(self, target_pos, external_load=300.0, dt=0.1):
        # 1. Calcul de l'erreur de position (Profil de consigne en triangle)
        error = target_pos - self.position
        
        # Commande de vitesse proportionnelle
        target_omega = error * 2.0
        
        # 2. Modèle de frottement dynamique Cf (Coulomb + Visqueux + Charge)
        # C_f = Cc * sign(w) + p_L * (F_ema / N_red) * sign(w * F_ema) + Be * w
        sign_omega = 1.0 if self.omega > 0 else (-1.0 if self.omega < 0 else 0.0)
        
        # Si une dégradation / perte de lubrification est injectée, les frottements augmentent fortement
        if self.degraded:
            self.Cc = min(2.5, self.Cc * 1.02)  # Augmentation progressive du frottement sec
            self.Be = min(0.5, self.Be * 1.02)  # Augmentation du frottement visqueux

        friction_torque = (self.Cc * sign_omega) + \
                          (self.p_L * (external_load / self.N_red) * sign_omega) + \
                          (self.Be * self.omega)

        # 3. Dynamique du moteur : Équation d'accélération (dw/dt)
        # dw/dt = (1 / J_m) * [ K_t * I_q - (F_ema / N_red) - C_f ]
        estimated_f_ema = external_load * 0.7  # Force transmise estimée
        acceleration = (1.0 / self.J_m) * (self.K_t * self.current - (estimated_f_ema / self.N_red) - friction_torque)
        
        # Mise à jour de la vitesse angulaire et de la position
        self.omega += acceleration * dt
        self.velocity = self.omega / self.N_red
        self.position += self.velocity * dt

        # 4. Calcul du courant moteur (I_q) nécessaire pour suivre la consigne et vaincre les frottements
        base_current = 5.0 + abs(self.omega) * 0.1 + (friction_torque / self.K_t)
        if self.degraded:
            base_current *= 2.2  # Surintensité caractéristique observée dans le projet REPRISE sans lubrifiant
            
        # Ajout d'un bruit de mesure réaliste
        self.current = max(0.0, base_current + random.uniform(-0.1, 0.1))

        # 5. Modèle thermique équivalent à 1er ordre (Effet Joule I^2*R et dissipation thermique)
        joule_heating = (self.current ** 2) * self.resistance * 0.015
        cooling_factor = 0.04 * (self.temperature - 25.0)
        self.temperature += (joule_heating - cooling_factor) * dt

        # 6. Algorithme de PHM (Health Index - HI)
        # Dégradation accélérée si la température dépasse 60°C ou si le courant dépasse 15A
        if self.temperature > 60.0 or self.current > 15.0 or self.degraded:
            degradation_rate = 0.2 if not self.degraded else 0.8
            self.health_index = max(0.0, self.health_index - degradation_rate)

    def get_payload(self):
        # Détermination du statut pour Node-RED / Tableau de bord
        if self.health_index < 50.0:
            status = "CRITICAL"
        elif self.health_index < 80.0:
            status = "WARNING"
        else:
            status = "NOMINAL"
            
        return {
            "position": round(self.position, 2),
            "velocity": round(self.velocity, 2),
            "current": round(self.current, 2),
            "temperature": round(self.temperature, 2),
            "health_index": round(self.health_index, 2),
            "status": status
        }

def main():
    client = mqtt.Client()
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(" Connecté au Broker MQTT avec succès.")
    except Exception as e:
        print(f" Erreur de connexion MQTT (le broker tourne-t-il via Docker ?) : {e}")
        return

    sim = EMASimulator()
    print(" Démarrage de la simulation EMA (Appuyez sur Ctrl+C pour quitter)...")
    
    cycle_counter = 0
    
    try:
        while True:
            # Profil de consigne en triangle (simulation des tests de pré-vol)
            target = 30.0 * random.choice([-1, 1])
            load = random.choice([300.0, 800.0]) # Charge nominale ou élevée (tests REPRISE)
            
            for step_count in range(25):
                cycle_counter += 1
                
                # Injection automatique d'une panne (perte de lubrification) après 30 itérations pour le test
                if cycle_counter > 30:
                    sim.degraded = True
                
                sim.step(target, external_load=load)
                
                payload = sim.get_payload()
                payload_json = json.dumps(payload)
                
                client.publish(MQTT_TOPIC, payload_json)
                print(f"Publié [{payload['status']}] -> Pos: {payload['position']}mm | I: {payload['current']}A | T: {payload['temperature']}°C | HI: {payload['health_index']}%")
                
                time.sleep(0.4)
                
    except KeyboardInterrupt:
        print("\n Simulation arrêtée par l'utilisateur.")
        client.disconnect()

if __name__ == "__main__":
    main()