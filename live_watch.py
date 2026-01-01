import socket
import sys
import subprocess
import time
import re

# Configuration
OPENOCD_HOST = "127.0.0.1"
OPENOCD_PORT = 50001
ELF_FILE = r"conan_output/build/lib_stm32"
NM_TOOL = "arm-none-eabi-nm"

def get_var_address(var_name):
    """Uses nm to find the address of a variable in the ELF file."""
    try:
        output = subprocess.check_output([NM_TOOL, ELF_FILE], stderr=subprocess.STDOUT).decode()
        for line in output.splitlines():
            line = line.strip()
            match = re.search(r"([0-9a-fA-F]{8})\s+[a-zA-Z]\s+(\b" + re.escape(var_name) + r"\b)$", line)
            if match:
                return "0x" + match.group(1)
    except Exception as e:
        print(f"Error reading ELF symbols: {e}")
    return None

def read_memory(address, size_cmd="mdh"):
    """Connects to OpenOCD TCL port and reads memory."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect((OPENOCD_HOST, OPENOCD_PORT))
            
            # Try without ocd_ prefix first as it's more standard for newer versions
            cmd = f"capture {{{size_cmd} {address} 1}}\n\x1a"
            s.sendall(cmd.encode())
            
            data = b""
            while True:
                chunk = s.recv(1024)
                if not chunk: break
                data += chunk
                if b"\x1a" in chunk:
                    break
            
            result = data.decode().replace("\x1a", "").strip()
            
            # If we get an "invalid command" error, try with ocd_ prefix
            if "invalid command" in result.lower():
                s.close()
                return read_memory_fallback(address, size_cmd)

            if ":" in result:
                return result.split(":")[1].strip()
            return result
    except Exception as e:
        return f"Error: {e}"

def read_memory_fallback(address, size_cmd):
    """Fallback with ocd_ prefix if needed."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect((OPENOCD_HOST, OPENOCD_PORT))
            cmd = f"capture {{ocd_{size_cmd} {address} 1}}\n\x1a"
            s.sendall(cmd.encode())
            data = b""
            while True:
                chunk = s.recv(1024)
                if not chunk: break
                data += chunk
                if b"\x1a" in chunk: break
            result = data.decode().replace("\x1a", "").strip()
            if ":" in result:
                return result.split(":")[1].strip()
            return result
    except Exception as e:
        return f"Error: {e}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python live_watch.py <variable_name> [interval_ms] [size: w, h, b]")
        sys.exit(1)

    var_name = sys.argv[1]
    interval = float(sys.argv[2]) / 1000.0 if len(sys.argv) > 2 else 0.5
    size_opt = sys.argv[3] if len(sys.argv) > 3 else "h"
    size_cmd = "mdw" if size_opt == "w" else "mdh" if size_opt == "h" else "mdb"

    print(f"Looking for variable '{var_name}' in {ELF_FILE}...")
    addr = get_var_address(var_name)
    
    if not addr:
        print(f"Could not find variable '{var_name}'")
        sys.exit(1)

    print(f"Monitoring '{var_name}' at {addr} (Ctrl+C to stop)")
    print("-" * 40)

    try:
        while True:
            val = read_memory(addr, size_cmd)
            try:
                dec_val = int(val, 16)
                print(f"\r{var_name}: {val} ({dec_val})      ", end="")
            except:
                print(f"\r{var_name}: {val}      ", end="")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
