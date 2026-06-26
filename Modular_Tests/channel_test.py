import sounddevice as sd
import numpy as np

data = sd.rec(frames=48000, samplerate=48000, channels=2, dtype='int32', device=1)
sd.wait()

canal_L = data[:, 0]
canal_R = data[:, 1]

print(f"Canal L - max: {np.max(np.abs(canal_L))}, promedio: {np.mean(np.abs(canal_L))}")
print(f"Canal R - max: {np.max(np.abs(canal_R))}, promedio: {np.mean(np.abs(canal_R))}")
