#!/bin/bash
# Start Vite dev server in the background
pnpm dev &
VITE_PID=$!

echo "Waiting for Vite dev server to start..."
# Wait until the server is actually responding (up to 10 seconds)
for i in {1..20}; do
  if curl -s http://localhost:5173 > /dev/null; then
    break
  fi
  sleep 0.5
done

echo "Vite is ready! Launching Qt shell..."
# Start the Qt shell
ZMAN_DEV=1 python3 server_qt.py

# When the Qt shell is closed, kill the Vite server
kill $VITE_PID
