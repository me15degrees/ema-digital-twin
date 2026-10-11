import json
import csv
import os
import paho.mqtt.client as mqtt
from datetime import datetime

# ==========================================
# TEST CONFIGURATION
# ==========================================
NOME_DO_TESTE = "ensaio_alternado_01"
ARQUIVO_NORMAL = f"{NOME_DO_TESTE}_normal.csv"
ARQUIVO_CORRUPTED = f"{NOME_DO_TESTE}_corrupted.csv"

CABECHALHOS = [
    "timestamp", "cycle_index", "mode", "position", "velocity", 
    "current", "temperature", "friction_cc", "health_index", "status"
]

def inicializar_csvs():
    for arquivo in [ARQUIVO_NORMAL, ARQUIVO_CORRUPTED]:
        if not os.path.isfile(arquivo):
            with open(arquivo, mode='w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=CABECHALHOS)
                writer.writeheader()
            print(f"File '{arquivo}' created successfully.")

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Logger connected to MQTT. Saving to files separated by mode.")
    client.subscribe("ema/telemetry")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        payload['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        mode = payload.get("mode", "NORMAL")
        arquivo_alvo = ARQUIVO_CORRUPTED if mode == "CORRUPTED" else ARQUIVO_NORMAL
        
        with open(arquivo_alvo, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=CABECHALHOS)
            writer.writerow(payload)
            
        print(f"[{mode}] Cycle {payload.get('cycle_index')} | Saved to {arquivo_alvo} | Status: {payload['status']}")
        
    except Exception as e:
        print(f"Error saving data: {e}")

if __name__ == "__main__":
    inicializar_csvs()
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ema_data_logger")
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.connect("localhost", 1883, 60)
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nLogger terminated by user.")


