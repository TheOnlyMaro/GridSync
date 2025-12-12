#!/bin/bash

echo "=========================================="
echo "GridSync Phase 2 - Running All Tests"
echo "=========================================="
echo ""

# Function to run a single test
run_test() {
    local test_name=$1
    local netem_cmd=$2
    local results_dir="results/${test_name}"

    echo "Running ${test_name} test..."

    # Create results directory
    mkdir -p ${results_dir}

    # Clean old CSV files
    rm -f client_metrics.csv server_metrics.csv

    # Apply network conditions if specified
    if [ ! -z "$netem_cmd" ]; then
        echo "  Applying network conditions: ${netem_cmd}"
        sudo tc qdisc add dev lo root netem ${netem_cmd}
    fi

    # Start server in background
    python3 server.py > /dev/null 2>&1 &
    SERVER_PID=$!
    echo "  Server started (PID: ${SERVER_PID})"

    # Wait for server to initialize
    sleep 2

    # Start client and run for 60 seconds
    timeout 60 python3 client.py > /dev/null 2>&1 &
    CLIENT_PID=$!
    echo "  Client started (PID: ${CLIENT_PID})"

    # Wait for test to complete
    echo "  Running for 60 seconds..."
    sleep 60

    # Kill processes
    kill ${CLIENT_PID} 2>/dev/null
    kill ${SERVER_PID} 2>/dev/null
    sleep 1
    kill -9 ${CLIENT_PID} 2>/dev/null
    kill -9 ${SERVER_PID} 2>/dev/null

    # Remove network conditions if they were applied
    if [ ! -z "$netem_cmd" ]; then
        sudo tc qdisc del dev lo root 2>/dev/null
    fi

    # Move CSV files to results directory
    if [ -f "client_metrics.csv" ]; then
        mv client_metrics.csv ${results_dir}/
        echo "  ✓ Collected client_metrics.csv ($(wc -l < ${results_dir}/client_metrics.csv) lines)"
    else
        echo "  ✗ WARNING: client_metrics.csv not found!"
    fi

    if [ -f "server_metrics.csv" ]; then
        mv server_metrics.csv ${results_dir}/
        echo "  ✓ Collected server_metrics.csv ($(wc -l < ${results_dir}/server_metrics.csv) lines)"
    else
        echo "  ✗ WARNING: server_metrics.csv not found!"
    fi

    echo "  Test complete! Results in ${results_dir}/"
    echo ""
}

# Run all 4 tests
echo "Test 1/4: Baseline (no network impairment)"
run_test "baseline" ""

echo "Test 2/4: 2% Packet Loss"
run_test "loss_2" "loss 2%"

echo "Test 3/4: 5% Packet Loss"
run_test "loss_5" "loss 5%"

echo "Test 4/4: 100ms Delay"
run_test "delay_100ms" "delay 100ms"

# Generate plots
echo "=========================================="
echo "Generating analysis plots..."
echo "=========================================="
python3 analyze_results.py

echo ""
echo "=========================================="
echo "All tests completed!"
echo "=========================================="
echo ""
echo "Results summary:"
echo "  - results/baseline/"
echo "  - results/loss_2/"
echo "  - results/loss_5/"
echo "  - results/delay_100ms/"
echo "  - results/*.png (analysis plots)"
echo ""