#!/usr/bin/env bash
set -e

echo "==> Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Creating data directories..."
mkdir -p data/storage

echo "==> Running database migrations..."
alembic upgrade head

echo "==> Build complete!"
