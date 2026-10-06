import numpy as np
import json
import paho.mqtt.client as mqtt

class EMADiagnosticMonitor:
    def __init__(self):
        self.phi_h_f = 0.1  # Matches the healthy baseline self.Cc from the physical model
        self.sigma_f = 0.02 
        self.glr_threshold_f = 1.5e5 
        self.expected_current_baseline = 5.0 # Expected normal holding current

    def inflight_passive_monitoring(self, actual_friction):
        estimated_phi_f = np.random.normal(actual_friction, self.sigma_f * 0.1)
        deviation = abs(estimated_phi_f - self.phi_h_f)
        confidence_bound = 3 * self.sigma_f # Using 3-sigma for tighter operational bounds
        
        if deviation > confidence_bound:
            print(f"[DEKF ALARM] In-flight friction anomalous: {estimated_phi_f:.3f} (Limit: {self.phi_h_f + confidence_bound:.3f})")
        else:
            print(f"[DEKF OK] In-flight friction normal: {estimated_phi_f:.3f}")

    def ground_active_monitoring(self, current_measure):
        # Calculate residual based on expected current vs actual drawn current
        healthy_residual_baseline = np.random.normal(0, 1.5) 
        enhanced_residual = abs(current_measure - self.expected_current_baseline - healthy_residual_baseline)
        
        glr_decision_value = enhanced_residual * 10000 
        
        if glr_decision_value > self.glr_threshold_f:
            print(f"[GLR ALARM] Ground residual exceeded threshold! Value: {glr_decision_value:.2f}")
        else:
            print(f"[GLR OK] Ground monitoring stable. Value: {glr_decision_value:.2f}")

monitor = EMADiagnosticMonitor()

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode('utf-8'))
    
    current = payload.get("current", 0.0)
    friction = payload.get("friction_cc", 0.1)
    status = payload.get("status")
    
    print(f"\n--- New Telemetry Received | Status: {status} ---")
    
    # Run the diagnostics against the live data
    monitor.inflight_passive_monitoring(actual_friction=friction)
    monitor.ground_active_monitoring(current_measure=current)

if __name__ == "__main__":
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ema_diagnostic_sub")
    client.on_message = on_message
    
    client.connect("localhost", 1883, 60)
    client.subscribe("ema/telemetry")
    
    print("Diagnostic Monitor Active. Listening on 'ema/telemetry'...")
    client.loop_forever()