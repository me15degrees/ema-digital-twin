import time
import json
import random
import paho.mqtt.client as mqtt

class EMAPhysicalSimulator:
    def __init__(self):
        self.position = 0.0          
        self.theta = 0.0             
        self.omega = 0.0             
        self.x_cs = 0.0              
        self.v_cs = 0.0              
        self.x_I = 0.0               
        
        self.current = 5.0           
        self.temperature = 25.0      
        self.health_index = 100.0    
        
        self.J_m = 0.0001            
        self.K_t = 0.5               
        self.N_red = 50.0            
        self.resistance = 0.5        
        
        self.Cc = 0.1                
        self.Be = 0.02               
        self.p_L = 0.05              
        
        self.M_cs = 5.0              
        self.k_s = 15000.0           
        self.k_d = 50.0              
        
        self.degraded = False        

    def step(self, target_pos, external_load=300.0, dt=0.05):
        if self.health_index <= 0.0 or self.temperature >= 110.0:
            self.omega = 0.0
            self.v_cs = 0.0
            self.current = 0.0  
            self.temperature -= 0.04 * (self.temperature - 25.0) * dt
            return

        K_pp = 2.5
        dx_I = (K_pp * (target_pos - self.position) - self.omega)
        self.x_I += dx_I * dt
        
        base_current = max(0.0, 5.0 + 0.8 * (target_pos - self.position) + 0.1 * self.x_I)
        if self.degraded:
            base_current *= 2.2
        self.current = max(0.0, min(35.0, base_current + random.uniform(-0.05, 0.05)))

        F_ema = self.k_s * (self.position - self.x_cs) + self.k_d * ((self.omega / self.N_red) - self.v_cs)
        F_load = 800.0 * self.x_cs + 5.0 * self.v_cs + external_load

        sign_omega = 1.0 if self.omega > 0 else (-1.0 if self.omega < 0 else 0.0)
        
        if self.degraded:
            self.Cc = min(2.5, self.Cc * 1.01)
            self.Be = min(0.5, self.Be * 1.01)

        friction_torque = (self.Cc * sign_omega) + (self.p_L * (F_ema / self.N_red) * sign_omega) + (self.Be * self.omega)

        d_omega = (1.0 / self.J_m) * (self.K_t * self.current - (F_ema / self.N_red) - friction_torque)
        d_theta = self.omega
        d_x_ema = self.omega / self.N_red

        d_v_cs = (1.0 / self.M_cs) * (self.k_s * (self.position - self.x_cs) + self.k_d * ((self.omega / self.N_red) - self.v_cs) - F_load)
        d_x_cs = self.v_cs

        self.omega += d_omega * dt
        self.theta += d_theta * dt
        self.position += d_x_ema * dt
        self.v_cs += d_v_cs * dt
        self.x_cs += d_x_cs * dt

        joule_heating = (self.current ** 2) * self.resistance * 0.015
        self.temperature += (joule_heating - 0.04 * (self.temperature - 25.0)) * dt

        if self.temperature > 60.0 or self.current > 15.0 or self.degraded:
            self.health_index = max(0.0, self.health_index - (0.5 if self.degraded else 0.1))

    def get_payload(self):
        status = "CRITICAL" if self.health_index < 50.0 else "WARNING" if self.health_index < 80.0 else "NOMINAL"
        return {
            "position": round(self.position, 2),
            "velocity": round(self.omega / self.N_red, 2),
            "current": round(self.current, 2),
            "temperature": round(self.temperature, 2),
            "friction_cc": round(self.Cc, 3), # Extracted to feed the DEKF estimation
            "health_index": round(self.health_index, 2),
            "status": status
        }

if __name__ == "__main__":
    # Usando VERSION2 para eliminar o aviso de depreciação
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ema_simulator_pub")
    client.connect("localhost", 1883, 60)
    
    sim = EMAPhysicalSimulator()
    print("Starting Physical EMA Simulation... Publishing to 'ema/telemetry'")
    print("Simulação configurada para 60 segundos (30s normal -> 30s degradado).")
    
    target = 10.0
    
    try:
        # 60 segundos no total (600 passos de 0.1s)
        for step in range(600):
            # Injeção da falha aos 30 segundos
            if step == 300:
                print("\n>>> INJECTING MECHANICAL DEGRADATION <<<\n")
                sim.degraded = True
                
            sim.step(target_pos=target)
            payload = sim.get_payload()
            
            client.publish("ema/telemetry", json.dumps(payload))
            time.sleep(0.1)
            
        print("\nSimulação concluída com sucesso (60 segundos atingidos).")
            
    except KeyboardInterrupt:
        print("\nSimulação física interrompida pelo usuário.")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="ema_simulator_pub")
    client.connect("localhost", 1883, 60) # Connects to standard local Mosquitto broker
    
    sim = EMAPhysicalSimulator()
    print("Starting Physical EMA Simulation... Publishing to 'ema/telemetry'")
    
    target = 10.0
    for step in range(500):
        # Introduce a degradation fault at step 200
        if step == 200:
            print("\n>>> INJECTING MECHANICAL DEGRADATION <<<\n")
            sim.degraded = True
            
        sim.step(target_pos=target)
        payload = sim.get_payload()
        
        client.publish("ema/telemetry", json.dumps(payload))
        time.sleep(0.1)