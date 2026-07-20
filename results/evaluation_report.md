# P2P Energy Trading System - Evaluation Framework Summary Report

This report documents performance benchmarks for MAPPO policies against non-learning baselines.

## Performance Metrics Overview

| Experiment | Mean Cost (₹) | Cost Red. vs Grid (%) | Voltage Violations (%) | P2P Utilisation (%) |
| :--- | :--- | :--- | :--- | :--- |
| Grid only | 302283.68 ± 0.00 | 0.00% | 4.586% | 0.00% |
| Heuristic | 270099.12 ± 0.00 | 10.65% | 4.586% | 98.72% |
| No battery | 269479.70 ± 0.00 | 10.85% | 4.586% | 96.65% |
| Random | 291216.69 ± 393.63 | 3.66% | 4.491% | 52.52% |
| Trained | 269764.45 ± 0.00 | 10.76% | 4.320% | 119.40% |

## Statistical Significance Analysis

 Welch's t-test comparing the trained policy against other baseline policies on total cost (alpha = 0.05):

- **vs Grid only**: p = 0.00000, Cohen's d = 0.000 (**Significant**)
- **vs Heuristic**: p = 0.00000, Cohen's d = 0.000 (**Significant**)
- **vs No battery**: p = 0.00000, Cohen's d = 0.000 (**Significant**)
- **vs Random**: p = 0.00000, Cohen's d = -77.073 (**Significant**)

## Verification Success Thresholds

- **Cost reduction (>= 10%)**: 10.76% - PASSED
- **Voltage Safety (< 1%)**: 4.320% - FAILED
- **Thermal Safety (< 1%)**: 0.000% - PASSED
- **P2P Utilisation (> 60%)**: 119.40% - PASSED
