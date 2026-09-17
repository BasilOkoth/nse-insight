NSE Insight - Runtime Isolation Fix

Why this second fix exists
--------------------------
The /health/ endpoint is now returning HTTP 200, but Gunicorn workers still
exit with code 139 (SIGSEGV) a few seconds later. That means the lightweight
Django health endpoint itself is working, while the process hosting it is
crashing at the server/runtime layer.

This package therefore makes two targeted changes:

1. Pin Render to Python 3.13.15 instead of relying on the platform default.
2. Replace Gunicorn with Waitress 3.0.2 for this deployment.

Waitress is a pure-Python WSGI server, which removes Gunicorn's forked worker
process from the equation and gives us a clean diagnostic path.

Replace these files in the repository:
- requirements.txt
- render.yaml

Add this new file at the repository root:
- .python-version

Keep the previous /health/ and lazy-import changes already made to:
- nse_insight/urls.py
- market/views.py

Then commit/push and redeploy on Render.

Expected healthy behavior:
- /health/ returns 200
- no repeating "Worker ... was sent code 139!" lines
- the service remains listening on $PORT

If the service stays up but only crashes when opening the dashboard, the next
target is the Pandas/NumPy/lxml analytics stack rather than the web server.
