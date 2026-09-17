NSE Insight Render Fix

Replace these files in your repository:
- render.yaml
- nse_insight/urls.py
- market/views.py

Changes:
- Gunicorn reduced to 1 worker / 1 thread.
- Added lightweight /health/ endpoint.
- Render health check moved from / to /health/.
- OpenMP/OpenBLAS/MKL/NumExpr thread counts limited to 1.
- Pandas/NumPy-heavy imports moved out of Django startup and into the views that need them.
- Added max-requests and jitter.

No changes were made to requirements.txt, analysis_engine.py, nse_data.py,
templates, scoring logic, or data files.
