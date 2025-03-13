#!/bin/bash

# Script to run the financial metrics migration

# Load database configuration from config.yaml
DB_HOST=$(grep -A 3 "postgres:" ../config/config.yaml | grep "host:" | awk '{print $2}')
DB_PORT=$(grep -A 3 "postgres:" ../config/config.yaml | grep "port:" | awk '{print $2}')
DB_USER=$(grep -A 3 "postgres:" ../config/config.yaml | grep "username:" | awk '{print $2}')
DB_PASS=$(grep -A 3 "postgres:" ../config/config.yaml | grep "password:" | awk '{print $2}')
DB_NAME=$(grep -A 3 "postgres:" ../config/config.yaml | grep "database:" | awk '{print $2}')

echo "Running migration to add financial metrics columns..."

# Run the migration script
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f add_financial_metrics.sql

# Check if migration was successful
if [ $? -eq 0 ]; then
    echo "Migration completed successfully!"
else
    echo "Migration failed. Please check the error messages above."
    exit 1
fi

echo "Financial metrics columns have been added to the database."