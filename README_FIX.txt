NSE Insight CSRF Fix

The latest Render log confirms the Waitress service is live.

The remaining functional error is:
Forbidden (Origin checking failed - https://nse-insight.onrender.com does not match any trusted origins.): /refresh/

Replace:
nse_insight/settings.py

This patch adds:
- CSRF_TRUSTED_ORIGINS with https://nse-insight.onrender.com
- support for an optional CSRF_TRUSTED_ORIGINS environment variable
- automatic trust of Render's RENDER_EXTERNAL_HOSTNAME when available

The favicon.ico 404 is harmless.

Do not treat the old "Worker ... code 139" lines before the Waitress handover as
evidence that the new Waitress process is crashing. The log shows the old
Gunicorn master was terminated while the new Waitress service came live.
