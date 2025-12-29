# Proactive Failure Prediction: Package Research

_Research completed: 2025-12-29_

## Executive Summary

**Recommended approach**: ADTK (primary) + ruptures (change-point detection)

These two lightweight packages provide effective time-series anomaly detection without ML model training overhead. They integrate well with Bo1's existing `PerformanceMonitor` service and Redis time-series storage.

---

## Evaluation Criteria

| Criterion | Requirement |
|-----------|-------------|
| License | MIT or Apache 2.0 preferred |
| Python | 3.11+ support |
| Dependencies | Minimal; no GPU required |
| Memory | Low footprint (<100MB for detection) |
| Integration | Works with Redis time-series, Postgres |
| Maintenance | Active (commits in last 12 months) |

---

## Package Comparison

### ML-Based Anomaly Detection

| Package | License | Python | GPU Required | Memory | Maintenance | Fit |
|---------|---------|--------|--------------|--------|-------------|-----|
| [PyOD](https://github.com/yzhao062/pyod) | BSD-2 | 3.8+ | No (optional) | Medium | Active (2025) | Medium |
| [Alibi Detect](https://github.com/SeldonIO/alibi-detect) | Apache 2.0 | 3.8+ | Optional | High | Active (Dec 2025) | Low |
| [ADTK](https://github.com/arundo/adtk) | MPL-2.0 | 3.5+ | No | Low | Stable | **High** |
| [Luminaire](https://github.com/zillow/luminaire) (Zillow) | Apache 2.0 | 3.7+ | No | Medium | Moderate | Medium |
| [Merlion](https://github.com/salesforce/Merlion) | BSD-3 | 3.8+ | Optional | High | Active | Low |
| [Luminol](https://github.com/linkedin/luminol) (LinkedIn) | Apache 2.0 | 2.7/3.x | No | Low | Inactive | Low |

### Statistical/Rule-Based

| Package | License | Python | GPU Required | Memory | Maintenance | Fit |
|---------|---------|--------|--------------|--------|-------------|-----|
| [ruptures](https://github.com/deepcharles/ruptures) | BSD-2 | 3.6+ | No | Low | Active | **High** |
| [Prophet](https://github.com/facebook/prophet) | MIT | 3.7+ | No | Medium | Active | Medium |
| [statsmodels](https://github.com/statsmodels/statsmodels) | BSD-3 | 3.8+ | No | Medium | Active | Medium |

### AIOps Platforms

| Platform | License | Python Agent | Self-Hosted | Fit |
|----------|---------|--------------|-------------|-----|
| [Apache SkyWalking](https://github.com/apache/skywalking) | Apache 2.0 | Yes | Yes | Low (overkill) |
| [Seldon Core](https://github.com/SeldonIO/seldon-core) | Apache 2.0 | Yes | Yes (k8s) | Low (requires k8s) |

---

## Recommended Packages

### Primary: ADTK (Anomaly Detection Toolkit)

**Why ADTK:**
- Designed specifically for time-series anomaly detection
- Rule-based approach matches Bo1's existing threshold logic
- Composable detectors, transformers, and aggregators
- No training required - uses statistical methods
- Lightweight: ~50KB package, minimal dependencies
- Works directly with pandas Series (easy Redis data conversion)

**Detectors available:**
- `ThresholdAD`: Static threshold crossing
- `QuantileAD`: Percentile-based outliers
- `InterQuartileRangeAD`: IQR-based outliers
- `PersistAD`: Values persisting above/below threshold
- `LevelShiftAD`: Sudden level changes
- `VolatilityShiftAD`: Variance changes
- `SeasonalAD`: Seasonal pattern anomalies

**Integration sketch:**
```python
from adtk.detector import QuantileAD, LevelShiftAD
from adtk.aggregator import AndAggregator
import pandas as pd

# Get data from existing PerformanceMonitor
values = performance_monitor.get_metric_values("api_response_time_ms", window_minutes=60)
ts = pd.Series({v[1]: v[0] for v in values})
ts.index = pd.to_datetime(ts.index, unit='s')

# Detect anomalies
quantile_detector = QuantileAD(high=0.99, low=0.01)
level_shift_detector = LevelShiftAD(c=6.0, side='both', window=5)

# Combine detectors
aggregator = AndAggregator()
anomalies = aggregator.aggregate({
    'quantile': quantile_detector.detect(ts),
    'level_shift': level_shift_detector.detect(ts)
})
```

### Secondary: ruptures (Change-Point Detection)

**Why ruptures:**
- Specialized in detecting structural changes in time series
- Useful for catching gradual degradation (not just spikes)
- Multiple algorithms: PELT, Binary Segmentation, Dynamic Programming
- Peer-reviewed (academic research backing)
- ~100KB package

**Use case:**
- Detect when baseline behavior shifts (e.g., response time creep)
- Identify regime changes in error rates
- Complement ADTK's point anomaly detection

**Integration sketch:**
```python
import ruptures as rpt
import numpy as np

# Convert Redis data to array
values = [v[0] for v in performance_monitor.get_metric_values("api_response_time_ms", 60)]
signal = np.array(values)

# Detect change points
algo = rpt.Pelt(model="rbf").fit(signal)
change_points = algo.predict(pen=10)  # penalty parameter

# change_points contains indices where behavior changed
```

---

## Packages Not Recommended

### PyOD
- Excellent for multivariate outlier detection, but requires training
- Overkill for Bo1's relatively simple metric streams
- Better suited for detecting unusual combinations of features

### Alibi Detect
- Designed for ML model monitoring (drift detection)
- Heavy dependencies (TensorFlow or PyTorch optional but common)
- More suited for detecting when input data distributions shift

### Merlion
- Comprehensive but heavy (Salesforce enterprise scale)
- Dashboard and PySpark integrations add complexity
- Requires more setup than Bo1 needs

### Prophet
- Excellent for forecasting, but anomaly detection is secondary
- Requires fitting a model (slower for real-time use)
- Better for batch analysis than streaming alerts

### Apache SkyWalking
- Full APM platform with its own data collection
- Would duplicate Prometheus/Grafana setup
- AIOps engine is incubating, not production-ready

### Seldon Core
- Requires Kubernetes (Bo1 uses SSH to droplet)
- Designed for ML model deployment, not general monitoring

---

## Integration Approach

### Phase 1: Add ADTK Detectors (Low effort)

1. Add `adtk` to requirements
2. Create `backend/services/anomaly_detector.py`
3. Wrap ADTK detectors with Bo1's Redis data format
4. Add to existing `PerformanceMonitor.analyze_trends()` method
5. Emit ntfy alerts on anomaly detection (existing pattern)

### Phase 2: Add Change-Point Detection (Low effort)

1. Add `ruptures` to requirements
2. Extend `anomaly_detector.py` with change-point detection
3. Run on longer windows (hourly) to detect baseline drift
4. Surface in admin dashboard as "behavior changes"

### Phase 3: Predictive Alerting (Medium effort)

1. Store detected patterns in `error_patterns` table
2. Use pattern frequency to predict impending issues
3. Add "predicted degradation" severity level
4. Optional: simple linear regression on metric trends

---

## Estimated Effort

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Phase 1 | 2-4 hours | `adtk>=0.6.2` |
| Phase 2 | 1-2 hours | `ruptures>=1.1.8` |
| Phase 3 | 4-8 hours | None (uses existing stack) |

---

## Data Sources (Existing)

Bo1 already collects:
- `perf:metrics:*` - Redis sorted sets with timestamped values
- `api_costs` table - LLM costs per request
- `error_patterns` table - Classified errors with match counts
- Prometheus metrics (via middleware)

The existing `PerformanceMonitor` service provides:
- `record_metric()` - Store time-series data
- `get_metric_values()` - Retrieve windowed data
- `get_degradation_score()` - Current vs baseline comparison
- `analyze_trends()` - Multi-metric health check

ADTK and ruptures can operate directly on data from `get_metric_values()`.

---

## References

- [ADTK Documentation](https://adtk.readthedocs.io/en/stable/)
- [ruptures Documentation](https://centre-borelli.github.io/ruptures-docs/)
- [PyOD GitHub](https://github.com/yzhao062/pyod)
- [Alibi Detect GitHub](https://github.com/SeldonIO/alibi-detect)
- [Merlion GitHub](https://github.com/salesforce/Merlion)
