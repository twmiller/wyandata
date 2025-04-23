#!/bin/bash

# Ensure the static and staticfiles directories exist
mkdir -p static
mkdir -p staticfiles

# Run collectstatic with --no-input to avoid prompting
echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Static files collection complete."
echo "You can now run the server with: python manage.py runserver 0.0.0.0:8000"
