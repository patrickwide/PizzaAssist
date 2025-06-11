#!/bin/bash

set -e  # Exit on any error

echo "🔧 Creating base directory structure..."

# Define base directories
DIRS=("data/db" "data/history" "data/documents")

for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "✅ Created directory: $dir"
    else
        echo "⚠️ Directory already exists: $dir"
    fi
done

echo "📄 Creating placeholder files in data/documents..."

# Define files
FILES=("orders.txt" "realistic_restaurant_reviews.csv")

for file in "${FILES[@]}"; do
    FILE_PATH="data/documents/$file"
    if [ ! -f "$FILE_PATH" ]; then
        touch "$FILE_PATH"
        echo "✅ Created file: $FILE_PATH"
    else
        echo "⚠️ File already exists: $FILE_PATH"
    fi
done

echo "📝 Creating system_message.md and welcome_message.md..."

# Create and populate markdown messages
SYSTEM_MESSAGE_FILE="data/system_message.md"
WELCOME_MESSAGE_FILE="data/welcome_message.md"

if [ ! -f "$SYSTEM_MESSAGE_FILE" ]; then
    cat <<EOF > "$SYSTEM_MESSAGE_FILE"
# System Message

This is an automated system setup script.  
It prepares the base folder structure and initializes key project files for use.

- Directory: \`data/\`
- Created on: $(date)
EOF
    echo "✅ Created: $SYSTEM_MESSAGE_FILE"
else
    echo "⚠️ File already exists: $SYSTEM_MESSAGE_FILE"
fi

if [ ! -f "$WELCOME_MESSAGE_FILE" ]; then
    cat <<EOF > "$WELCOME_MESSAGE_FILE"
# Welcome Message

Welcome to the project! 🎉  
The environment has been initialized and you're ready to begin.

Be sure to check out the \`data/documents\` folder for working files.
EOF
    echo "✅ Created: $WELCOME_MESSAGE_FILE"
else
    echo "⚠️ File already exists: $WELCOME_MESSAGE_FILE"
fi

# FINAL SYSTEM MESSAGE
echo ""
echo "🎉 Directory and file structure successfully initialized under 'data/'"
echo "✅ Setup complete. You can start working with your project."
