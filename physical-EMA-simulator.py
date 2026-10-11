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

    def step(self, target_pos, external_load=300.0, dt=0.001):
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

        # Calculation of differential equations and corrected acceleration limit
        d_omega = (1.0 / self.J_m) * (self.K_t * self.current - (F_ema / self.N_red) - friction_torque)
        d_omega = max(-50000.0, min(50000.0, d_omega)) # <--- Limite aplicado no sítio correto
        
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
            "friction_cc": round(self.Cc, 3), 
            "health_index": round(self.health_index, 2),
            "status": status
        }

if __name__ == "__main__":
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ema_simulator_pub")
    client.connect("localhost", 1883, 60)
    
    print("Starting Physical EMA Simulation... Publishing to 'ema/telemetry'")
    
    target = 10.0
    cycle = 1
    
    try:
        while True:
            print(f"\n{'='*50}\n=== STARTING COMPLETE CYCLE {cycle} ===\n{'='*50}")
            
            # We reset the simulator object at the beginning of each cycle to clear thermal/mechanical damage and avoid the simulation stagnating in a CRITICAL state. 
    
            sim = EMAPhysicalSimulator() 
            
            # Definition of the 4 phases (30s each = 300 steps of 0.1s)
            fases = [
                {"phase": "IN-FLIGHT", "mode": "NORMAL", "steps": 300, "degraded": False},
                {"phase": "IN-FLIGHT", "mode": "CORRUPTED", "steps": 300, "degraded": True},
                {"phase": "GROUND", "mode": "NORMAL", "steps": 300, "degraded": False},
                {"phase": "GROUND", "mode": "CORRUPTED", "steps": 300, "degraded": True}
            ]
            
            for f in fases:
                print(f"\n>>> CURRENT: {f['phase']} | MODE: {f['mode']} <<<")
                sim.degraded = f['degraded']
                
                # If we switch back to NORMAL mode, we virtually "fix" the temperature and health so the engine keeps running.
                if not sim.degraded:
                    sim.health_index = 100.0
                    sim.temperature = 25.0
                
                for step in range(f['steps']):
                    sim.step(target_pos=target)
                    payload = sim.get_payload()
                    
                    # We inject the contextual metadata directly into the JSON.
                    payload["cycle_index"] = cycle
                    payload["phase"] = f["phase"]
                    payload["mode"] = f["mode"]
                    
                    client.publish("ema/telemetry", json.dumps(payload))
                    time.sleep(0.1)
            
            cycle += 1
            
    except KeyboardInterrupt:
        print("\nPhysical simulation terminated by user.")