import json
import csv
import os
import paho.mqtt.client as mqtt
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DO TESTE
# Altere esta variável para renomear o arquivo de saída
NOME_DO_TESTE = "ensaio_degradacao_01" 
# ==========================================

ARQUIVO_CSV = f"{NOME_DO_TESTE}.csv"

# Definir os cabeçalhos das colunas com base no payload do simulador + timestamp
CABECHALHOS = [
    "timestamp", "position", "velocity", "current", 
    "temperature", "friction_cc", "health_index", "status"
]

def inicializar_csv():
    """Cria o arquivo CSV e escreve o cabeçalho se o arquivo não existir."""
    if not os.path.isfile(ARQUIVO_CSV):
        with open(ARQUIVO_CSV, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=CABECHALHOS)
            writer.writeheader()
        print(f"Arquivo '{ARQUIVO_CSV}' criado com sucesso.")

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Logger conectado ao MQTT. Salvando dados em: {ARQUIVO_CSV}")
    client.subscribe("ema/telemetry")

def on_message(client, userdata, msg):
    try:
        # Decodificar o payload JSON
        payload = json.loads(msg.payload.decode('utf-8'))
        
        # Adicionar carimbo de data/hora atual
        payload['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Salvar a linha no arquivo CSV
        with open(ARQUIVO_CSV, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=CABECHALHOS)
            writer.writerow(payload)
            
        print(f"Salvo: {payload['timestamp']} | Status: {payload['status']}")
        
    except Exception as e:
        print(f"Erro ao salvar dado: {e}")

if __name__ == "__main__":
    inicializar_csv()
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ema_data_logger")
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Conectar ao broker Mosquitto local (porta padrão 1883)
    client.connect("localhost", 1883, 60)
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nLogger finalizado pelo usuário.")