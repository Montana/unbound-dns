#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import os
import platform
import re
from pathlib import Path

class UnboundInstallerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Unbound DNS Installer")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        self.is_installing = False
        self.os_type = self.detect_os()
        
        self.setup_styles()
        self.create_widgets()
        self.check_status()
    
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        bg_color = '#f0f0f0'
        accent_color = '#0066cc'
        success_color = '#28a745'
        error_color = '#dc3545'
        
        style.configure('Title.TLabel', font=('Helvetica', 16, 'bold'), foreground=accent_color)
        style.configure('Subtitle.TLabel', font=('Helvetica', 10), foreground='#666666')
        style.configure('Status.TLabel', font=('Helvetica', 10, 'bold'))
        style.configure('Success.TLabel', foreground=success_color)
        style.configure('Error.TLabel', foreground=error_color)
        style.configure('Primary.TButton', font=('Helvetica', 10, 'bold'))
        
    def detect_os(self):
        system = platform.system()
        if system == "Darwin":
            return "macos"
        elif system == "Linux":
            return "linux"
        else:
            return "unknown"
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        title_label = ttk.Label(header_frame, text="Unbound DNS Installer", style='Title.TLabel')
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        subtitle_label = ttk.Label(header_frame, 
                                   text="Resilient DNS with Automatic Failover & DoT Support",
                                   style='Subtitle.TLabel')
        subtitle_label.grid(row=1, column=0, sticky=tk.W)
        
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)
        
        ttk.Label(status_frame, text="Operating System:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.os_label = ttk.Label(status_frame, text=self.os_type.upper())
        self.os_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(status_frame, text="Unbound Status:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.status_label = ttk.Label(status_frame, text="Checking...", style='Status.TLabel')
        self.status_label.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(status_frame, text="Port 53:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.port_label = ttk.Label(status_frame, text="Checking...")
        self.port_label.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="10")
        output_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=15, wrap=tk.WORD,
                                                     font=('Courier', 9), bg='#1e1e1e', fg='#d4d4d4')
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        button_frame.columnconfigure(3, weight=1)
        
        self.install_btn = ttk.Button(button_frame, text="Install", 
                                      command=self.install_unbound, style='Primary.TButton')
        self.install_btn.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        self.start_btn = ttk.Button(button_frame, text="Start", 
                                    command=self.start_unbound, state='disabled')
        self.start_btn.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        self.stop_btn = ttk.Button(button_frame, text="Stop", 
                                   command=self.stop_unbound, state='disabled')
        self.stop_btn.grid(row=0, column=2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        self.test_btn = ttk.Button(button_frame, text="Test DNS", 
                                   command=self.test_dns)
        self.test_btn.grid(row=0, column=3, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        self.log("GUI initialized. Ready to install Unbound DNS.")
    
    def log(self, message, color=None):
        self.output_text.insert(tk.END, message + "\n")
        if color:
            start_idx = self.output_text.index(f"end-{len(message)+1}c")
            end_idx = self.output_text.index("end-1c")
            tag_name = f"color_{color}"
            self.output_text.tag_config(tag_name, foreground=color)
            self.output_text.tag_add(tag_name, start_idx, end_idx)
        self.output_text.see(tk.END)
        self.root.update()
    
    def run_command(self, command, shell=True):
        try:
            self.log(f"$ {command if isinstance(command, str) else ' '.join(command)}", "#888888")
            result = subprocess.run(command, shell=shell, capture_output=True, text=True, timeout=120)
            
            if result.stdout:
                self.log(result.stdout.strip())
            if result.returncode != 0 and result.stderr:
                self.log(result.stderr.strip(), "#ff6b6b")
            
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            self.log("Command timed out", "#ff6b6b")
            return False
        except Exception as e:
            self.log(f"Error: {str(e)}", "#ff6b6b")
            return False
    
    def check_status(self):
        def check():
            if self.os_type == "macos":
                result = subprocess.run(['pgrep', '-x', 'unbound'], capture_output=True)
                is_running = result.returncode == 0
            else:
                result = subprocess.run(['systemctl', 'is-active', 'unbound'], 
                                      capture_output=True, text=True)
                is_running = result.stdout.strip() == 'active'
            
            port_check = subprocess.run(['sudo', 'lsof', '-i', ':53', '-sTCP:LISTEN'], 
                                       capture_output=True)
            port_in_use = port_check.returncode == 0
            
            self.root.after(0, self.update_status, is_running, port_in_use)
        
        threading.Thread(target=check, daemon=True).start()
    
    def update_status(self, is_running, port_in_use):
        if is_running:
            self.status_label.config(text="Running", style='Success.TLabel')
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
        else:
            self.status_label.config(text="Not Running", style='Error.TLabel')
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
        
        if port_in_use:
            self.port_label.config(text="In Use", foreground='#ffa500')
        else:
            self.port_label.config(text="Available", foreground='#28a745')
    
    def install_unbound(self):
        if self.is_installing:
            messagebox.showwarning("Busy", "Installation is already in progress")
            return
        
        response = messagebox.askyesno("Confirm Installation", 
                                       "This will install Unbound DNS and modify system DNS settings.\n\n"
                                       "The script requires sudo privileges.\n\n"
                                       "Continue?")
        if not response:
            return
        
        self.is_installing = True
        self.install_btn.config(state='disabled')
        self.output_text.delete(1.0, tk.END)
        
        def install():
            self.log("=" * 60, "#0066cc")
            self.log("Starting Unbound DNS Installation", "#0066cc")
            self.log("=" * 60, "#0066cc")
            
            script_path = Path(__file__).parent / "unbound_install.sh"
            
            if not script_path.exists():
                self.log("Error: unbound_install.sh not found!", "#ff6b6b")
                self.log("Please ensure the bash script is in the same directory.", "#ff6b6b")
                self.root.after(0, self.installation_complete, False)
                return
            
            success = self.run_command(f"sudo bash {script_path}")
            
            if success:
                self.log("=" * 60, "#28a745")
                self.log("Installation completed successfully!", "#28a745")
                self.log("=" * 60, "#28a745")
            else:
                self.log("=" * 60, "#ff6b6b")
                self.log("Installation failed. Check the output above.", "#ff6b6b")
                self.log("=" * 60, "#ff6b6b")
            
            self.root.after(0, self.installation_complete, success)
        
        threading.Thread(target=install, daemon=True).start()
    
    def installation_complete(self, success):
        self.is_installing = False
        self.install_btn.config(state='normal')
        self.check_status()
        
        if success:
            messagebox.showinfo("Success", "Unbound DNS installed successfully!\n\n"
                                          "Your system is now using secure DNS with automatic failover.")
    
    def start_unbound(self):
        self.output_text.delete(1.0, tk.END)
        self.log("Starting Unbound DNS service...")
        
        def start():
            if self.os_type == "macos":
                success = self.run_command("brew services start unbound")
            else:
                success = self.run_command("sudo systemctl start unbound")
            
            if success:
                self.log("Unbound started successfully", "#28a745")
            else:
                self.log("Failed to start Unbound", "#ff6b6b")
            
            self.root.after(0, self.check_status)
        
        threading.Thread(target=start, daemon=True).start()
    
    def stop_unbound(self):
        self.output_text.delete(1.0, tk.END)
        self.log("Stopping Unbound DNS service...")
        
        def stop():
            if self.os_type == "macos":
                success = self.run_command("brew services stop unbound")
            else:
                success = self.run_command("sudo systemctl stop unbound")
            
            if success:
                self.log("Unbound stopped successfully", "#28a745")
            else:
                self.log("Failed to stop Unbound", "#ff6b6b")
            
            self.root.after(0, self.check_status)
        
        threading.Thread(target=stop, daemon=True).start()
    
    def test_dns(self):
        self.output_text.delete(1.0, tk.END)
        self.log("Testing DNS resolution...")
        
        def test():
            success = self.run_command("dig @127.0.0.1 google.com +short")
            
            if success:
                self.log("DNS is working correctly!", "#28a745")
            else:
                self.log("DNS test failed", "#ff6b6b")
        
        threading.Thread(target=test, daemon=True).start()

def main():
    root = tk.Tk()
    app = UnboundInstallerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
