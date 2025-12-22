#!/bin/bash

# GridSync Phase 3 - Quick Test Script
# 10-second test to verify client/server work and CSV logging

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Clean up function
cleanup() {
    print_status "Cleaning up processes..."
    pkill -f "python3.*server.py" 2>/dev/null || true
    pkill -f "python3.*client.py" 2>/dev/null || true
    sleep 1
    print_success "Cleanup complete"
}

# Main test
main() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}GridSync Quick Test (10 seconds)${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    # Clean up any existing processes
    cleanup
    
    # Check if server.py and client.py exist
    if [ ! -f "server.py" ]; then
        print_error "server.py not found"
        exit 1
    fi
    
    if [ ! -f "client.py" ]; then
        print_error "client.py not found"
        exit 1
    fi
    
    # Remove old CSV files if they exist
    if [ -f "client_metrics.csv" ]; then
        rm -f "client_metrics.csv"
        print_status "Removed old client_metrics.csv"
    fi
    
    if [ -f "server_metrics.csv" ]; then
        rm -f "server_metrics.csv"
        print_status "Removed old server_metrics.csv"
    fi
    
    # Start server in background
    print_status "Starting server..."
    python3 server.py > /dev/null 2>&1 &
    local server_pid=$!
    sleep 2  # Give server time to start
    print_success "Server started (PID: $server_pid)"
    
    # Start client in background
    print_status "Starting client..."
    python3 client.py > /dev/null 2>&1 &
    local client_pid=$!
    print_success "Client started (PID: $client_pid)"
    
    # Run for 10 seconds
    print_status "Test running for 10 seconds..."
    sleep 10
    
    # Stop processes
    cleanup
    
    # Check if CSV files were created
    echo ""
    print_status "Checking results..."
    
    local csv_works=1
    
    if [ -f "client_metrics.csv" ]; then
        print_success "client_metrics.csv created"
        local client_lines=$(wc -l < "client_metrics.csv" | tr -d ' ')
        print_status "  Lines: $client_lines"
        
        if [ "$client_lines" -gt 0 ]; then
            echo ""
            echo "First 3 lines of client_metrics.csv:"
            head -n 3 "client_metrics.csv" | sed 's/^/  /'
            echo ""
        else
            print_error "client_metrics.csv is empty"
            csv_works=0
        fi
    else
        print_error "client_metrics.csv not created"
        csv_works=0
    fi
    
    if [ -f "server_metrics.csv" ]; then
        print_success "server_metrics.csv created"
        local server_lines=$(wc -l < "server_metrics.csv" | tr -d ' ')
        print_status "  Lines: $server_lines"
        
        if [ "$server_lines" -gt 0 ]; then
            echo ""
            echo "First 3 lines of server_metrics.csv:"
            head -n 3 "server_metrics.csv" | sed 's/^/  /'
            echo ""
        else
            print_error "server_metrics.csv is empty"
            csv_works=0
        fi
    else
        print_error "server_metrics.csv not created"
        csv_works=0
    fi
    
    # Final verdict
    echo -e "${BLUE}========================================${NC}"
    if [ $csv_works -eq 1 ]; then
        print_success "CSV logging works!"
        echo ""
        print_status "Client and server are functioning correctly."
        print_status "Ready to run full test suite: sudo ./run_complete_tests.sh"
    else
        print_error "CSV logging broken!"
        echo ""
        print_error "CSV files were not created or are empty."
        print_error "Please check server.py and client.py for issues."
    fi
    echo ""
}

# Run main function
main

