#!/bin/bash
# Credential Storage Setup Script
# This script helps set up secure credential storage for the Discord AI Bot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=================================="
echo "Credential Storage Setup"
echo "=================================="
echo ""

# Check if .env file exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "Creating .env file from template..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo "✓ Created .env file"
else
    echo "✓ .env file already exists"
fi

echo ""
echo "Generating secure keys..."
echo ""

# Generate SECRET_KEY for JWT
echo "1. Generating SECRET_KEY (for JWT signing)..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "   Generated: ${SECRET_KEY:0:20}..."

# Update .env file with SECRET_KEY if it's still the default
if grep -q "SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32" "$PROJECT_ROOT/.env"; then
    sed -i.bak "s|SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32|SECRET_KEY=$SECRET_KEY|g" "$PROJECT_ROOT/.env"
    echo "   ✓ Updated SECRET_KEY in .env"
else
    echo "   ⚠ SECRET_KEY already customized in .env (skipping)"
fi

echo ""

# Generate MASTER_ENCRYPTION_KEY
echo "2. Generating MASTER_ENCRYPTION_KEY (for credential vault)..."
cd "$PROJECT_ROOT"
MASTER_KEY=$(python3 scripts/manage_credentials.py generate-key 2>/dev/null | grep "MASTER_ENCRYPTION_KEY=" | cut -d= -f2)

if [ -n "$MASTER_KEY" ]; then
    echo "   Generated: ${MASTER_KEY:0:20}..."

    # Check if key is already set in .env
    if grep -q "^MASTER_ENCRYPTION_KEY=" "$PROJECT_ROOT/.env"; then
        echo "   ⚠ MASTER_ENCRYPTION_KEY already set in .env (skipping)"
    elif grep -q "^# MASTER_ENCRYPTION_KEY=" "$PROJECT_ROOT/.env"; then
        # Uncomment and set the key
        sed -i.bak "s|^# MASTER_ENCRYPTION_KEY=.*|MASTER_ENCRYPTION_KEY=$MASTER_KEY|g" "$PROJECT_ROOT/.env"
        echo "   ✓ Added MASTER_ENCRYPTION_KEY to .env"
    else
        # Add at the end of security section
        echo "MASTER_ENCRYPTION_KEY=$MASTER_KEY" >> "$PROJECT_ROOT/.env"
        echo "   ✓ Added MASTER_ENCRYPTION_KEY to .env"
    fi
else
    echo "   ✗ Failed to generate MASTER_ENCRYPTION_KEY"
fi

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. Edit .env file and add your credentials:"
echo "   - DISCORD_BOT_TOKEN (get from https://discord.com/developers/applications)"
echo "   - ANTHROPIC_API_KEY (get from https://console.anthropic.com/)"
echo "   - ADMIN_PASSWORD (change from default)"
echo ""
echo "2. (Optional) Store credentials in encrypted vault:"
echo "   python scripts/manage_credentials.py set DISCORD_BOT_TOKEN \"your-token\" token"
echo "   python scripts/manage_credentials.py set ANTHROPIC_API_KEY \"your-key\" api_key"
echo ""
echo "3. Verify credential setup:"
echo "   python scripts/manage_credentials.py health"
echo ""
echo "4. Review the credential storage guide:"
echo "   docs/CREDENTIAL_STORAGE_GUIDE.md"
echo ""
echo "=================================="
echo ""
echo "⚠ SECURITY REMINDERS:"
echo "  • Never commit .env file to version control (it's in .gitignore)"
echo "  • Use different keys for development/staging/production"
echo "  • Rotate credentials regularly (check with: python scripts/manage_credentials.py check-rotation)"
echo "  • Keep your MASTER_ENCRYPTION_KEY secure - without it, you cannot decrypt vault credentials"
echo ""
