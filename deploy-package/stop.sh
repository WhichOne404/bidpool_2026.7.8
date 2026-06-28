#!/bin/bash
echo "Stopping services..."
pkill -f "bidpool-go" 2>/dev/null
pkill -f "main.py.*bidpool" 2>/dev/null
echo "Services stopped"
