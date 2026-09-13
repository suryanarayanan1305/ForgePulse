# FORGEPULSE: Anomaly Detection & Machine Health Mathematics

## 1. Machine Health Score Formula

The health score is **deterministic and fully auditable**:

$$\text{Health} = 100 - (\text{Pen}_{\text{temp}} + \text{Pen}_{\text{vib}} + \text{Pen}_{\text{pres}} + \text{Pen}_{\text{err}} + \text{Pen}_{\text{downtime}})$$

$$\text{Health} \in [0.0, 100.0]$$

### Penalty Calculations:
- **Temperature Penalty** (Max 30 pts):
  $$\text{Pen}_{\text{temp}} = 20.0 + \left(\frac{T}{T_{\text{limit}}} - 1.0\right) \times 50.0 \quad \text{if } T > T_{\text{limit}}$$
- **Vibration Penalty** (Max 35 pts - critical mechanical health):
  $$\text{Pen}_{\text{vib}} = 25.0 + \left(\frac{V}{V_{\text{limit}}} - 1.0\right) \times 50.0 \quad \text{if } V > V_{\text{limit}}$$
- **Error Code Penalty**: 20.0 pts if active diagnostic error code present.
- **Downtime Penalty**: 20.0 pts if in `FAULT` status; 5.0 pts if in `STOPPED`.

---

## 2. Multi-Tier Anomaly Detection Architecture

```
                    ┌────────────────────────────┐
                    │ Incoming Telemetry Reading │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
             [ Level 1: Static Threshold Guard ]
             Is Temp > 85°C or Vib > 7.5 mm/s?
                         /           \
                       YES           NO
                       /               \
            (Flag Anomaly)              ▼
                           [ Level 2: Rolling Z-Score ]
                           Is |Z| = |(x - μ) / σ| > 3.0?
                                       /           \
                                     YES           NO
                                     /               \
                          (Flag Anomaly)              ▼
                                         [ Level 3: IsolationForest ]
                                         Multivariate feature anomaly?
                                                     /           \
                                                   YES           NO
                                                   /               \
                                        (Flag Anomaly)     (Mark Normal)
```

### Level 3: Scikit-Learn IsolationForest
- **Input Features**: `[temperature, vibration, pressure, rpm, power_consumption]`
- **Algorithm**: Tree-based recursive partitioning. Outliers require significantly fewer splits to isolate than clustered normal points.
- **Inference Time**: $< 1\text{ms}$ per observation.
