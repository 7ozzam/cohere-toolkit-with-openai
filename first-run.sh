#!/bin/bash

# Ensure the script exits if any command fails
set -e
set -x  # Enable verbose mode to show commands as they are executed

# Activate the current conda environment
echo "Activating conda environment..."
. $(conda info --base)/etc/profile.d/conda.sh
conda activate "$CONDA_DEFAULT_ENV"

# Export PYTHONPATH
export PYTHONPATH="$PYTHONPATH:$PWD/src"
echo "PYTHONPATH set to: $PYTHONPATH"

# Run the setup steps
echo "Running setup..."
if poetry install --with setup,dev --verbose; then
    echo "Dependencies installed successfully."
else
    echo "Failed to install dependencies."
    exit 1
fi

# Run migrations
echo "Running migrations..."
if poetry run alembic -c src/backend/alembic.ini upgrade head; then
    echo "Migrations completed successfully."
else
    echo "Migrations failed."
    exit 1
fi

# Start backend CLI
echo "Starting backend CLI..."
if poetry run python src/backend/cli/main.py; then
    echo "Backend CLI started successfully."
else
    echo "Failed to start backend CLI."
    exit 1
fi


# Start development server
echo "Starting development server..."
# docker compose up --build -d
