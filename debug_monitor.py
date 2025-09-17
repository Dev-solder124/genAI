#!/usr/bin/env python3
"""
Real-time log monitoring script for genai-chatbot
Run this in a separate terminal to monitor logs while testing
"""

import os
import time
import sys
from pathlib import Path

def tail_file(filepath, lines=50):
    """Tail a file and yield new lines"""
    if not os.path.exists(filepath):
        print(f"   Log file not found: {filepath}")
        print("  Waiting for log file to be created...")
        while not os.path.exists(filepath):
            time.sleep(1)
        print(f"  Log file created: {filepath}")
    
    # Read existing lines first
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        existing_lines = f.readlines()
        if existing_lines:
            print(" Recent log entries:")
            print("-" * 80)
            for line in existing_lines[-lines:]:
                print(line.rstrip())
            print("-" * 80)
    
    # Monitor for new lines
    print(" Monitoring for new log entries... (Press Ctrl+C to stop)")
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        # Go to end of file
        f.seek(0, 2)
        
        while True:
            try:
                line = f.readline()
                if line:
                    # Color-code log levels
                    line_stripped = line.rstrip()
                    if 'ERROR' in line_stripped:
                        print(f"  {line_stripped}")
                    elif 'WARNING' in line_stripped:
                        print(f"  {line_stripped}")
                    elif 'INFO' in line_stripped:
                        print(f"  {line_stripped}")
                    elif 'DEBUG' in line_stripped:
                        print(f"  {line_stripped}")
                    else:
                        print(line_stripped)
                else:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n  Stopping log monitor...")
                break
            except Exception as e:
                print(f"  Error reading log: {e}")
                time.sleep(1)

def monitor_chatbot_logs():
    """Monitor the main chatbot log file"""
    log_file = "chatbot.log"
    
    print("  Genai-Chatbot Debug Monitor")
    print("=" * 50)
    print(f"  Monitoring: {os.path.abspath(log_file)}")
    print("  Color coding:")
    print("     ERROR     WARNING     INFO     DEBUG")
    print("=" * 50)
    
    try:
        tail_file(log_file)
    except Exception as e:
        print(f"  Failed to monitor logs: {e}")
        sys.exit(1)

def show_log_analysis():
    """Analyze the log file for common issues"""
    log_file = "chatbot.log"
    
    if not os.path.exists(log_file):
        print("  No log file found yet. Run the main.py server first.")
        return
    
    print("  Log File Analysis")
    print("=" * 50)
    
    error_count = 0
    warning_count = 0
    info_count = 0
    debug_count = 0
    
    errors = []
    warnings = []
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                if 'ERROR' in line:
                    error_count += 1
                    errors.append(f"Line {line_num}: {line.strip()}")
                elif 'WARNING' in line:
                    warning_count += 1
                    warnings.append(f"Line {line_num}: {line.strip()}")
                elif 'INFO' in line:
                    info_count += 1
                elif 'DEBUG' in line:
                    debug_count += 1
        
        print(f"  Log Statistics:")
        print(f"     Errors: {error_count}")
        print(f"     Warnings: {warning_count}")
        print(f"     Info: {info_count}")
        print(f"     Debug: {debug_count}")
        
        if errors:
            print(f"\n  Recent Errors ({min(5, len(errors))} of {len(errors)}):")
            for error in errors[-5:]:
                print(f"   {error}")
        
        if warnings:
            print(f"\n  Recent Warnings ({min(3, len(warnings))} of {len(warnings)}):")
            for warning in warnings[-3:]:
                print(f"   {warning}")
        
        if error_count == 0 and warning_count == 0:
            print("\n  No errors or warnings found!")
        
    except Exception as e:
        print(f"  Error analyzing log file: {e}")

def clear_logs():
    """Clear the log file"""
    log_file = "chatbot.log"
    
    try:
        if os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write("")
            print(f"  Cleared log file: {log_file}")
        else:
            print(f"  No log file to clear: {log_file}")
    except Exception as e:
        print(f"  Error clearing log file: {e}")

def main():
    """Main function with command options"""
    if len(sys.argv) < 2:
        print("  Genai-Chatbot Debug Monitor")
        print("\nUsage:")
        print("  python debug_monitor.py monitor    # Monitor logs in real-time")
        print("  python debug_monitor.py analyze    # Analyze existing logs")
        print("  python debug_monitor.py clear      # Clear log file")
        print("\nMake sure to run main.py first to generate logs!")
        return
    
    command = sys.argv[1].lower()
    
    if command == "monitor":
        monitor_chatbot_logs()
    elif command == "analyze":
        show_log_analysis()
    elif command == "clear":
        clear_logs()
    else:
        print(f"  Unknown command: {command}")
        print("Valid commands: monitor, analyze, clear")

if __name__ == "__main__":
    main()