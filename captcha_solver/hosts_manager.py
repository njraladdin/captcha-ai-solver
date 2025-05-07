"""
Hosts file manager for captcha_solver package.

This module provides functions to add and remove entries to the Windows hosts file
to temporarily redirect domains to 127.0.0.1, which helps bypass domain restrictions
in reCAPTCHA challenges.
"""

import os
import sys
import ctypes
import tempfile
import subprocess
from pathlib import Path


# Windows hosts file path
HOSTS_FILE_PATH = r"C:\Windows\System32\drivers\etc\hosts"

def is_admin():
    """
    Check if the script is running with administrator privileges.
    
    Returns:
        bool: True if running as administrator, False otherwise
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def restart_with_admin():
    """
    Restart the current script with administrator privileges.
    """
    if not is_admin():
        print("Requesting administrator privileges...")
        # Re-run the script with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)

def add_to_hosts(domain, ip_address="127.0.0.1"):
    """
    Add a domain entry to the hosts file.
    
    Args:
        domain (str): The domain name to add
        ip_address (str, optional): The IP address to map the domain to. 
                                    Defaults to "127.0.0.1".
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not is_admin():
        print("Error: Administrator privileges required to modify hosts file.")
        return False
    
    try:
        hosts_file = Path(HOSTS_FILE_PATH)
        hosts_content = hosts_file.read_text()
        
        # Check if entry already exists
        entry = f"{ip_address} {domain}"
        if entry in hosts_content:
            print(f"Entry '{entry}' already exists in hosts file.")
            return True
        
        # Create a backup
        backup_path = hosts_file.with_suffix(".bak")
        hosts_file.replace(backup_path)
        
        # Add our entry
        new_content = hosts_content
        if new_content and not new_content.endswith("\n"):
            new_content += "\n"
        new_content += f"{entry}  # Added by captcha_solver\n"
        
        # Write to temporary file first
        temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w')
        temp_file.write(new_content)
        temp_file.close()
        
        # Copy temp file to hosts file location (safer than direct write)
        os.replace(temp_file.name, HOSTS_FILE_PATH)
        
        print(f"Successfully added '{entry}' to hosts file.")
        
        # Flush DNS cache to apply changes immediately
        flush_dns_cache()
        
        return True
    
    except Exception as e:
        print(f"Error adding entry to hosts file: {e}")
        return False

def remove_from_hosts(domain, ip_address="127.0.0.1"):
    """
    Remove a domain entry from the hosts file.
    
    Args:
        domain (str): The domain name to remove
        ip_address (str, optional): The IP address mapped to the domain.
                                    Defaults to "127.0.0.1".
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not is_admin():
        print("Error: Administrator privileges required to modify hosts file.")
        return False
    
    try:
        hosts_file = Path(HOSTS_FILE_PATH)
        hosts_content = hosts_file.read_text()
        
        # Check if entry exists
        entry = f"{ip_address} {domain}"
        comment_entry = f"{entry}  # Added by captcha_solver"
        
        if entry not in hosts_content and comment_entry not in hosts_content:
            print(f"Entry for '{domain}' not found in hosts file.")
            return True
        
        # Create a backup
        backup_path = hosts_file.with_suffix(".bak")
        hosts_file.replace(backup_path)
        
        # Remove the entry and its variations
        lines = hosts_content.splitlines()
        new_lines = []
        for line in lines:
            if (f"{ip_address} {domain}" not in line and 
                not (line.strip().startswith(f"{ip_address} {domain}"))):
                new_lines.append(line)
        
        new_content = "\n".join(new_lines)
        if new_content and not new_content.endswith("\n"):
            new_content += "\n"
        
        # Write to temporary file first
        temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w')
        temp_file.write(new_content)
        temp_file.close()
        
        # Copy temp file to hosts file location (safer than direct write)
        os.replace(temp_file.name, HOSTS_FILE_PATH)
        
        print(f"Successfully removed '{domain}' from hosts file.")
        
        # Flush DNS cache to apply changes immediately
        flush_dns_cache()
        
        return True
    
    except Exception as e:
        print(f"Error removing entry from hosts file: {e}")
        return False

def flush_dns_cache():
    """
    Flush the DNS cache to apply hosts file changes immediately.
    """
    try:
        subprocess.run(["ipconfig", "/flushdns"], 
                       stdout=subprocess.PIPE, 
                       stderr=subprocess.PIPE, 
                       check=True)
        print("DNS cache flushed successfully.")
    except subprocess.CalledProcessError:
        print("Failed to flush DNS cache.")
    except Exception as e:
        print(f"Error flushing DNS cache: {e}")

def check_domain_in_hosts(domain, ip_address="127.0.0.1"):
    """
    Check if a domain entry exists in the hosts file.
    
    Args:
        domain (str): The domain name to check
        ip_address (str, optional): The IP address mapped to the domain.
                                    Defaults to "127.0.0.1".
    
    Returns:
        bool: True if entry exists, False otherwise
    """
    try:
        hosts_file = Path(HOSTS_FILE_PATH)
        hosts_content = hosts_file.read_text()
        
        entry = f"{ip_address} {domain}"
        for line in hosts_content.splitlines():
            if line.strip().startswith(entry):
                return True
        
        return False
    
    except Exception as e:
        print(f"Error checking hosts file: {e}")
        return False


if __name__ == "__main__":
    # Test the hosts file manager
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage Windows hosts file entries")
    parser.add_argument("action", choices=["add", "remove", "check"], 
                        help="Action to perform on hosts file")
    parser.add_argument("domain", help="Domain name to manipulate")
    parser.add_argument("--ip", default="127.0.0.1", help="IP address (default: 127.0.0.1)")
    
    # Check for admin rights first
    if len(sys.argv) > 1 and not is_admin() and sys.argv[1] in ["add", "remove"]:
        print("This operation requires administrator privileges.")
        restart_with_admin()
    
    args = parser.parse_args()
    
    if args.action == "add":
        add_to_hosts(args.domain, args.ip)
    elif args.action == "remove":
        remove_from_hosts(args.domain, args.ip)
    elif args.action == "check":
        exists = check_domain_in_hosts(args.domain, args.ip)
        status = "exists" if exists else "does not exist"
        print(f"Entry for '{args.domain}' {status} in hosts file.") 