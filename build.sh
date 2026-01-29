#!/bin/bash
echo "Running database migrations..."
python migrate_shelf_user_id.py
echo "Migrations completed!"
