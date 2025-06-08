#!/bin/bash

# Create base directories
mkdir -p data/db
mkdir -p data/history
mkdir -p data/reviews

# Create blank file for store metadata
touch data/db/store_metadata.json

# Create blank file in history
touch data/history/conversation_history.jsonl

# Create blank files in reviews
touch data/reviews/orders.txt
touch data/reviews/realistic_restaurant_reviews.csv

echo "Directory and file structure created successfully under 'data/'"
