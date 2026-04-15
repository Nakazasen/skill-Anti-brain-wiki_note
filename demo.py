import os
import subprocess
import json
import time

# ANSI colors for terminal
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(text):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}{text.center(60)}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}\n")

def run_demo():
    clear()
    print_header("Hybrid ABW: Action Governance Demo")
    
    print(f"{BOLD}Scenario:{RESET} Resuming a project with a pending security change.")
    print(f"Workspace: {YELLOW}examples/resume-abw{RESET}\n")
    time.sleep(1)

    # --- PART 1: THE WILD AGENT ---
    print(f"{BOLD}[1/2] THE WILD AGENT (Ungoverned Control){RESET}")
    print(f"{RED}Targeting: step-auth-change (Unsafe Zone){RESET}")
    print(f"{RED}Status: EXECUTION STARTING...{RESET}")
    time.sleep(1.5)
    print(f"{BOLD}{RED}CRITICAL FAILURE:{RESET} Wild Agent overrode protected Auth logic blindly.")
    print(f"{RED}Result: Invisible Security Regression. Task Failed Silently.{RESET}\n")
    
    time.sleep(2)
    print("-" * 60)
    
    # --- PART 2: THE GOVERNED AGENT ---
    print(f"\n{BOLD}[2/2] THE GOVERNED AGENT (ABW Runtime Control){RESET}")
    print(f"{YELLOW}Invoking ABW Continuation Gate...{RESET}\n")
    time.sleep(1)
    
    try:
        # Run the real gate script
        result = subprocess.check_output(
            ["py", "scripts/continuation_gate.py", "--workspace", "examples/resume-abw"],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        gate_data = json.loads(result)
        
        # Display the Blocked Unsafe Zone
        skipped = gate_data.get("skipped", [])
        for item in skipped:
            print(f"{BOLD}{GREEN}GOVERNANCE ALERT:{RESET} Blocked unsafe step: {YELLOW}{item['step_id']}{RESET}")
            print(f"Reason: {item['reason']}")
            
        print(f"\n{BOLD}{GREEN}SAFE SELECTION:{RESET} Selected gated step: {YELLOW}{gate_data['selected']['step_id']}{RESET}")
        print(f"Safety Score: {BOLD}{GREEN}{gate_data['selected']['safety_score']}{RESET}\n")
        
        time.sleep(1.5)
        print(f"{BOLD}{GREEN}RESULT: SYSTEM HARDENED.{RESET}")
        print(f"{GREEN}The agent is forced into correction. No invisible failure occurred.{RESET}")

    except Exception as e:
        print(f"{RED}Error running gate: {e}{RESET}")

    print_header("DEMO COMPLETE")
    print(f"{BOLD}Tagline:{RESET} Without governance, failure is invisible.")
    print(f"With ABW, failure is blocked, logged, and forced into correction.\n")

if __name__ == "__main__":
    run_demo()
