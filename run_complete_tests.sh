#!/bin/bash

# GridSync Phase 3 - Complete Test Suite
# This script runs all test scenarios with network emulation

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INTERFACE="lo"
TEST_DURATION=60
PORT=9999

# Function to print status messages
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        print_error "This script must be run as root (use sudo)"
        print_error "Root access is needed for tc (traffic control) and tcpdump"
        exit 1
    fi
    print_success "Running as root"
}

# Check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    local missing=0
    
    if ! command -v python3 &> /dev/null; then
        print_error "python3 not found"
        missing=1
    else
        print_success "python3 found: $(python3 --version)"
    fi
    
    if ! command -v tc &> /dev/null; then
        print_error "tc (traffic control) not found"
        print_error "Install with: sudo apt-get install iproute2"
        missing=1
    else
        print_success "tc found"
    fi
    
    if ! command -v tcpdump &> /dev/null; then
        print_error "tcpdump not found"
        print_error "Install with: sudo apt-get install tcpdump"
        missing=1
    else
        print_success "tcpdump found"
    fi
    
    if ! python3 -c "import psutil" &> /dev/null; then
        print_error "psutil Python module not found"
        print_error "Install with: pip3 install psutil"
        missing=1
    else
        print_success "psutil Python module found"
    fi
    
    if [ $missing -eq 1 ]; then
        print_error "Missing dependencies. Please install them before continuing."
        exit 1
    fi
    
    print_success "All dependencies satisfied"
}

# Clean up existing processes
cleanup_processes() {
    print_status "Cleaning up existing processes..."
    
    # Kill any existing server.py or client.py processes
    pkill -f "python3.*server.py" 2>/dev/null || true
    pkill -f "python3.*client.py" 2>/dev/null || true
    pkill -f "tcpdump.*lo" 2>/dev/null || true
    
    # Wait a moment for processes to die
    sleep 1
    
    print_success "Cleanup complete"
}

# Clean up network emulation
cleanup_netem() {
    print_status "Removing network emulation rules..."
    tc qdisc del dev "$INTERFACE" root 2>/dev/null || true
    print_success "Network emulation rules removed"
}

# Function to run a test scenario
run_scenario() {
    local scenario_name=$1
    local netem_cmd=$2
    
    print_status "========================================="
    print_status "Running scenario: $scenario_name"
    print_status "========================================="
    
    # Create results directory
    local results_dir="results/$scenario_name"
    mkdir -p "$results_dir"
    print_success "Created directory: $results_dir"
    
    # Set up network emulation if provided
    if [ -n "$netem_cmd" ]; then
        print_status "Setting up network emulation: $netem_cmd"
        cleanup_netem  # Clean up any existing rules first
        tc qdisc add dev "$INTERFACE" root netem $netem_cmd
        print_success "Network emulation active: $netem_cmd"
    fi
    
    # Start tcpdump in background
    print_status "Starting packet capture..."
    tcpdump -i "$INTERFACE" -w "$results_dir/capture.pcap" -s 0 "udp port $PORT" > /dev/null 2>&1 &
    local tcpdump_pid=$!
    sleep 1
    print_success "tcpdump started (PID: $tcpdump_pid)"
    
    # Start server
    print_status "Starting server..."
    python3 server.py > "$results_dir/server.log" 2>&1 &
    local server_pid=$!
    sleep 3  # Give server time to start
    print_success "Server started (PID: $server_pid)"
    
    # Start client
    print_status "Starting client..."
    python3 client.py > "$results_dir/client.log" 2>&1 &
    local client_pid=$!
    print_success "Client started (PID: $client_pid)"
    
    # Run test for specified duration
    print_status "Test running for ${TEST_DURATION} seconds..."
    sleep $TEST_DURATION
    
    # Stop processes
    print_status "Stopping processes..."
    kill $client_pid 2>/dev/null || true
    sleep 1
    kill $server_pid 2>/dev/null || true
    sleep 1
    kill $tcpdump_pid 2>/dev/null || true
    sleep 1
    
    # Make sure everything is dead
    pkill -f "python3.*server.py" 2>/dev/null || true
    pkill -f "python3.*client.py" 2>/dev/null || true
    pkill -f "tcpdump.*lo" 2>/dev/null || true
    
    print_success "All processes stopped"
    
    # Move CSV files if they exist
    if [ -f "client_metrics.csv" ]; then
        mv "client_metrics.csv" "$results_dir/client_metrics.csv"
        print_success "Moved client_metrics.csv to $results_dir/"
    else
        print_warning "client_metrics.csv not found"
    fi
    
    if [ -f "server_metrics.csv" ]; then
        mv "server_metrics.csv" "$results_dir/server_metrics.csv"
        print_success "Moved server_metrics.csv to $results_dir/"
    else
        print_warning "server_metrics.csv not found"
    fi
    
    # Print CSV line counts
    if [ -f "$results_dir/client_metrics.csv" ]; then
        local client_lines=$(wc -l < "$results_dir/client_metrics.csv" | tr -d ' ')
        print_status "client_metrics.csv has $client_lines lines"
    fi
    
    if [ -f "$results_dir/server_metrics.csv" ]; then
        local server_lines=$(wc -l < "$results_dir/server_metrics.csv" | tr -d ' ')
        print_status "server_metrics.csv has $server_lines lines"
    fi
    
    # Check PCAP file size
    if [ -f "$results_dir/capture.pcap" ]; then
        local pcap_size=$(stat -f%z "$results_dir/capture.pcap" 2>/dev/null || stat -c%s "$results_dir/capture.pcap" 2>/dev/null || echo "0")
        print_status "capture.pcap size: $pcap_size bytes"
    fi
    
    # Clean up network emulation
    if [ -n "$netem_cmd" ]; then
        cleanup_netem
    fi
    
    print_success "Scenario $scenario_name completed"
    echo ""
}

# Main execution
main() {
    echo ""
    print_status "========================================="
    print_status "GridSync Phase 3 - Complete Test Suite"
    print_status "========================================="
    echo ""
    
    # Pre-flight checks
    check_root
    check_dependencies
    
    print_status "Network interface: $INTERFACE"
    print_status "Test duration per scenario: ${TEST_DURATION} seconds"
    echo ""
    
    # Clean up before starting
    cleanup_processes
    cleanup_netem
    
    # Run all scenarios
    run_scenario "baseline" ""
    run_scenario "loss_2" "loss 2%"
    run_scenario "loss_5" "loss 5%"
    run_scenario "delay_100ms" "delay 100ms"
    
    # Final cleanup
    cleanup_netem
    cleanup_processes
    
    # Run analysis if script exists
    if [ -f "analyze_results.py" ]; then
        print_status "========================================="
        print_status "Running analysis..."
        print_status "========================================="
        python3 analyze_results.py
        print_success "Analysis complete"
    else
        print_warning "analyze_results.py not found, skipping analysis"
    fi
    
    # Print summary
    echo ""
    print_status "========================================="
    print_status "Test Suite Complete - Summary"
    print_status "========================================="
    
    echo ""
    print_status "Results directory structure:"
    if [ -d "results" ]; then
        find results -type f -name "*.pcap" -o -name "*.csv" -o -name "*.log" | sort | while read file; do
            local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "?")
            echo "  $file ($size bytes)"
        done
    fi
    
    echo ""
    print_success "All tests completed successfully!"
    print_status "Run ./validate_results.sh to verify all files are present"
    echo ""
}

# Run main function
main

