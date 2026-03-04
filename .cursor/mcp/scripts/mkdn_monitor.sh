#!/bin/bash

CONTAINER_NAME="markitdown-mcp-server"
CHECK_INTERVAL=30  # seconds
LOG_FILE="$HOME/monitor.log"

# Ensure log file exists
touch "$LOG_FILE"

log_message() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" | tee -a "$LOG_FILE"
}

get_container_status() {
    docker inspect -f '{{.State.Running}}' $CONTAINER_NAME 2>/dev/null
}

get_container_uptime() {
    docker inspect --format='{{.State.StartedAt}}' $CONTAINER_NAME 2>/dev/null
}

get_seconds_since_start() {
    local start_time=$(get_container_uptime)
    if [ -z "$start_time" ]; then
        echo "0"
        return
    fi
    
    local start_epoch=$(date -d "$start_time" +%s 2>/dev/null)
    local now_epoch=$(date +%s)
    local seconds=$((now_epoch - start_epoch))
    
    echo $((seconds > 0 ? seconds : 0))
}

format_uptime() {
    local seconds=$1
    local hours=$((seconds / 3600))
    local minutes=$(((seconds % 3600) / 60))
    printf "%dh %dm" $hours $minutes
}

check_for_errors() {
    docker logs --tail 10 $CONTAINER_NAME 2>&1 | grep -iE "error|fatal|exception" | tail -1
}

log_message "=== MCP Monitor Started ==="

while true; do
    RUNNING=$(get_container_status)
    UPTIME_SECONDS=$(get_seconds_since_start)
    UPTIME_FORMATTED=$(format_uptime $UPTIME_SECONDS)
    
    # Check if container is running
    if [ "$RUNNING" != "true" ]; then
        log_message "✗ Container DOWN - restarting..."
        docker start $CONTAINER_NAME 2>&1 | while read line; do
            log_message "  $line"
        done
        sleep 5
        RUNNING=$(get_container_status)
        UPTIME_SECONDS=$(get_seconds_since_start)
        UPTIME_FORMATTED=$(format_uptime $UPTIME_SECONDS)
    fi
    
    # Check for actual errors in logs
    ERROR_MSG=$(check_for_errors)
    
    # Log heartbeat: simple status + uptime (+ error if found)
    if [ "$RUNNING" = "true" ]; then
        if [ -n "$ERROR_MSG" ]; then
            log_message "⚠️  Container running with errors: $ERROR_MSG | Uptime: $UPTIME_FORMATTED"
        else
            log_message "✓ Container running | Uptime: $UPTIME_FORMATTED"
        fi
    else
        log_message "✗ Container DOWN"
    fi
    
    sleep $CHECK_INTERVAL
done
