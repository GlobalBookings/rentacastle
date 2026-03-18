#!/bin/bash
set -e

echo "=== RentACastle Agent Deployment ==="

# Update system
apt-get update && apt-get upgrade -y

# Install Docker if not present
if ! command -v docker &> /dev/null; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
fi

# Install Docker Compose if not present
if ! command -v docker compose &> /dev/null; then
  echo "Installing Docker Compose plugin..."
  apt-get install -y docker-compose-plugin
fi

# Create app directory
mkdir -p /opt/rentacastle-agents
cd /opt/rentacastle-agents

# Clone or pull repo
if [ -d ".git" ]; then
  echo "Pulling latest..."
  git pull origin master
else
  echo "Cloning repo..."
  git clone https://github.com/GlobalBookings/rentacastle.git .
fi

cd agents

# Check .env exists
if [ ! -f ".env" ]; then
  echo "ERROR: agents/.env not found. Copy .env.example to .env and fill in your keys."
  echo "  cp .env.example .env"
  echo "  nano .env"
  exit 1
fi

# Build and start
echo "Building and starting agents..."
docker compose up -d --build

echo ""
echo "=== Deployment Complete ==="
echo "Agents are running. Check logs with:"
echo "  docker compose logs -f"
echo ""
echo "Health check:"
echo "  curl http://localhost:3100/health"
