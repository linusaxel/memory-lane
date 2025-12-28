#!/bin/bash
set -e

cd "$(dirname "$0")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting Memory Lane...${NC}"

# Check for .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Copy .env.example and configure it.${NC}"
fi

# Start database
echo "Starting database..."
docker compose up -d

# Wait for database to be ready
echo "Waiting for database..."
until docker compose exec -T db pg_isready -U memorylane > /dev/null 2>&1; do
    sleep 1
done
echo -e "${GREEN}Database ready${NC}"

# Install dependencies if needed
if [ ! -d "venv" ] && [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo -e "${GREEN}Memory Lane is ready${NC}"
echo ""
echo "Next steps:"
echo "  python -m pipeline.run_all    # Run full pipeline"
echo "  python -m pipeline.ingest     # Run single stage"
echo "  uvicorn api.main:app --reload # Start API server"
