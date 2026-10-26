#!/bin/bash
# ZERO X - One command startup script
cd ~/zerox

echo "🚀 Starting ZERO X Key System..."

# Kill any old processes
pkill -f server.py 2>/dev/null
pkill -f bot.py 2>/dev/null
pkill -f "nokey@localhost.run" 2>/dev/null
sleep 1

# Start Flask server
echo "✅ Starting server..."
python server.py &
sleep 3

# Start tunnel and get URL
echo "✅ Starting tunnel..."
ssh -R 80:localhost:5000 nokey@localhost.run 2>&1 | while read line; do
    echo "$line"
    # Extract the tunnel URL
    if echo "$line" | grep -q "lhr.life"; then
        URL=$(echo "$line" | grep -o 'https://[a-zA-Z0-9]*\.lhr\.life')
        if [ ! -z "$URL" ]; then
            echo ""
            echo "🌐 Your public URL is: $URL"
            echo ""
            # Update server.py and bot.py with new URL
            sed -i "s|https://YOUR_TUNNEL_URL|$URL|g" server.py bot.py dumb_with_key.py
            sed -i "s|https://[a-zA-Z0-9]*\.lhr\.life|$URL|g" server.py bot.py dumb_with_key.py
            echo "✅ URL updated in all files!"
            echo ""
            # Start bot
            echo "✅ Starting Discord bot..."
            python bot.py &
            echo ""
            echo "════════════════════════════════"
            echo "✅ EVERYTHING IS RUNNING!"
            echo "🌐 Server URL: $URL"
            echo "🔑 Verify URL: $URL/verify"
            echo "════════════════════════════════"
        fi
    fi
done
