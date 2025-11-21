#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import threading
import os
import platform
import re
import time
from pathlib import Path
from datetime import datetime

class UnboundInstallerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Unbound DNS Installer")
        self.root.geometry("900x700")
        self.root.resizable(True, True)

        self.is_installing = False
        self.os_type = self.detect_os()
        self.auto_refresh = tk.BooleanVar(value=False)
        self.config_path = None
        self.refresh_job = None

        self.setup_styles()
        self.create_widgets()
        self.check_status()
        self.detect_config_path()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        bg_color = '#f0f0f0'
        accent_color = '#0066cc'
        success_color = '#28a745'
        error_color = '#dc3545'
        warning_color = '#ffa500'

        style.configure('Title.TLabel', font=('Helvetica', 18, 'bold'), foreground=accent_color)
        style.configure('Subtitle.TLabel', font=('Helvetica', 10), foreground='#666666')
        style.configure('Status.TLabel', font=('Helvetica', 10, 'bold'))
        style.configure('Success.TLabel', foreground=success_color, font=('Helvetica', 10, 'bold'))
        style.configure('Error.TLabel', foreground=error_color, font=('Helvetica', 10, 'bold'))
        style.configure('Warning.TLabel', foreground=warning_color, font=('Helvetica', 10, 'bold'))
        style.configure('Primary.TButton', font=('Helvetica', 10, 'bold'), padding=5)
        style.configure('Secondary.TButton', font=('Helvetica', 9), padding=3)

    def detect_os(self):
        system = platform.system()
        if system == "Darwin":
            return "macos"
        elif system == "Linux":
            return "linux"
        else:
            return "unknown"

    def create_widgets(self):
        self.create_menu()

        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        title_label = ttk.Label(header_frame, text="Unbound DNS Installer", style='Title.TLabel')
        title_label.grid(row=0, column=0, sticky=tk.W)

        subtitle_label = ttk.Label(header_frame,
                                   text="Resilient DNS with Automatic Failover & DoT Support",
                                   style='Subtitle.TLabel')
        subtitle_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)

        ttk.Label(status_frame, text="Operating System:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.os_label = ttk.Label(status_frame, text=self.os_type.upper())
        self.os_label.grid(row=0, column=1, sticky=tk.W, pady=3)

        ttk.Label(status_frame, text="Unbound Status:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.status_label = ttk.Label(status_frame, text="Checking...", style='Status.TLabel')
        self.status_label.grid(row=1, column=1, sticky=tk.W, pady=3)

        ttk.Label(status_frame, text="Port 53:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.port_label = ttk.Label(status_frame, text="Checking...")
        self.port_label.grid(row=2, column=1, sticky=tk.W, pady=3)

        ttk.Label(status_frame, text="Config File:").grid(row=3, column=0, sticky=tk.W, pady=3)
        self.config_label = ttk.Label(status_frame, text="Not detected")
        self.config_label.grid(row=3, column=1, sticky=tk.W, pady=3)

        ttk.Label(status_frame, text="Last Check:").grid(row=4, column=0, sticky=tk.W, pady=3)
        self.last_check_label = ttk.Label(status_frame, text="Never")
        self.last_check_label.grid(row=4, column=1, sticky=tk.W, pady=3)

        refresh_check = ttk.Checkbutton(status_frame, text="Auto-refresh (5s)",
                                       variable=self.auto_refresh,
                                       command=self.toggle_auto_refresh)
        refresh_check.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

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
        button_frame.columnconfigure(4, weight=1)

        self.install_btn = ttk.Button(button_frame, text="Install",
                                      command=self.install_unbound, style='Primary.TButton')
        self.install_btn.grid(row=0, column=0, padx=3, pady=5, sticky=(tk.W, tk.E))

        self.start_btn = ttk.Button(button_frame, text="Start",
                                    command=self.start_unbound, state='disabled')
        self.start_btn.grid(row=0, column=1, padx=3, pady=5, sticky=(tk.W, tk.E))

        self.stop_btn = ttk.Button(button_frame, text="Stop",
                                   command=self.stop_unbound, state='disabled')
        self.stop_btn.grid(row=0, column=2, padx=3, pady=5, sticky=(tk.W, tk.E))

        self.restart_btn = ttk.Button(button_frame, text="Restart",
                                     command=self.restart_unbound, state='disabled')
        self.restart_btn.grid(row=0, column=3, padx=3, pady=5, sticky=(tk.W, tk.E))

        self.test_btn = ttk.Button(button_frame, text="Test DNS",
                                   command=self.test_dns)
        self.test_btn.grid(row=0, column=4, padx=3, pady=5, sticky=(tk.W, tk.E))

        utility_frame = ttk.Frame(main_frame)
        utility_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        utility_frame.columnconfigure(0, weight=1)
        utility_frame.columnconfigure(1, weight=1)
        utility_frame.columnconfigure(2, weight=1)

        self.refresh_btn = ttk.Button(utility_frame, text="Refresh Status",
                                      command=self.manual_refresh, style='Secondary.TButton')
        self.refresh_btn.grid(row=0, column=0, padx=3, pady=2, sticky=(tk.W, tk.E))

        self.view_config_btn = ttk.Button(utility_frame, text="View Config",
                                         command=self.view_config, style='Secondary.TButton',
                                         state='disabled')
        self.view_config_btn.grid(row=0, column=1, padx=3, pady=2, sticky=(tk.W, tk.E))

        self.clear_btn = ttk.Button(utility_frame, text="Clear Output",
                                    command=self.clear_output, style='Secondary.TButton')
        self.clear_btn.grid(row=0, column=2, padx=3, pady=2, sticky=(tk.W, tk.E))

        self.log("GUI initialized. Ready to install Unbound DNS.")
        self.log(f"Detected OS: {self.os_type.upper()}")

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Log", command=self.export_log)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="View Config", command=self.view_config)
        tools_menu.add_command(label="Fix Config (Regenerate)", command=self.fix_config)
        tools_menu.add_separator()
        tools_menu.add_command(label="View System DNS", command=self.view_system_dns)
        tools_menu.add_command(label="Check Port 53", command=self.check_port_53)
        tools_menu.add_command(label="Test Multiple Servers", command=self.test_multiple_dns)
        tools_menu.add_separator()
        tools_menu.add_command(label="Flush DNS Cache", command=self.flush_cache)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Documentation", command=self.show_docs)

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

    def run_command(self, command, shell=True, show_command=True):
        try:
            if show_command:
                self.log(f"$ {command if isinstance(command, str) else ' '.join(command)}", "#888888")

            result = subprocess.run(command, shell=shell, capture_output=True, text=True, timeout=120)

            if result.stdout:
                output = result.stdout.strip()
                if output:
                    self.log(output)

            if result.returncode != 0:
                if result.stderr:
                    stderr = result.stderr.strip()
                    if stderr:
                        self.log(stderr, "#ff6b6b")
                return False

            return True
        except subprocess.TimeoutExpired:
            self.log("Command timed out after 120 seconds", "#ff6b6b")
            return False
        except FileNotFoundError:
            self.log(f"Command not found: {command}", "#ff6b6b")
            return False
        except Exception as e:
            self.log(f"Error executing command: {str(e)}", "#ff6b6b")
            return False

    def check_status(self):
        def check():
            try:
                is_running = False
                port_in_use = False

                if self.os_type == "macos":
                    result = subprocess.run(['pgrep', '-x', 'unbound'],
                                          capture_output=True, timeout=5)
                    is_running = result.returncode == 0
                else:
                    result = subprocess.run(['systemctl', 'is-active', 'unbound'],
                                          capture_output=True, text=True, timeout=5)
                    is_running = result.stdout.strip() == 'active'

                port_check = subprocess.run(['sudo', 'lsof', '-i', ':53', '-sTCP:LISTEN'],
                                           capture_output=True, timeout=5)
                port_in_use = port_check.returncode == 0

                self.root.after(0, self.update_status, is_running, port_in_use, None)
            except subprocess.TimeoutExpired:
                self.root.after(0, self.update_status, False, False, "Timeout checking status")
            except Exception as e:
                self.root.after(0, self.update_status, False, False, str(e))

        threading.Thread(target=check, daemon=True).start()

    def update_status(self, is_running, port_in_use, error=None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.last_check_label.config(text=timestamp)

        if error:
            self.status_label.config(text=f"Error: {error}", style='Error.TLabel')
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='disabled')
            self.restart_btn.config(state='disabled')
        elif is_running:
            self.status_label.config(text="Running", style='Success.TLabel')
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            self.restart_btn.config(state='normal')
        else:
            self.status_label.config(text="Not Running", style='Error.TLabel')
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            self.restart_btn.config(state='disabled')

        if port_in_use:
            self.port_label.config(text="In Use", foreground='#ffa500')
        else:
            self.port_label.config(text="Available", foreground='#28a745')

    def detect_config_path(self):
        possible_paths = []

        if self.os_type == "macos":
            try:
                brew_prefix = subprocess.run(['brew', '--prefix'],
                                            capture_output=True, text=True, timeout=5)
                if brew_prefix.returncode == 0:
                    prefix = brew_prefix.stdout.strip()
                    possible_paths.append(f"{prefix}/etc/unbound/unbound.conf")
            except:
                pass
        else:
            possible_paths.append("/etc/unbound/unbound.conf")

        for path in possible_paths:
            if os.path.exists(path):
                self.config_path = path
                self.config_label.config(text=path, foreground='#28a745')
                self.view_config_btn.config(state='normal')
                return

        self.config_label.config(text="Not found", foreground='#999999')

    def toggle_auto_refresh(self):
        if self.auto_refresh.get():
            self.auto_refresh_status()
        else:
            if self.refresh_job:
                self.root.after_cancel(self.refresh_job)
                self.refresh_job = None

    def auto_refresh_status(self):
        if self.auto_refresh.get():
            self.check_status()
            self.refresh_job = self.root.after(5000, self.auto_refresh_status)

    def manual_refresh(self):
        self.log("Refreshing status...", "#0066cc")
        self.check_status()
        self.detect_config_path()

    def clear_output(self):
        self.output_text.delete(1.0, tk.END)
        self.log("Output cleared.")

    def view_config(self):
        if not self.config_path or not os.path.exists(self.config_path):
            messagebox.showerror("Error", "Configuration file not found.")
            return

        try:
            with open(self.config_path, 'r') as f:
                content = f.read()

            config_window = tk.Toplevel(self.root)
            config_window.title(f"Unbound Configuration - {self.config_path}")
            config_window.geometry("800x600")

            text_frame = ttk.Frame(config_window, padding="10")
            text_frame.pack(fill=tk.BOTH, expand=True)

            text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD,
                                                   font=('Courier', 10))
            text_widget.pack(fill=tk.BOTH, expand=True)
            text_widget.insert(1.0, content)
            text_widget.config(state='disabled')

            button_frame = ttk.Frame(config_window, padding="10")
            button_frame.pack(fill=tk.X)

            ttk.Button(button_frame, text="Close",
                      command=config_window.destroy).pack(side=tk.RIGHT)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to read config file:\n{str(e)}")

    def fix_config(self):
        if not self.config_path:
            messagebox.showerror("Error", "Configuration path not detected.\nPlease install Unbound first.")
            return

        response = messagebox.askyesno("Fix Configuration",
                                       "This will regenerate the Unbound configuration file\n"
                                       "with macOS-compatible settings.\n\n"
                                       "A backup will be created.\n\n"
                                       "Continue?")
        if not response:
            return

        self.output_text.delete(1.0, tk.END)
        self.log("Regenerating Unbound configuration...", "#0066cc")

        def fix():
            try:
                backup_path = f"{self.config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                if os.path.exists(self.config_path):
                    result = subprocess.run(['sudo', 'cp', self.config_path, backup_path],
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        self.log(f"Backup created: {backup_path}", "#28a745")
                    else:
                        self.log(f"Warning: Could not create backup", "#ffa500")

                config_content = """server:
    verbosity: 1
    interface: 127.0.0.1
    interface: ::1
    port: 53

    do-ip4: yes
    do-ip6: yes
    do-udp: yes
    do-tcp: yes

    access-control: 127.0.0.0/8 allow
    access-control: ::1 allow
    access-control: 0.0.0.0/0 refuse
    access-control: ::/0 refuse

    hide-identity: yes
    hide-version: yes
    harden-glue: yes
    harden-dnssec-stripped: yes
    harden-referral-path: yes
    harden-algo-downgrade: yes

    use-caps-for-id: yes
    qname-minimisation: yes

    cache-min-ttl: 3600
    cache-max-ttl: 86400
    prefetch: yes
    prefetch-key: yes

    serve-expired: yes
    serve-expired-ttl: 86400
    serve-expired-client-timeout: 1800

    rrset-cache-size: 100m
    msg-cache-size: 50m
    key-cache-size: 100m
    neg-cache-size: 10m

    num-threads: 2
    msg-cache-slabs: 4
    rrset-cache-slabs: 4
    infra-cache-slabs: 4
    key-cache-slabs: 4

    outgoing-range: 8192
    num-queries-per-thread: 4096
    so-rcvbuf: 4m
    so-sndbuf: 4m

    edns-buffer-size: 1232

    unwanted-reply-threshold: 10000
    do-not-query-localhost: no

    val-clean-additional: yes

    logfile: ""
    use-syslog: yes
    log-queries: no
    log-replies: no

forward-zone:
    name: "."

    forward-tls-upstream: yes
    forward-first: no

    forward-addr: 1.1.1.1@853#cloudflare-dns.com
    forward-addr: 1.0.0.1@853#cloudflare-dns.com

    forward-addr: 9.9.9.9@853#dns.quad9.net
    forward-addr: 149.112.112.112@853#dns.quad9.net

    forward-addr: 8.8.8.8@853#dns.google
    forward-addr: 8.8.4.4@853#dns.google
"""

                temp_file = f"/tmp/unbound_config_{os.getpid()}.conf"
                with open(temp_file, 'w') as f:
                    f.write(config_content)

                self.log(f"Wrote temporary config to: {temp_file}", "#28a745")

                result = subprocess.run(['sudo', 'cp', temp_file, self.config_path],
                                       capture_output=True, text=True, timeout=10)

                os.remove(temp_file)

                if result.returncode == 0:
                    self.log(f"Configuration written to: {self.config_path}", "#28a745")
                else:
                    self.log(f"ERROR: Failed to write config file", "#ff6b6b")
                    if result.stderr:
                        self.log(result.stderr, "#ff6b6b")
                    messagebox.showerror("Error", "Failed to write configuration file.\nCheck output for details.")
                    return

                self.log("\nVerifying configuration...", "#0066cc")

                verify = subprocess.run(['sudo', 'unbound-checkconf', self.config_path],
                                       capture_output=True, text=True, timeout=5)

                if verify.returncode == 0:
                    self.log("Configuration is valid!", "#28a745")
                    self.log("\nConfiguration fix complete. You can now start Unbound.", "#0066cc")
                    messagebox.showinfo("Success",
                                      "Configuration regenerated successfully!\n\n"
                                      "The config no longer requires the 'unbound' user.\n\n"
                                      "Click Start to launch Unbound with the new config.")
                else:
                    self.log("Configuration validation failed:", "#ff6b6b")
                    if verify.stderr:
                        self.log(verify.stderr, "#ff6b6b")
                    messagebox.showerror("Validation Failed",
                                       "The configuration was created but validation failed.\n"
                                       "Check the output window for details.")

            except Exception as e:
                self.log(f"ERROR: {str(e)}", "#ff6b6b")
                messagebox.showerror("Error", f"Failed to regenerate config:\n{str(e)}")

        threading.Thread(target=fix, daemon=True).start()

    def view_system_dns(self):
        self.output_text.delete(1.0, tk.END)
        self.log("Checking system DNS configuration...", "#0066cc")

        def check():
            if self.os_type == "macos":
                self.run_command("scutil --dns | grep 'nameserver'")
            else:
                self.run_command("cat /etc/resolv.conf")

        threading.Thread(target=check, daemon=True).start()

    def check_port_53(self):
        self.output_text.delete(1.0, tk.END)
        self.log("Checking what's using port 53...", "#0066cc")
        self.log("=" * 50, "#0066cc")

        def check():
            self.log("\nChecking TCP port 53:")
            self.run_command("sudo lsof -i :53 -sTCP:LISTEN")

            self.log("\nChecking UDP port 53:")
            self.run_command("sudo lsof -i :53 -sUDP:Idle")

            self.log("\nChecking for Unbound process:")
            result = subprocess.run(['pgrep', '-fl', 'unbound'],
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.log(result.stdout.strip(), "#28a745")
            else:
                self.log("No Unbound process found", "#ff6b6b")

            self.log("\n" + "=" * 50, "#0066cc")
            self.log("Diagnostic complete", "#0066cc")

        threading.Thread(target=check, daemon=True).start()

    def test_multiple_dns(self):
        self.output_text.delete(1.0, tk.END)
        self.log("Testing multiple DNS servers...", "#0066cc")

        def test():
            servers = [
                ("Local Unbound", "127.0.0.1"),
                ("Cloudflare", "1.1.1.1"),
                ("Google", "8.8.8.8"),
                ("Quad9", "9.9.9.9")
            ]

            for name, server in servers:
                self.log(f"\nTesting {name} ({server}):", "#0066cc")
                start = time.time()
                result = subprocess.run(
                    f"dig @{server} google.com +short +time=3",
                    shell=True, capture_output=True, text=True, timeout=5
                )
                elapsed = (time.time() - start) * 1000

                if result.returncode == 0 and result.stdout.strip():
                    self.log(f"Response time: {elapsed:.0f}ms", "#28a745")
                    self.log(f"Result: {result.stdout.strip()[:50]}")
                else:
                    self.log("Failed or timeout", "#ff6b6b")

        threading.Thread(target=test, daemon=True).start()

    def flush_cache(self):
        self.output_text.delete(1.0, tk.END)
        self.log("Flushing DNS cache...", "#0066cc")

        def flush():
            if self.os_type == "macos":
                self.run_command("sudo dscacheutil -flushcache")
                self.run_command("sudo killall -HUP mDNSResponder")
            else:
                self.run_command("sudo systemctl restart unbound")

            self.log("DNS cache flushed", "#28a745")

        threading.Thread(target=flush, daemon=True).start()

    def export_log(self):
        content = self.output_text.get(1.0, tk.END)

        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"unbound_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Log exported to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export log:\n{str(e)}")

    def show_about(self):
        about_text = """Unbound DNS Installer GUI
Version 2.0

A modern interface for installing and managing
Unbound DNS with automatic failover and DoT support.

Features:
- Cross-platform support
- Real-time monitoring
- DNS-over-TLS encryption
- Automatic failover
- DNSSEC validation

Supports: macOS, Debian, Ubuntu, Fedora, Arch Linux"""

        messagebox.showinfo("About", about_text)

    def show_docs(self):
        docs_text = """Quick Start Guide:

1. Install: Click Install button to set up Unbound
2. Monitor: Check status indicators for service health
3. Test: Use Test DNS to verify functionality
4. Manage: Use Start/Stop/Restart as needed

Menu Options:
- File > Export Log: Save output to file
- Tools > View Config: See Unbound configuration
- Tools > View System DNS: Check DNS settings
- Tools > Test Multiple Servers: Compare performance
- Tools > Flush DNS Cache: Clear cached entries

Tips:
- Enable Auto-refresh for live monitoring
- Check Last Check timestamp for freshness
- Use Clear Output to reset the log window"""

        messagebox.showinfo("Documentation", docs_text)

    def restart_unbound(self):
        self.output_text.delete(1.0, tk.END)
        self.log("Restarting Unbound DNS service...")

        def restart():
            if self.os_type == "macos":
                self.run_command("sudo killall unbound")
                time.sleep(2)
                try:
                    brew_prefix = subprocess.run(['brew', '--prefix'],
                                                capture_output=True, text=True, timeout=5)
                    if brew_prefix.returncode == 0:
                        prefix = brew_prefix.stdout.strip()
                        config_path = f"{prefix}/etc/unbound/unbound.conf"
                        success = self.run_command(f"sudo {prefix}/sbin/unbound -c {config_path} &")
                    else:
                        success = False
                except:
                    success = False
            else:
                success = self.run_command("sudo systemctl restart unbound")

            time.sleep(2)

            if success:
                self.log("Unbound restarted successfully", "#28a745")
            else:
                self.log("Failed to restart Unbound", "#ff6b6b")

            self.root.after(0, self.check_status)

        threading.Thread(target=restart, daemon=True).start()

    def install_unbound(self):
        if self.is_installing:
            messagebox.showwarning("Busy", "Installation is already in progress")
            return

        if self.os_type == "macos":
            confirm_msg = ("This will install Unbound DNS and modify system DNS settings.\n\n"
                          "The script will request sudo privileges when needed.\n\n"
                          "Continue?")
        else:
            confirm_msg = ("This will install Unbound DNS and modify system DNS settings.\n\n"
                          "The script requires sudo privileges.\n\n"
                          "Continue?")

        response = messagebox.askyesno("Confirm Installation", confirm_msg)
        if not response:
            return

        self.is_installing = True
        self.install_btn.config(state='disabled')
        self.output_text.delete(1.0, tk.END)

        def install():
            self.log("=" * 70, "#0066cc")
            self.log("STARTING UNBOUND DNS INSTALLATION", "#0066cc")
            self.log("=" * 70, "#0066cc")
            self.log("")

            script_path = Path(__file__).parent / "unbound_dns.sh"

            if not script_path.exists():
                self.log("ERROR: unbound_dns.sh not found!", "#ff6b6b")
                self.log("Please ensure the bash script is in the same directory.", "#ff6b6b")
                self.log(f"Looking for: {script_path}", "#ff6b6b")
                self.root.after(0, self.installation_complete, False)
                return

            self.log(f"Found installation script: {script_path}", "#28a745")
            self.log("Starting installation process...\n")

            if self.os_type == "macos":
                success = self.run_command(f"bash {script_path}")
            else:
                success = self.run_command(f"sudo bash {script_path}")

            self.log("")
            if success:
                self.log("=" * 70, "#28a745")
                self.log("INSTALLATION COMPLETED SUCCESSFULLY", "#28a745")
                self.log("=" * 70, "#28a745")
                self.log("\nYour system is now using Unbound DNS with:", "#28a745")
                self.log("  - DNS-over-TLS encryption", "#28a745")
                self.log("  - Automatic failover", "#28a745")
                self.log("  - DNSSEC validation", "#28a745")
            else:
                self.log("=" * 70, "#ff6b6b")
                self.log("INSTALLATION FAILED", "#ff6b6b")
                self.log("=" * 70, "#ff6b6b")
                self.log("\nPlease check the error messages above.", "#ff6b6b")

            self.root.after(0, self.installation_complete, success)

        threading.Thread(target=install, daemon=True).start()

    def installation_complete(self, success):
        self.is_installing = False
        self.install_btn.config(state='normal')
        self.check_status()
        self.detect_config_path()

        if success:
            messagebox.showinfo("Success",
                              "Unbound DNS installed successfully!\n\n"
                              "Your system is now using secure DNS with:\n"
                              "  • Automatic failover\n"
                              "  • DNS-over-TLS encryption\n"
                              "  • DNSSEC validation\n\n"
                              "Use 'Test DNS' to verify functionality.")
        else:
            messagebox.showerror("Installation Failed",
                               "The installation did not complete successfully.\n\n"
                               "Please check the output window for details.")

    def start_unbound(self):
        self.output_text.delete(1.0, tk.END)
        self.log("Starting Unbound DNS service...")

        def start():
            if self.os_type == "macos":
                self.log("Checking for existing Unbound processes...")
                kill_result = subprocess.run(['pgrep', '-x', 'unbound'], capture_output=True)
                if kill_result.returncode == 0:
                    self.log("Stopping existing Unbound process...")
                    self.run_command("sudo killall unbound")
                    time.sleep(2)

                try:
                    brew_prefix = subprocess.run(['brew', '--prefix'],
                                                capture_output=True, text=True, timeout=5)
                    if brew_prefix.returncode == 0:
                        prefix = brew_prefix.stdout.strip()
                        unbound_bin = f"{prefix}/sbin/unbound"
                        config_path = f"{prefix}/etc/unbound/unbound.conf"

                        self.log(f"Using Unbound binary: {unbound_bin}")
                        self.log(f"Using config: {config_path}")

                        if not os.path.exists(unbound_bin):
                            self.log(f"ERROR: Unbound binary not found at {unbound_bin}", "#ff6b6b")
                            success = False
                        elif not os.path.exists(config_path):
                            self.log(f"ERROR: Config file not found at {config_path}", "#ff6b6b")
                            success = False
                        else:
                            self.log("Starting Unbound with sudo...")
                            result = subprocess.run(
                                ['sudo', unbound_bin, '-c', config_path],
                                capture_output=True, text=True, timeout=10
                            )

                            if result.returncode != 0:
                                self.log(f"ERROR: Unbound failed to start", "#ff6b6b")
                                if result.stderr:
                                    self.log(f"Error output: {result.stderr}", "#ff6b6b")
                                if result.stdout:
                                    self.log(f"Output: {result.stdout}")
                                success = False
                            else:
                                time.sleep(2)
                                check = subprocess.run(['pgrep', '-x', 'unbound'], capture_output=True)
                                success = check.returncode == 0

                                if not success:
                                    self.log("WARNING: Command succeeded but process not found", "#ffa500")
                    else:
                        self.log("ERROR: Could not determine Homebrew prefix", "#ff6b6b")
                        success = False
                except Exception as e:
                    self.log(f"ERROR: Exception while starting: {str(e)}", "#ff6b6b")
                    success = False
            else:
                success = self.run_command("sudo systemctl start unbound")

            time.sleep(2)

            if success:
                self.log("Unbound started successfully", "#28a745")
                self.log("Verifying Unbound is running...")
                if self.os_type == "macos":
                    verify = subprocess.run(['pgrep', '-x', 'unbound'], capture_output=True)
                    if verify.returncode == 0:
                        self.log("Verified: Unbound process is running", "#28a745")
                    else:
                        self.log("WARNING: Unbound process not found after start", "#ffa500")
            else:
                self.log("Failed to start Unbound", "#ff6b6b")
                self.log("\nTroubleshooting:", "#ffa500")
                self.log("1. Try running manually: sudo $(brew --prefix)/sbin/unbound -c $(brew --prefix)/etc/unbound/unbound.conf", "#ffa500")
                self.log("2. Check config syntax: sudo unbound-checkconf", "#ffa500")
                self.log("3. View errors with: Tools > Check Port 53", "#ffa500")

            self.root.after(0, self.check_status)

        threading.Thread(target=start, daemon=True).start()

    def stop_unbound(self):
        self.output_text.delete(1.0, tk.END)
        self.log("Stopping Unbound DNS service...")

        def stop():
            if self.os_type == "macos":
                success = self.run_command("sudo killall unbound")
            else:
                success = self.run_command("sudo systemctl stop unbound")

            time.sleep(1)

            if success:
                self.log("Unbound stopped successfully", "#28a745")
            else:
                self.log("Failed to stop Unbound", "#ff6b6b")

            self.root.after(0, self.check_status)

        threading.Thread(target=stop, daemon=True).start()

    def test_dns(self):
        self.output_text.delete(1.0, tk.END)
        self.log("Testing DNS resolution...", "#0066cc")
        self.log("=" * 50, "#0066cc")

        def test():
            self.log("\nChecking if Unbound is running...")
            if self.os_type == "macos":
                check = subprocess.run(['pgrep', '-x', 'unbound'],
                                      capture_output=True, timeout=5)
                is_running = check.returncode == 0
            else:
                check = subprocess.run(['systemctl', 'is-active', 'unbound'],
                                      capture_output=True, text=True, timeout=5)
                is_running = check.stdout.strip() == 'active'

            if not is_running:
                self.log("ERROR: Unbound is not running!", "#ff6b6b")
                self.log("Please start Unbound first using the Start button.", "#ff6b6b")
                return

            self.log("Unbound is running. Checking port 53...", "#28a745")
            port_check = subprocess.run(['sudo', 'lsof', '-i', ':53'],
                                       capture_output=True, text=True, timeout=5)
            if port_check.returncode == 0:
                self.log("Port 53 is in use (good!)", "#28a745")
                if 'unbound' in port_check.stdout:
                    self.log("Unbound is listening on port 53", "#28a745")
                else:
                    self.log("WARNING: Another process is using port 53", "#ffa500")
                    self.log(port_check.stdout[:200])
            else:
                self.log("WARNING: Port 53 check inconclusive", "#ffa500")

            test_domains = ["google.com", "cloudflare.com", "github.com"]
            all_passed = True

            for domain in test_domains:
                self.log(f"\nQuerying {domain} via local Unbound (127.0.0.1)...")
                start = time.time()

                try:
                    result = subprocess.run(
                        f"dig @127.0.0.1 {domain} +short +time=5 +tries=1",
                        shell=True, capture_output=True, text=True, timeout=8
                    )
                    elapsed = (time.time() - start) * 1000

                    if result.returncode == 0 and result.stdout.strip():
                        self.log(f"SUCCESS - Response time: {elapsed:.0f}ms", "#28a745")
                        ips = result.stdout.strip().split('\n')
                        for ip in ips[:3]:
                            if ip:
                                self.log(f"  → {ip}")
                    else:
                        self.log(f"FAILED - No response", "#ff6b6b")
                        if result.stderr:
                            self.log(f"Error: {result.stderr[:100]}", "#ff6b6b")
                        all_passed = False
                except subprocess.TimeoutExpired:
                    self.log(f"FAILED - Query timed out (>8s)", "#ff6b6b")
                    self.log("This suggests Unbound is not responding on 127.0.0.1:53", "#ff6b6b")
                    all_passed = False

            self.log("\n" + "=" * 50, "#0066cc")
            if all_passed:
                self.log("DNS TEST RESULT: ALL TESTS PASSED", "#28a745")
                self.log("Your DNS is working correctly!", "#28a745")
            else:
                self.log("DNS TEST RESULT: SOME TESTS FAILED", "#ff6b6b")
                self.log("\nTroubleshooting steps:", "#ffa500")
                self.log("1. Check if Unbound is running (Status panel)", "#ffa500")
                self.log("2. Try restarting Unbound", "#ffa500")
                self.log("3. Check config with 'View Config' button", "#ffa500")
                if self.os_type == "macos":
                    self.log("4. Run: sudo lsof -i :53", "#ffa500")
                else:
                    self.log("4. Run: sudo systemctl status unbound", "#ffa500")

        threading.Thread(target=test, daemon=True).start()

def main():
    root = tk.Tk()
    app = UnboundInstallerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
