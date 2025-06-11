#!/bin/bash

# Create base directories
mkdir -p data/db
mkdir -p data/history
mkdir -p data/documents

# Create blank files in documents
touch data/documents/orders.txt
touch data/documents/realistic_restaurant_reviews.csv

echo "Directory and file structure created successfully under 'data/'"
