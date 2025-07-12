#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import subprocess
import sys
import os

class SNPediaScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SNPedia Scraper")
        self.root.geometry("600x400")
        
        # Status frame
        status_frame = ttk.Frame(root, padding="10")
        status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.status_label = ttk.Label(status_frame, text="Status: Ready")
        self.status_label.pack()
        
        self.progress_label = ttk.Label(status_frame, text="SNPs scraped: 0")
        self.progress_label.pack()
        
        # Control buttons
        button_frame = ttk.Frame(root, padding="10")
        button_frame.grid(row=1, column=0)
        
        self.start_button = ttk.Button(button_frame, text="Start Scraping", command=self.start_scraping)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_scraping, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Log output
        self.log_text = scrolledtext.ScrolledText(root, height=20, width=70)
        self.log_text.grid(row=2, column=0, padx=10, pady=10)
        
        self.process = None
        
    def start_scraping(self):
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Status: Running")
        
        # Run scraper in subprocess
        self.process = subprocess.Popen(
            [sys.executable, "snpedia_scraper.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor output in thread
        threading.Thread(target=self.monitor_output, daemon=True).start()
        
    def monitor_output(self):
        for line in iter(self.process.stdout.readline, ''):
            self.log_text.insert(tk.END, line)
            self.log_text.see(tk.END)
            
            # Update progress
            if "Scraped" in line and "SNPs" in line:
                try:
                    count = line.split()[1]
                    self.progress_label.config(text=f"SNPs scraped: {count}")
                except:
                    pass
        
        self.status_label.config(text="Status: Stopped")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
    def stop_scraping(self):
        if self.process:
            self.process.terminate()

if __name__ == "__main__":
    root = tk.Tk()
    app = SNPediaScraperGUI(root)
    root.mainloop()
