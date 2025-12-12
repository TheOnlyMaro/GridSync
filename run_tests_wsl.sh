#!/bin/bash

echo "=========================================="
echo "GridSync Phase 2 - WSL2 Compatible Tests"
echo "=========================================="
echo ""
echo "NOTE: Running in WSL2 - network emulation disabled"
echo "For full network testing, use native Linux or VM"
echo ""

# Function to run a single test
run_test() {
    local test_name=$1
    local results_dir="results/${test_name}"
    local test_duration=60

    echo "Running ${test_name} test..."

    # Create results directory
    mkdir -p ${results_dir}

    # Clean old CSV files
    rm -f client_metrics.csv server_metrics.csv

    # Start server in background
    echo "  Starting server..."
    python3 server.py > ${results_dir}/server.log 2>&1 &
    SERVER_PID=$!
    echo "  Server started (PID: ${SERVER_PID})"

    # Wait for server to initialize
    sleep 3

    # Start client and run for specified duration
    echo "  Starting client..."
    python3 client.py > ${results_dir}/client.log 2>&1 &
    CLIENT_PID=$!
    echo "  Client started (PID: ${CLIENT_PID})"

    # Wait for test to complete
    echo "  Running for ${test_duration} seconds..."
    sleep ${test_duration}

    # Give time for CSV files to be written
    sleep 2

    # Kill processes gracefully first
    echo "  Stopping client and server..."
    kill ${CLIENT_PID} 2>/dev/null
    kill ${SERVER_PID} 2>/dev/null
    sleep 2

    # Force kill if still running
    kill -9 ${CLIENT_PID} 2>/dev/null
    kill -9 ${SERVER_PID} 2>/dev/null
    sleep 1

    # Move CSV files to results directory
    if [ -f "client_metrics.csv" ]; then
        mv client_metrics.csv ${results_dir}/
        echo "  ✓ Collected client_metrics.csv ($(wc -l < ${results_dir}/client_metrics.csv) lines)"
    else
        echo "  ✗ WARNING: client_metrics.csv not found!"
        echo "  Check ${results_dir}/client.log for errors"
    fi

    if [ -f "server_metrics.csv" ]; then
        mv server_metrics.csv ${results_dir}/
        echo "  ✓ Collected server_metrics.csv ($(wc -l < ${results_dir}/server_metrics.csv) lines)"
    else
        echo "  ✗ WARNING: server_metrics.csv not found!"
        echo "  Check ${results_dir}/server.log for errors"
    fi

    echo "  Test complete! Results in ${results_dir}/"
    echo ""
}

# Check if required dependencies are installed
check_dependencies() {
    echo "Checking dependencies..."

    if ! command -v python3 &> /dev/null; then
        echo "✗ Error: python3 not found. Please install Python 3."
        exit 1
    fi

    if ! python3 -c "import psutil" 2>/dev/null; then
        echo "✗ Error: psutil module not found."
        echo "  Install with: pip3 install psutil"
        exit 1
    fi

    if ! python3 -c "import matplotlib" 2>/dev/null; then
        echo "⚠ Warning: matplotlib not found (needed for plots)."
        echo "  Install with: pip3 install matplotlib pandas"
    fi

    echo "✓ Dependencies OK"
    echo ""
}

# Run dependency check
check_dependencies

# Kill any existing instances
echo "Cleaning up any existing server/client processes..."
pkill -f "python3 server.py" 2>/dev/null
pkill -f "python3 client.py" 2>/dev/null
sleep 1

# Run baseline test only (since we can't emulate network conditions in WSL2)
echo "Test 1/1: Baseline (no network impairment)"
run_test "baseline"

echo ""
echo "=========================================="
echo "NOTE: Network impairment tests skipped"
echo "=========================================="
echo ""
echo "WSL2 does not support tc/netem network emulation."
echo "To run full tests with packet loss and delay:"
echo "  1. Use a native Linux system or VM"
echo "  2. Or use the Windows PowerShell script with Clumsy"
echo ""

# Generate plots if matplotlib is available
if python3 -c "import matplotlib" 2>/dev/null; then
    echo "=========================================="
    echo "Generating analysis plots..."
    echo "=========================================="
    if [ -f "analyze_results.py" ]; then
        python3 analyze_results.py
    else
        echo "✗ analyze_results.py not found"
    fi
else
    echo "Skipping plot generation (matplotlib not installed)"
fi

echo ""
echo "=========================================="
echo "Test completed!"
echo "=========================================="
echo ""
echo "Results:"
echo "  - results/baseline/"
echo "  - results/baseline/client_metrics.csv"
echo "  - results/baseline/server_metrics.csv"
echo ""
echo "Next steps for Phase 2:"
echo "  1. Verify CSV files contain data"
echo "  2. Install matplotlib: pip3 install matplotlib pandas"
echo "  3. Run analyze_results.py to generate plots"
echo "  4. For network impairment tests, use native Linux"
echo ""