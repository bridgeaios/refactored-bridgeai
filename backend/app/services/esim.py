import random

class EsimService:
    def get_status(self):
        return {
            "status": "active" if random.random() > 0.05 else "inactive",
            "iccid": f"8950{random.randint(10**15,10**16-1)}",
            "profile_name": "BRIDGE-OS-GLOBAL",
            "data_remaining_gb": round(random.uniform(0.5, 15.0), 1),
            "signal_bars": random.randint(2,5),
            "carrier": random.choice(["GlobalTel", "BRIDGE eSIM", "Nomad", "Airalo"])
        }
