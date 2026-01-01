import socket
import sys
import subprocess
import time
import re
import os

# --- Configuration ---
OPENOCD_HOST = "127.0.0.1"
OPENOCD_PORT = 50001
ELF_FILE = r"conan_output/build/lib_stm32"
NM_TOOL = "arm-none-eabi-nm"
WATCH_MD = "LIVE_WATCH.md"
WATCHLIST_FILE = "watchlist.txt"

class MarkdownLiveWatch:
    def __init__(self):
        self.vars = []
        self.last_mtime = 0
        self.use_ocd_prefix = False
        self.last_error = "None"

    def get_symbol_info(self, var_name):
        try:
            if not os.path.exists(ELF_FILE):
                return None, None
            # On Windows, we use shell=True to handle spaces in tool paths if any
            cmd = f'"{NM_TOOL}" "{ELF_FILE}"'
            output = subprocess.check_output(cmd, shell=True).decode()
            for line in output.splitlines():
                match = re.search(r"([0-9a-fA-F]+)\s+[a-zA-Z]\s+(\b" + re.escape(var_name) + r"\b)$", line.strip())
                if match:
                    addr = "0x" + match.group(1)
                    size = "mdw"
                    if var_name.startswith('u8') or var_name.startswith('b'): size = "mdb"
                    if var_name.startswith('u16') or 'ADC' in var_name: size = "mdh"
                    return addr, size
        except Exception as e:
            self.last_error = f"NM Error: {str(e)}"
        return None, None

    def refresh_watchlist(self):
        if not os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
                f.write("u16LiveCounter\nuwTick\nADC_u16Array[10]\n")
        
        try:
            mtime = os.path.getmtime(WATCHLIST_FILE)
            if mtime > self.last_mtime or not self.vars:
                self.last_mtime = mtime
                new_vars = []
                with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                    for raw_line in f:
                        # Be defensive: skip None lines and trim whitespace
                        if raw_line is None:
                            continue
                        line = raw_line.strip()
                        if not line or line.startswith("#"):
                            continue
                        # Match: name or name[count], e.g. ADC_u16Array[10]
                        match = re.match(r'^\s*([^\[\]\s]+)\s*(?:\[(\d+)\])?\s*$', line)
                        if not match:
                            # Skip invalid entries without raising (keeps watcher robust)
                            continue
                        name = match.group(1).strip() if match.group(1) else None
                        if not name:
                            continue
                        try:
                            count = int(match.group(2)) if match.group(2) else 1
                        except Exception:
                            count = 1
                        addr, size = self.get_symbol_info(name)
                        if addr:
                            new_vars.append({"name": name, "display": line, "addr": addr, "size": size, "count": count})
                self.vars = new_vars
        except Exception as e:
            self.last_error = f"Watchlist Refresh Error: {str(e)}"

    def read_memory(self, var):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect((OPENOCD_HOST, OPENOCD_PORT))
                
                prefix = "ocd_" if self.use_ocd_prefix else ""
                # Fixed newline and command termination (\n\x1a)
                cmd = f"capture {{{prefix}{var['size']} {var['addr']} {var['count']}}}\n\x1a"
                s.sendall(cmd.encode())
                
                data = b""
                while True:
                    chunk = s.recv(4096)
                    if not chunk: break
                    data += chunk
                    if b"\x1a" in chunk: break
                
                raw = data.decode(errors='ignore').replace("\x1a", "").strip()
                
                if "invalid command" in raw.lower() and not self.use_ocd_prefix:
                    self.use_ocd_prefix = True
                    return self.read_memory(var)

                vals = []
                for line in raw.splitlines():
                    if ":" in line:
                        parts = line.split(":")[1].strip().split()
                        vals.extend(parts)
                
                if not vals:
                    if raw: self.last_error = f"OpenOCD: {raw}"
                    return ["???"] * var['count']
                
                self.last_error = "None"
                return vals[:var['count']]
        except Exception as e:
            self.last_error = f"Socket Error: {str(e)}"
            return ["???"] * var['count']

    def update_markdown(self):
        md = "# 🔴 STM32 Live Watch\n\n"
        
        if self.last_error != "None":
            md += f"> ⚠️ **Status:** {self.last_error}\n\n"
        else:
            md += f"> ✅ **Status:** Connected and Monitoring {len(self.vars)} items\n\n"

        md += "| Variable | Hex | Decimal |\n"
        md += "| :--- | :--- | :--- |\n"
        
        for v in self.vars:
            vals = self.read_memory(v)
            if v['count'] == 1:
                h = vals[0] if vals else "???"
                try: d = str(int(h, 16))
                except: d = "---"
                md += f"| **{v['name']}** | `{h}` | {d} |\n"
            else:
                md += f"| `{v['display']}` | | |\n"
                for i, h in enumerate(vals):
                    try: d = str(int(h, 16))
                    except: d = "---"
                    md += f"| &nbsp;&nbsp;&nbsp; `[{i}]` | `{h}` | {d} |\n"
        
        md += f"\n\n---\n*Last Update: {time.strftime('%H:%M:%S')}*  \n"
        md += "Edit `watchlist.txt` to change variables."
        
        try:
            with open(WATCH_MD, "w", encoding="utf-8") as f:
                f.write(md)
        except Exception as e:
            print(f"Error writing markdown: {e}")

    def run(self):
        print(f"--- Markdown Watcher Running ---")
        print(f"--- Open {WATCH_MD} and click 'Open Preview to the Side' ---")
        while True:
            self.refresh_watchlist()
            self.update_markdown()
            time.sleep(0.5)

if __name__ == "__main__":
    MarkdownLiveWatch().run()