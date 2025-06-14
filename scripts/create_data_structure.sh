#!/bin/bash

set -e  # Exit on any error

echo "🔧 Creating base directory structure..."

# Define base directories
DIRS=("data/db" "data/history" "data/documents" "scripts/templates")

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

echo "📝 Creating system_message.txt and welcome_message.txt..."

# Create and populate template messages
TEMPLATE_DIR="scripts/templates"
SYSTEM_MESSAGE_TEMPLATE="$TEMPLATE_DIR/system_message.template.txt"
WELCOME_MESSAGE_TEMPLATE="$TEMPLATE_DIR/welcome_message.template.txt"

# Create template files
if [ ! -f "$SYSTEM_MESSAGE_TEMPLATE" ]; then
    cat <<EOF > "$SYSTEM_MESSAGE_TEMPLATE"
# System Message

This is an automated system setup script.  
It prepares the base folder structure and initializes key project files for use.

- Directory: \`data/\`
- Created on: $(date)
EOF
    echo "✅ Created template: $SYSTEM_MESSAGE_TEMPLATE"
else
    echo "⚠️ Template already exists: $SYSTEM_MESSAGE_TEMPLATE"
fi

if [ ! -f "$WELCOME_MESSAGE_TEMPLATE" ]; then
    cat <<EOF > "$WELCOME_MESSAGE_TEMPLATE"
# Welcome Message

Welcome to the project! 🎉  
The environment has been initialized and you're ready to begin.

Be sure to check out the \`data/documents\` folder for working files.
EOF
    echo "✅ Created template: $WELCOME_MESSAGE_TEMPLATE"
else
    echo "⚠️ Template already exists: $WELCOME_MESSAGE_TEMPLATE"
fi

# Copy templates to actual files if they don't exist
SYSTEM_MESSAGE_FILE="data/system_message.txt"
WELCOME_MESSAGE_FILE="data/welcome_message.txt"

if [ ! -f "$SYSTEM_MESSAGE_FILE" ]; then
    cp "$SYSTEM_MESSAGE_TEMPLATE" "$SYSTEM_MESSAGE_FILE"
    echo "✅ Created: $SYSTEM_MESSAGE_FILE from template"
else
    echo "⚠️ File already exists: $SYSTEM_MESSAGE_FILE"
fi

if [ ! -f "$WELCOME_MESSAGE_FILE" ]; then
    cp "$WELCOME_MESSAGE_TEMPLATE" "$WELCOME_MESSAGE_FILE"
    echo "✅ Created: $WELCOME_MESSAGE_FILE from template"
else
    echo "⚠️ File already exists: $WELCOME_MESSAGE_FILE"
fi

# FINAL SYSTEM MESSAGE
echo ""
echo "🎉 Directory and file structure successfully initialized under 'data/'"
echo "✅ Template files stored in $TEMPLATE_DIR"
echo "✅ Setup complete. You can start working with your project."
