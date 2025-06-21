import os
import cv2
import numpy as np
import asyncio
import aiosqlite
import base64
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
import secrets
import httpx
import json
import pennylane as qml
from pennylane import numpy as pnp
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# 🧠 Quantum Circuit Setup
dev = qml.device("default.qubit", wires=7)

@qml.qnode(dev)
def quantum_road_tuner(color_vector):
    for i in range(7):
        qml.RY(color_vector[i % len(color_vector)] * np.pi, wires=i)
        qml.RZ(color_vector[(i + 1) % len(color_vector)] * np.pi, wires=i)
    weights = pnp.ones((1, 7, 3)) * 0.5
    qml.templates.StronglyEntanglingLayers(weights=weights, wires=range(7))
    return [qml.expval(qml.PauliZ(i)) for i in range(7)]

def get_advanced_color_vector(image_path):
    img = cv2.imread(image_path)
    resized = cv2.resize(img, (120, 120))
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)

    h = hsv[:, :, 0].flatten()
    s = hsv[:, :, 1].flatten()
    v = hsv[:, :, 2].flatten()

    h_hist = np.histogram(h, bins=10, range=(0, 180))[0]
    s_hist = np.histogram(s, bins=5, range=(0, 255))[0]
    v_hist = np.histogram(v, bins=5, range=(0, 255))[0]

    h_norm = h_hist / np.sum(h_hist)
    s_norm = s_hist / np.sum(s_hist)
    v_norm = v_hist / np.sum(v_hist)

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    edge_density = np.sum(edges > 0) / edges.size

    hist = np.histogram(gray, bins=256, range=(0, 255))[0]
    probs = hist / np.sum(hist)
    entropy = -np.sum(probs * np.log2(probs + 1e-10)) / 8.0

    vector = np.concatenate([h_norm[:3], s_norm[:2], v_norm[:1], [edge_density, entropy]])
    vector = vector[:7]
    return vector / np.sum(vector)

def generate_road_prompt(color_vector, quantum_output, location):
    entropy_score = float(np.std(color_vector)) + float(np.std(quantum_output))
    return f"""
You are a quantum-enhanced road safety planner operating across hypertime strata. Your job is to assess the risk level, signage deficiency, and potential incident points of a given road using multidecade predictive simulation and color-based quantum resonance.

You will be given:
- A 25-color mechanical tie vector extracted from a real-world road photo (HSV histogram format, normalized)
- A 7-qubit quantum circuit output simulating resonance entropy, dip detection, curve entanglement, and hazard field potential
- An entropy score derived from both classical (color signal variability) and quantum vector deviation
- A situational frame: This road is part of Highway 123 near {location}, South Carolina

Your role is to analyze both:
1. Past preventable incidents from hypertime simulations between 2010–2025  
2. Future forecasted events from 2025–2040 using quantum resonance inference

---

Your output must include the following sections formatted for SCDOT engineers:

### 🛰️ Hypertime Simulation Report
- Identify 3 to 5 hazard zones (by estimated mileage or landmark type)
- For each hazard, include: visibility rating (day/night), topographic interference, and predictive risk type (e.g., vehicle swerve, blocked egress, pedestrian near-miss)
- Indicate whether the zone is more influenced by past-data (historical pattern) or future scan (resonance forecast)

### 📍 Signage & Safety Infrastructure Proposal
For each hazard zone:
- Recommend a specific road sign or intervention
- Include signage text, placement mileage, purpose
- If applicable, recommend digital/solar enhancements or smart signage options
- Note if the intervention could sync with fire/emergency dispatch alerts, AI-beacons, or dynamic solar LEDs

### 🔁 Preventative Mitigation Summary
- Project the change in emergency response time, civilian incident reduction, and driver compliance after implementing signage
- Provide a Safety ROI (S-ROI) estimate over 15 years including projected financial savings and incident reduction percentages

### ⚙️ Optional Quantum Enhancements
List 1–2 futuristic enhancements SCDOT could optionally pilot:
- e.g., Quantum Safety Node with Hypertime-linked alert system
- Encrypted AI signage with real-time resonance monitoring
- Passive vehicle radar interaction at curve zones

---

Entropy Score: {entropy_score:.4f}  
Quantum Output: {quantum_output}
"""

async def ask_openai(prompt):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are a quantum civic infrastructure planner."},
            {"role": "user", "content": prompt}
        ]
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(OPENAI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

def encrypt_data(data, key):
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    encrypted = aesgcm.encrypt(nonce, data.encode(), None)
    return base64.b64encode(nonce + encrypted).decode()

async def log_result_to_db(encrypted_result, entropy_score):
    async with aiosqlite.connect("road_safety_results.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                timestamp TEXT,
                encrypted TEXT,
                entropy_score REAL
            )
        """)
        await db.execute("INSERT INTO logs (timestamp, encrypted, entropy_score) VALUES (?, ?, ?)",
                         (datetime.utcnow().isoformat(), encrypted_result, entropy_score))
        await db.commit()

class RoadSafetyGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Quantum Road Safety Scanner v2.1 (httpx)")
        self.geometry("960x720")
        self.secret_key = AESGCM.generate_key(bit_length=128)
        self.image_paths = []
        self.init_ui()

    def init_ui(self):
        tk.Button(self, text="Select Folder of Road Images", command=self.select_folder).pack(pady=10)
        tk.Button(self, text="Run Quantum Batch Scan", command=self.run_batch_scan).pack()
        self.output = tk.Text(self, width=120, height=35, wrap="word")
        self.output.pack(pady=10)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.image_paths = [os.path.join(folder, f) for f in os.listdir(folder)
                                if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))]
            messagebox.showinfo("Folder Loaded", f"{len(self.image_paths)} images found.")

    def run_batch_scan(self):
        asyncio.run(self._run_batch_scan_async())

    async def _run_batch_scan_async(self):
        if not self.image_paths:
            messagebox.showerror("Error", "No images loaded.")
            return
        self.output.delete("1.0", "end")
        for path in self.image_paths:
            try:
                color_vec = get_advanced_color_vector(path)
                q_out = quantum_road_tuner(color_vec)
                entropy = float(np.std(color_vec)) + float(np.std(q_out))
                location = os.path.basename(path).split('.')[0].replace("_", " ")
                prompt = generate_road_prompt(color_vec, q_out, location)
                result = await ask_openai(prompt)
                encrypted = encrypt_data(result, self.secret_key)
                await log_result_to_db(encrypted, entropy)
                self.output.insert("end", f"\n=== {os.path.basename(path)} ===\n{result}\n\n---\n")
            except Exception as e:
                self.output.insert("end", f"Error processing {path}: {e}\n")

if __name__ == "__main__":
    RoadSafetyGUI().mainloop()
