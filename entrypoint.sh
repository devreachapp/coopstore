#!/bin/bash
set -e  # Exit script on first error

echo "🚀 Running database migrations..."
flask db stamp head
flask db migrate -m "Fixing migration issue"
flask db upgrade

#python run.py

echo "🔄 Resetting failed PostgreSQL transactions..."
psql $DATABASE_URL -c "ROLLBACK;" || echo "⚠️ No transaction to rollback"

echo "✅ Starting Flask application with extended execution tolerance..."
# ADDED --timeout 120 to prevent Gunicorn from killing the worker during MetaAPI handshakes
exec gunicorn -w 4 -b 0.0.0.0:$PORT --timeout 120 run:app
