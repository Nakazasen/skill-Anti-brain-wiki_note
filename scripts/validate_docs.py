import os
import re
import sys

# Commands that are intentional or aliases and don't have a direct 1:1 file match
COMMAND_ALLOWLIST = {
    'help',         # Back-reference to help.md itself
    'save-brain',   # Alias for save_brain.md
}

# Suspicious tokens common in shift-jis/latin-1 vs utf-8 mojibake
SUSPICIOUS_TOKENS = ['ﾃ', 'ﾄ', 'ﾆ', '蘯', '盻', '碼', '駟', '駢']

def check_content(filepath):
    """Check if a file is valid UTF-8 and contains no likely mojibake."""
    errors = []
    try:
        with open(filepath, 'rb') as f:
            raw_data = f.read()
            content = raw_data.decode('utf-8')
            
            # Check for suspicious tokens
            for token in SUSPICIOUS_TOKENS:
                if token in content:
                    errors.append(f"Suspicious token found (likely mojibake): {token}")
                    break
                    
    except UnicodeDecodeError as e:
        errors.append(f"UnicodeDecodeError: {str(e)}")
    
    return errors, content if not errors else ""

def extract_commands(content):
    """Extract slash commands like /abw-init from markdown content.
    Uses negative lookbehind to avoid matching paths (e.g., .brain/lessons)
    or combined terms (e.g., UI/UX).
    """
    # Match /command only if NOT preceded by a-z, A-Z, 0-9, or .
    matches = re.findall(r'(?<![a-zA-Z0-9.])/(?P<cmd>[a-zA-Z0-9_-]+)', content)
    return set(matches)

def main():
    workflows_dir = 'workflows'
    help_file = os.path.join(workflows_dir, 'help.md')
    readme_file = os.path.join(workflows_dir, 'README.md')
    
    overall_success = True
    
    # 1. Check encoding and suspicious tokens
    files_to_check = [help_file, readme_file, 'README.md', 'README.en.md']
    for f_path in files_to_check:
        if not os.path.exists(f_path):
            print(f"Warning: {f_path} not found.")
            continue
        errs, _ = check_content(f_path)
        if errs:
            print(f"ERROR: {f_path} failed checks:")
            for e in errs:
                print(f"  - {e}")
            overall_success = False
        else:
            print(f"OK: {f_path} passed encoding and mojibake checks.")

    # 2. Extract expected commands from filenames
    expected_from_files = set()
    for f in os.listdir(workflows_dir):
        if f.endswith('.md') and f != 'README.md':
            cmd_name = f.replace('.md', '').replace('_', '-')
            expected_from_files.add(cmd_name)
    
    # 3. Validate help.md drift
    errs, help_content = check_content(help_file)
    if not errs:
        documented_cmds = extract_commands(help_content)
        
        # Missing in help
        missing = expected_from_files - (documented_cmds | COMMAND_ALLOWLIST)
        if missing:
            print(f"ERROR: Commands in workflows/ but missing in help.md: {missing}")
            overall_success = False
            
        # Extra/Stale in help
        extra = documented_cmds - (expected_from_files | COMMAND_ALLOWLIST)
        # Filter out common markdown links or false positives if needed
        # (Current regex is fairly specific to /command)
        if extra:
            print(f"ERROR: Stale or extra commands in help.md (not found in workflows/): {extra}")
            overall_success = False
            
        if not missing and not extra:
            print("OK: help.md is perfectly synchronized with workflows/.")
    else:
        overall_success = False

    # 4. Validate workflows/README.md drift
    errs, readme_content = check_content(readme_file)
    if not errs:
        documented_cmds = extract_commands(readme_content)
        missing = expected_from_files - (documented_cmds | COMMAND_ALLOWLIST)
        extra = documented_cmds - (expected_from_files | COMMAND_ALLOWLIST)
        
        if missing:
            print(f"ERROR: Commands in workflows/ but missing in workflows/README.md: {missing}")
            overall_success = False
        if extra:
            print(f"ERROR: Stale or extra commands in workflows/README.md: {extra}")
            overall_success = False
            
        if not missing and not extra:
            print("OK: workflows/README.md is perfectly synchronized with workflows/.")
    else:
        overall_success = False

    # 5. Final Verdict
    print(f"\nTotal command files found: {len(expected_from_files)}")
    
    if overall_success:
        print("\nVERDICT: PASS")
        sys.exit(0)
    else:
        print("\nVERDICT: FAIL")
        sys.exit(1)

if __name__ == '__main__':
    main()
