#!/usr/bin/env bash
# exit on error
set -o errexit

echo "========================================"
echo "Render Build Script Starting..."
echo "========================================"

# Check for DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL environment variable is NOT set!"
    echo "⚠️  WARNING: Will use SQLite fallback (data will be lost on restart!)"
    echo ""
    echo "To fix this:"
    echo "1. Go to your Render Dashboard"
    echo "2. Create a PostgreSQL database (if not already created)"
    echo "3. Connect it to this web service"
    echo "4. DATABASE_URL should be automatically added"
    echo ""
    echo "Continuing with build anyway..."
else
    echo "✅ DATABASE_URL is set: ${DATABASE_URL:0:20}..."
fi

echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Collecting static files..."
python manage.py collectstatic --no-input

echo ""
echo "Running migrations..."
python manage.py migrate --no-input

echo ""
echo "Verifying database tables..."
python manage.py showmigrations orders

echo ""
echo "========================================"
echo "Build complete!"
echo "========================================"
