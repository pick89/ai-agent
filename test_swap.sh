#!/bin/bash
echo "🔍 Testing swap configuration..."
echo ""

# Check current swap
echo "1. Current swap usage:"
free -h | grep -i swap
echo ""

# Test model loading with swap
echo "2. Testing model load with swap..."
time ollama run mistral "Hello" --verbose 2>&1 | grep -i "swap\|memory\|load"
echo ""

# Monitor during load
echo "3. Monitoring swap during model load..."
ollama run llama3.2 "Test" &
PID=$!
for i in {1..10}; do
    echo -n "Second $i: "
    free -h | grep Swap | awk '{print "Swap used: "$3}'
    sleep 1
done
kill $PID 2>/dev/null