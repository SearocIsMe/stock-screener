#!/bin/bash

# Database configuration
DB_HOST="localhost"
DB_PORT="5432"
DB_USER="postgres"
DB_PASSWORD="postgres"
DB_NAME="stock_screener"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up PostgreSQL database for stock_screener...${NC}"

# Check if PostgreSQL is installed and running
if ! command -v psql &> /dev/null; then
    echo -e "${RED}PostgreSQL is not installed. Please install PostgreSQL and try again.${NC}"
    exit 1
fi

# Check if PostgreSQL service is running
if ! pg_isready -h $DB_HOST -p $DB_PORT > /dev/null 2>&1; then
    echo -e "${YELLOW}PostgreSQL service is not running. Attempting to start...${NC}"
    sudo service postgresql start
    sleep 2
    if ! pg_isready -h $DB_HOST -p $DB_PORT > /dev/null 2>&1; then
        echo -e "${RED}Failed to start PostgreSQL service. Please start it manually and try again.${NC}"
        exit 1
    fi
    echo -e "${GREEN}PostgreSQL service started successfully.${NC}"
fi

# Check if Redis is installed and running
if ! command -v redis-cli &> /dev/null; then
    echo -e "${RED}Redis is not installed. Please install Redis and try again.${NC}"
    exit 1
fi

# Check if Redis service is running
redis-cli ping > /dev/null 2>&1 || { echo -e "${YELLOW}Redis service is not running. Attempting to start...${NC}"; sudo service redis-server start; }

# Create database if it doesn't exist
echo -e "${YELLOW}Creating database if it doesn't exist...${NC}"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1
if [ $? -ne 0 ]; then
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "CREATE DATABASE $DB_NAME"
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to create database. Please check your PostgreSQL configuration.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Database created successfully.${NC}"
else
    echo -e "${GREEN}Database already exists.${NC}"
fi

# Run the initialization script
echo -e "${YELLOW}Running database initialization script...${NC}"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f init_db.sql

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Database schema created successfully!${NC}"
else
    echo -e "${RED}Failed to create database schema. Please check the error messages above.${NC}"
    exit 1
fi

echo -e "${YELLOW}Setting up Python environment...${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3 and try again.${NC}"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}pip is not installed. Please install pip and try again.${NC}"
    exit 1
fi

# Install required packages
echo -e "${YELLOW}Installing required Python packages...${NC}"
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Python packages installed successfully!${NC}"
else
    echo -e "${RED}Failed to install Python packages. Please check the error messages above.${NC}"
    exit 1
fi

echo -e "${GREEN}Setup completed successfully!${NC}"
echo -e "${YELLOW}You can now run the application using:${NC}"
echo -e "${GREEN}python3 run.py${NC}"

# Final check for services
echo -e "${YELLOW}Ensuring services are running: PostgreSQL and Redis${NC}"