#!/bin/bash

# Setup script untuk NOC RAG POC
# Script ini akan melakukan instalasi dan konfigurasi awal

set -e  # Exit on error

echo "======================================"
echo "NOC RAG POC - Setup Script"
echo "======================================"
echo ""

# Cek Python version
echo "Checking Python version..."
python3 --version

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f .env ]; then
    echo ""
    echo "File .env tidak ditemukan!"
    echo "Copy env.template menjadi .env? (y/n)"
    read -r response
    if [ "$response" = "y" ]; then
        cp env.template .env
        echo ".env file created from template"
        echo ""
        echo "PENTING: Edit file .env dan isi DEEPSEEK_API_KEY!"
        echo ""
    else
        echo "Skip .env creation"
    fi
else
    echo ""
    echo ".env file already exists"
fi

# Run migrations
echo ""
echo "Running database migrations..."
python3 manage.py makemigrations
python3 manage.py migrate

# Ask to create superuser
echo ""
echo "Buat superuser untuk Django admin? (y/n)"
read -r response
if [ "$response" = "y" ]; then
    python3 manage.py createsuperuser
else
    echo "Skip superuser creation"
fi

echo ""
echo "======================================"
echo "Setup completed!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file dan isi DEEPSEEK_API_KEY"
echo "2. Jalankan server: python3 manage.py runserver"
echo "3. Akses API di: http://127.0.0.1:8000/"
echo "4. Akses admin di: http://127.0.0.1:8000/admin/"
echo ""
echo "Lihat QUICKSTART.md untuk panduan testing API"
echo ""
