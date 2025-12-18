#!/bin/bash

# GridSync Phase 3 - Results Validation Script
# Checks that all required test result files exist and have data

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test scenarios
SCENARIOS=("baseline" "loss_2" "loss_5" "delay_100ms")

# Function to print status
print_check() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

# Function to check file exists and has minimum size/lines
check_file() {
    local file=$1
    local min_size=$2
    local min_lines=$3
    local description=$4
    
    if [ ! -f "$file" ]; then
        print_check 1 "$description: File does not exist"
        return 1
    fi
    
    local actual_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "0")
    if [ "$actual_size" -lt "$min_size" ]; then
        print_check 1 "$description: File too small ($actual_size bytes < $min_size bytes)"
        return 1
    fi
    
    if [ -n "$min_lines" ]; then
        local actual_lines=$(wc -l < "$file" 2>/dev/null | tr -d ' ' || echo "0")
        if [ "$actual_lines" -lt "$min_lines" ]; then
            print_check 1 "$description: File has too few lines ($actual_lines < $min_lines)"
            return 1
        fi
    fi
    
    print_check 0 "$description"
    return 0
}

# Validate a single scenario
validate_scenario() {
    local scenario=$1
    local results_dir="results/$scenario"
    local errors=0
    
    echo ""
    echo -e "${BLUE}Validating scenario: $scenario${NC}"
    echo "----------------------------------------"
    
    # Check PCAP file
    check_file "$results_dir/capture.pcap" 1000 "" "  capture.pcap"
    if [ $? -ne 0 ]; then
        ((errors++))
    fi
    
    # Check client metrics CSV
    check_file "$results_dir/client_metrics.csv" 100 10 "  client_metrics.csv"
    if [ $? -ne 0 ]; then
        ((errors++))
    fi
    
    # Check server metrics CSV
    check_file "$results_dir/server_metrics.csv" 100 10 "  server_metrics.csv"
    if [ $? -ne 0 ]; then
        ((errors++))
    fi
    
    # Check client log
    check_file "$results_dir/client.log" 10 "" "  client.log"
    if [ $? -ne 0 ]; then
        ((errors++))
    fi
    
    # Check server log
    check_file "$results_dir/server.log" 10 "" "  server.log"
    if [ $? -ne 0 ]; then
        ((errors++))
    fi
    
    return $errors
}

# Main validation
main() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}GridSync Phase 3 - Results Validation${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    local total_errors=0
    
    # Check if results directory exists
    if [ ! -d "results" ]; then
        echo -e "${RED}✗${NC} results/ directory does not exist"
        echo ""
        echo -e "${RED}MISSING FILES${NC}"
        echo "Run ./run_complete_tests.sh first to generate test results"
        exit 1
    fi
    
    # Validate each scenario
    for scenario in "${SCENARIOS[@]}"; do
        local scenario_errors=0
        validate_scenario "$scenario"
        scenario_errors=$?
        total_errors=$((total_errors + scenario_errors))
    done
    
    # Print summary
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Validation Summary${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    if [ $total_errors -eq 0 ]; then
        echo ""
        echo -e "${GREEN}READY FOR SUBMISSION${NC}"
        echo ""
        echo "All required files are present and contain data:"
        echo "  ✓ 4 PCAP files (packet captures)"
        echo "  ✓ 4 client_metrics.csv files"
        echo "  ✓ 4 server_metrics.csv files"
        echo "  ✓ 4 client.log files"
        echo "  ✓ 4 server.log files"
        echo ""
    else
        echo ""
        echo -e "${RED}MISSING FILES${NC}"
        echo ""
        echo "Found $total_errors file(s) missing or invalid."
        echo "Please run ./run_complete_tests.sh to generate all test results."
        echo ""
        exit 1
    fi
}

# Run main function
main

