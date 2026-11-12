import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
snapshot = json.loads(Path('/scratch/snapshot.json').read_text())
thermal = snapshot['document']['hardware'].get('simulator', {}).get('thermal')
report = {'kind':'snapshot_model_analysis','qualification':False}
if thermal:
    x = np.linspace(0, 60, 121)
    capacity = thermal['capacity_j_per_c']; loss = thermal['loss_w_per_c']
    equilibrium = thermal['ambient_c'] + thermal['heat_input_w'] / loss
    y = equilibrium + (thermal['initial_c']-equilibrium)*np.exp(-loss*x/capacity)
    plt.plot(x, y); plt.xlabel('Time (s)'); plt.ylabel('Temperature (degC)')
    plt.title('Snapshot thermal model, not physical measurements')
    plt.savefig('analysis.png')
    report['equilibrium_c'] = equilibrium
recording = Path('/scratch/recording.csv')
if recording.exists():
    import csv
    report['copied_recording_rows'] = len(list(csv.DictReader(recording.open())))
Path('analysis.json').write_text(json.dumps(report))
