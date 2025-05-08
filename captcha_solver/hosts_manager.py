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
        
        # Determine domain variations to add (with and without www)
        domains_to_add = [domain]
        if domain.startswith('www.'):
            # If domain starts with www, also add the non-www version
            domains_to_add.append(domain[4:])
        elif not domain.startswith('www.'):
            # If domain doesn't start with www, also add the www version
            domains_to_add.append(f"www.{domain}")
        
        # Create a backup
        backup_path = hosts_file.with_suffix(".bak")
        hosts_file.replace(backup_path)
        
        # Add our entries
        new_content = hosts_content
        if new_content and not new_content.endswith("\n"):
            new_content += "\n"
        
        domains_added = []
        for d in domains_to_add:
            entry = f"{ip_address} {d}"
            if entry not in hosts_content:
                new_content += f"{entry}  # Added by captcha_solver\n"
                domains_added.append(d)
            else:
                print(f"Entry '{entry}' already exists in hosts file.")
        
        # Write to temporary file first
        temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w')
        temp_file.write(new_content)
        temp_file.close()
        
        # Copy temp file to hosts file location (safer than direct write)
        os.replace(temp_file.name, HOSTS_FILE_PATH)
        
        if domains_added:
            print(f"Successfully added domains to hosts file: {', '.join(domains_added)}")
        
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
        
        # Determine domain variations to remove (with and without www)
        domains_to_remove = [domain]
        if domain.startswith('www.'):
            # If domain starts with www, also remove the non-www version
            domains_to_remove.append(domain[4:])
        elif not domain.startswith('www.'):
            # If domain doesn't start with www, also remove the www version
            domains_to_remove.append(f"www.{domain}")
        
        # Create a backup
        backup_path = hosts_file.with_suffix(".bak")
        hosts_file.replace(backup_path)
        
        # Process the file line by line to remove entries for all domain variants
        lines = hosts_content.splitlines()
        new_lines = []
        removed_domains = []
        
        for line in lines:
            should_keep = True
            for d in domains_to_remove:
                if f"{ip_address} {d}" in line or line.strip().startswith(f"{ip_address} {d}"):
                    should_keep = False
                    removed_domains.append(d)
                    break
            
            if should_keep:
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
        
        if removed_domains:
            print(f"Successfully removed domains from hosts file: {', '.join(set(removed_domains))}")
        
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

def admin_run_command(command):
    """
    Run a command with elevated (administrator) privileges.
    
    Args:
        command (str): Command to run with admin rights
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not is_admin():
        print(f"Error: Administrator privileges required to run '{command}'")
        return False
        
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            check=True
        )
        print(f"Command executed successfully: {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        print(f"stderr: {e.stderr.decode() if e.stderr else 'None'}")
        return False
    except Exception as e:
        print(f"Unexpected error running command: {e}")
        return False

def setup_port_forwarding(port, target_port=80):
    """
    Set up port forwarding from high port to port 80/443 using netsh interface portproxy.
    This allows a non-admin process to effectively use standard web ports via forwarding.
    
    Args:
        port (int): The high numbered port the app is actually running on
        target_port (int): The port to forward to (80 for HTTP, 443 for HTTPS)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not is_admin():
        print("Error: Administrator privileges required to set up port forwarding")
        return False
        
    try:
        # Delete any existing port forwarding rules for target port
        delete_cmd = f"netsh interface portproxy delete v4tov4 listenport={target_port} listenaddress=0.0.0.0"
        subprocess.run(delete_cmd, shell=True, stderr=subprocess.PIPE)
        
        # Add new port forwarding rule that listens on all interfaces
        add_cmd = f"netsh interface portproxy add v4tov4 listenport={target_port} listenaddress=0.0.0.0 connectport={port} connectaddress=127.0.0.1"
        result = subprocess.run(
            add_cmd, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            check=True
        )
        
        print(f"Successfully set up port forwarding from port {target_port} to {port}")
        
        # Add a firewall rule to allow incoming connections to the target port if it doesn't exist
        protocol = "HTTPS" if target_port == 443 else "HTTP"
        fw_name = f"CaptchaSolver{protocol}Access"
        fw_cmd = f'netsh advfirewall firewall show rule name="{fw_name}" >nul 2>&1 || '
        fw_cmd += f'netsh advfirewall firewall add rule name="{fw_name}" dir=in action=allow protocol=TCP localport={target_port}'
        subprocess.run(fw_cmd, shell=True, stderr=subprocess.PIPE)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error setting up port forwarding: {e}")
        print(f"stderr: {e.stderr.decode() if e.stderr else 'None'}")
        return False
    except Exception as e:
        print(f"Unexpected error setting up port forwarding: {e}")
        return False

def remove_port_forwarding(target_port=80):
    """
    Remove port forwarding rules previously set up.
    
    Args:
        target_port (int): The listening port to remove forwarding for (usually 80)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not is_admin():
        print("Error: Administrator privileges required to remove port forwarding")
        return False
        
    try:
        # Delete the port forwarding rule
        delete_cmd = f"netsh interface portproxy delete v4tov4 listenport={target_port} listenaddress=0.0.0.0"
        result = subprocess.run(
            delete_cmd, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            check=True
        )
        
        print(f"Successfully removed port forwarding for port {target_port}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error removing port forwarding: {e}")
        print(f"stderr: {e.stderr.decode() if e.stderr else 'None'}")
        return False
    except Exception as e:
        print(f"Unexpected error removing port forwarding: {e}")
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