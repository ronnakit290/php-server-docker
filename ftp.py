import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import ftplib
import os
import threading
from datetime import datetime
from tkinter import simpledialog
from typing import Optional
import json
import shutil

class FTPClient:
    def __init__(self, root):
        self.root = root
        self.root.title("FTP Client - ใช้งานง่าย")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')
        
        self.ftp: Optional[ftplib.FTP] = None
        self.connected = False
        self.current_local_path = os.getcwd()
        self.current_remote_path = "/"
        self.configs = self.load_configs()
        
        self.create_widgets()
        self.refresh_local_files()
        
    def create_widgets(self):
        # Connection Frame
        conn_frame = ttk.LabelFrame(self.root, text="การเชื่อมต่อ FTP", padding="10")
        conn_frame.pack(fill="x", padx=10, pady=5)
        
        # Server info
        ttk.Label(conn_frame, text="Server:").grid(row=0, column=0, sticky="w", padx=5)
        self.server_entry = ttk.Entry(conn_frame, width=20)
        self.server_entry.grid(row=0, column=1, padx=5)
        self.server_entry.insert(0, "ftp.example.com")
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky="w", padx=5)
        self.port_entry = ttk.Entry(conn_frame, width=8)
        self.port_entry.grid(row=0, column=3, padx=5)
        self.port_entry.insert(0, "21")
        
        ttk.Label(conn_frame, text="Username:").grid(row=1, column=0, sticky="w", padx=5)
        self.user_entry = ttk.Entry(conn_frame, width=20)
        self.user_entry.grid(row=1, column=1, padx=5)
        
        ttk.Label(conn_frame, text="Password:").grid(row=1, column=2, sticky="w", padx=5)
        self.pass_entry = ttk.Entry(conn_frame, width=20, show="*")
        self.pass_entry.grid(row=1, column=3, padx=5)
        
        # Profile combobox
        ttk.Label(conn_frame, text="โปรไฟล์:").grid(row=2, column=0, sticky="w", padx=5, pady=(5,0))
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(conn_frame, textvariable=self.profile_var, state="readonly", width=18)
        self.profile_combo["values"] = list(self.configs.keys())
        self.profile_combo.grid(row=2, column=1, sticky="w", padx=5, pady=(5,0))
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_selected)
        
        # Connection buttons
        self.connect_btn = ttk.Button(conn_frame, text="เชื่อมต่อ", command=self.connect_ftp)
        self.connect_btn.grid(row=0, column=4, padx=10)
        
        self.disconnect_btn = ttk.Button(conn_frame, text="ตัดการเชื่อมต่อ", command=self.disconnect_ftp, state="disabled")
        self.disconnect_btn.grid(row=1, column=4, padx=10)
        
        # Main content frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Local files frame
        local_frame = ttk.LabelFrame(main_frame, text="ไฟล์ในเครื่อง", padding="5")
        local_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        # Local path
        local_path_frame = ttk.Frame(local_frame)
        local_path_frame.pack(fill="x", pady=5)
        
        ttk.Label(local_path_frame, text="Path:").pack(side="left")
        self.local_path_var = tk.StringVar(value=self.current_local_path)
        ttk.Entry(local_path_frame, textvariable=self.local_path_var, state="readonly").pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(local_path_frame, text="เลือกโฟลเดอร์", command=self.browse_local_folder).pack(side="right")
        
        # Local file list
        local_list_frame = ttk.Frame(local_frame)
        local_list_frame.pack(fill="both", expand=True)
        
        self.local_tree = ttk.Treeview(local_list_frame, columns=("size", "modified"), show="tree headings")
        self.local_tree.heading("#0", text="ชื่อไฟล์")
        self.local_tree.heading("size", text="ขนาด")
        self.local_tree.heading("modified", text="วันที่แก้ไข")
        self.local_tree.column("#0", width=200)
        self.local_tree.column("size", width=100)
        self.local_tree.column("modified", width=150)
        
        local_scroll = ttk.Scrollbar(local_list_frame, orient="vertical", command=self.local_tree.yview)
        self.local_tree.configure(yscrollcommand=local_scroll.set)
        
        self.local_tree.pack(side="left", fill="both", expand=True)
        local_scroll.pack(side="right", fill="y")
        
        self.local_tree.bind("<Double-1>", self.on_local_double_click)
        
        # Transfer buttons frame
        transfer_frame = ttk.Frame(main_frame)
        transfer_frame.pack(side="left", fill="y", padx=10)
        
        ttk.Button(transfer_frame, text="อัปโหลด →", command=self.upload_file, width=12).pack(pady=10)
        ttk.Button(transfer_frame, text="← ดาวน์โหลด", command=self.download_file, width=12).pack(pady=10)
        ttk.Button(transfer_frame, text="รีเฟรช", command=self.refresh_all, width=12).pack(pady=10)
        
        # Remote files frame
        remote_frame = ttk.LabelFrame(main_frame, text="ไฟล์บนเซิร์ฟเวอร์", padding="5")
        remote_frame.pack(side="right", fill="both", expand=True, padx=5)
        
        # Remote path
        remote_path_frame = ttk.Frame(remote_frame)
        remote_path_frame.pack(fill="x", pady=5)
        
        ttk.Label(remote_path_frame, text="Path:").pack(side="left")
        self.remote_path_var = tk.StringVar(value=self.current_remote_path)
        ttk.Entry(remote_path_frame, textvariable=self.remote_path_var, state="readonly").pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(remote_path_frame, text="ไปที่โฟลเดอร์", command=self.go_to_remote_folder).pack(side="right")
        
        # Remote file list
        remote_list_frame = ttk.Frame(remote_frame)
        remote_list_frame.pack(fill="both", expand=True)
        
        self.remote_tree = ttk.Treeview(remote_list_frame, columns=("size", "modified"), show="tree headings")
        self.remote_tree.heading("#0", text="ชื่อไฟล์")
        self.remote_tree.heading("size", text="ขนาด")
        self.remote_tree.heading("modified", text="วันที่แก้ไข")
        self.remote_tree.column("#0", width=200)
        self.remote_tree.column("size", width=100)
        self.remote_tree.column("modified", width=150)
        
        remote_scroll = ttk.Scrollbar(remote_list_frame, orient="vertical", command=self.remote_tree.yview)
        self.remote_tree.configure(yscrollcommand=remote_scroll.set)
        
        self.remote_tree.pack(side="left", fill="both", expand=True)
        remote_scroll.pack(side="right", fill="y")
        
        self.remote_tree.bind("<Double-1>", self.on_remote_double_click)
        
        # Context menus
        self.create_context_menus()
        
        # Log frame
        log_frame = ttk.LabelFrame(self.root, text="Log", padding="5")
        log_frame.pack(fill="x", padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state="disabled")
        self.log_text.pack(fill="x")
        
        # Status bar
        self.status_var = tk.StringVar(value="ยังไม่ได้เชื่อมต่อ")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(fill="x", side="bottom")
        
    def create_context_menus(self):
        # Local context menu
        self.local_menu = tk.Menu(self.root, tearoff=0)
        self.local_menu.add_command(label="อัปโหลด", command=self.upload_file)
        self.local_menu.add_command(label="ลบ", command=self.delete_local_file)
        self.local_menu.add_command(label="สร้างโฟลเดอร์", command=self.create_local_folder)
        
        # Remote context menu
        self.remote_menu = tk.Menu(self.root, tearoff=0)
        self.remote_menu.add_command(label="ดาวน์โหลด", command=self.download_file)
        self.remote_menu.add_command(label="ลบ", command=self.delete_remote_file)
        self.remote_menu.add_command(label="สร้างโฟลเดอร์", command=self.create_remote_folder)
        
        self.local_tree.bind("<Button-3>", self.show_local_menu)
        self.remote_tree.bind("<Button-3>", self.show_remote_menu)
        
    def show_local_menu(self, event):
        self.local_menu.post(event.x_root, event.y_root)
        
    def show_remote_menu(self, event):
        if self.connected:
            self.remote_menu.post(event.x_root, event.y_root)
    
    def log_message(self, message):
        self.log_text.config(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.config(state="disabled")
        self.log_text.see("end")
        
    def connect_ftp(self):
        server = self.server_entry.get().strip()
        port = int(self.port_entry.get().strip() or "21")
        username = self.user_entry.get().strip()
        password = self.pass_entry.get()
        
        if not server:
            messagebox.showerror("ข้อผิดพลาด", "กรุณาระบุ server")
            return
            
        def connect_thread():
            try:
                self.ftp = ftplib.FTP()
                self.ftp.connect(server, port)
                
                if username:
                    self.ftp.login(username, password)
                else:
                    self.ftp.login()
                    
                self.connected = True
                # ถ้ามี remote_dir ในโปรไฟล์ ให้เปลี่ยนไปก่อน
                try:
                    profile_name = self.profile_var.get()
                    remote_dir = self.configs.get(profile_name, {}).get("remote_dir")
                    if remote_dir:
                        self.ftp.cwd(remote_dir)
                except Exception:
                    pass
                self.current_remote_path = self.ftp.pwd()
                
                self.root.after(0, lambda: self.update_connection_status(True))
                self.root.after(0, self.refresh_remote_files)
                self.log_message(f"เชื่อมต่อสำเร็จ: {server}:{port}")
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถเชื่อมต่อได้: {str(e)}"))
                self.log_message(f"เชื่อมต่อล้มเหลว: {str(e)}")
                
        threading.Thread(target=connect_thread, daemon=True).start()
        
    def disconnect_ftp(self):
        if self.ftp:
            try:
                self.ftp.quit()
            except:
                pass
            self.ftp = None
            
        self.connected = False
        self.update_connection_status(False)
        self.remote_tree.delete(*self.remote_tree.get_children())
        self.log_message("ตัดการเชื่อมต่อแล้ว")
        
    def update_connection_status(self, connected):
        if connected:
            self.status_var.set(f"เชื่อมต่อแล้ว: {self.server_entry.get()}")
            self.connect_btn.config(state="disabled")
            self.disconnect_btn.config(state="normal")
        else:
            self.status_var.set("ยังไม่ได้เชื่อมต่อ")
            self.connect_btn.config(state="normal")
            self.disconnect_btn.config(state="disabled")
            
    def refresh_local_files(self):
        self.local_tree.delete(*self.local_tree.get_children())
        
        try:
            # Add parent directory entry
            if self.current_local_path != os.path.dirname(self.current_local_path):
                self.local_tree.insert("", "end", text="..", values=("", ""))
                
            for item in os.listdir(self.current_local_path):
                item_path = os.path.join(self.current_local_path, item)
                
                if os.path.isdir(item_path):
                    self.local_tree.insert("", "end", text=f"📁 {item}", values=("โฟลเดอร์", ""))
                else:
                    size = os.path.getsize(item_path)
                    modified = datetime.fromtimestamp(os.path.getmtime(item_path)).strftime("%Y-%m-%d %H:%M")
                    self.local_tree.insert("", "end", text=item, values=(f"{size:,} bytes", modified))
                    
        except Exception as e:
            self.log_message(f"ไม่สามารถอ่านไฟล์ในเครื่องได้: {str(e)}")
            
        self.local_path_var.set(self.current_local_path)
        
    def refresh_remote_files(self):
        if not self.connected:
            return
            
        if self.ftp is None:
            return
            
        self.remote_tree.delete(*self.remote_tree.get_children())
        
        def refresh_thread():
            try:
                assert self.ftp is not None  # Safeguard for type checker

                # Add parent directory entry
                if self.current_remote_path != "/":
                    self.root.after(0, lambda: self.remote_tree.insert("", "end", text="..", values=("", "")))

                # Try MLSD (RFC 3659) first for structured data
                entries = []
                try:
                    entries = list(self.ftp.mlsd())  # [(name, facts), ...]
                except Exception:
                    # Fallback to NLST if MLSD not supported
                    entries = [(name, {}) for name in self.ftp.nlst()]

                for name, facts in entries:
                    # Skip current and parent directory references
                    if name in (".", ".."):
                        continue

                    is_dir = False
                    size_str = ""

                    # Determine directory status
                    if "type" in facts:
                        is_dir = facts["type"] == "dir"
                    else:
                        # Last resort: attempt CWD trick
                        current = self.ftp.pwd()
                        try:
                            self.ftp.cwd(name)
                            is_dir = True
                            self.ftp.cwd(current)
                        except Exception:
                            is_dir = False

                    if is_dir:
                        self.root.after(0, lambda n=name: self.remote_tree.insert("", "end", text=f"📁 {n}", values=("โฟลเดอร์", "")))
                    else:
                        # Try to get size
                        if not size_str:
                            try:
                                size_val = self.ftp.size(name)
                                if size_val is not None:
                                    size_str = f"{size_val} bytes"
                            except Exception:
                                size_str = ""

                        self.root.after(0, lambda n=name, sz=size_str: self.remote_tree.insert("", "end", text=n, values=(sz, "")))

            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"ไม่สามารถอ่านไฟล์บนเซิร์ฟเวอร์ได้: {str(e)}"))

        threading.Thread(target=refresh_thread, daemon=True).start()
        self.remote_path_var.set(self.current_remote_path)
        
    def on_local_double_click(self, event):
        selection = self.local_tree.selection()
        if selection:
            item_text = self.local_tree.item(selection[0])["text"]
            
            if item_text == "..":
                self.current_local_path = os.path.dirname(self.current_local_path)
                self.refresh_local_files()
            elif item_text.startswith("📁"):
                folder_name = item_text[2:]  # Remove folder emoji
                self.current_local_path = os.path.join(self.current_local_path, folder_name)
                self.refresh_local_files()
                
    def on_remote_double_click(self, event):
        if not self.connected:
            return
            
        selection = self.remote_tree.selection()
        if selection:
            item_text = self.remote_tree.item(selection[0])["text"]
            
            def change_dir():
                try:
                    assert self.ftp is not None  # Safeguard
                    
                    if item_text == "..":
                        self.ftp.cwd("..")
                        self.current_remote_path = self.ftp.pwd()
                    elif item_text.startswith("📁"):
                        folder_name = item_text[2:]  # Remove folder emoji
                        self.ftp.cwd(folder_name)
                        self.current_remote_path = self.ftp.pwd()
                        
                    self.root.after(0, self.refresh_remote_files)
                except Exception as e:
                    self.root.after(0, lambda: self.log_message(f"ไม่สามารถเข้าโฟลเดอร์ได้: {str(e)}"))
                    
            threading.Thread(target=change_dir, daemon=True).start()
            
    def browse_local_folder(self):
        folder = filedialog.askdirectory(initialdir=self.current_local_path)
        if folder:
            self.current_local_path = folder
            self.refresh_local_files()
            
    def go_to_remote_folder(self):
        if not self.connected:
            messagebox.showwarning("คำเตือน", "กรุณาเชื่อมต่อก่อน")
            return
            
        path = simpledialog.askstring("ไปที่โฟลเดอร์", "ระบุ path ที่ต้องการ:", initialvalue=self.current_remote_path)
        if path:
            def change_dir():
                try:
                    assert self.ftp is not None  # Safeguard
                    
                    self.ftp.cwd(path)
                    self.current_remote_path = self.ftp.pwd()
                    self.root.after(0, self.refresh_remote_files)
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถเข้าโฟลเดอร์ได้: {str(e)}"))
                    
            threading.Thread(target=change_dir, daemon=True).start()
            
    def upload_file(self):
        if not self.connected:
            messagebox.showwarning("คำเตือน", "กรุณาเชื่อมต่อก่อน")
            return

        selection = self.local_tree.selection()
        if not selection:
            messagebox.showwarning("คำเตือน", "กรุณาเลือกไฟล์/โฟลเดอร์ที่ต้องการอัปโหลด")
            return

        item_text = self.local_tree.item(selection[0])["text"]
        if item_text == "..":
            messagebox.showwarning("คำเตือน", "กรุณาเลือกไฟล์/โฟลเดอร์ที่ถูกต้อง")
            return

        # ตรวจว่าเป็นโฟลเดอร์หรือไฟล์
        is_dir = item_text.startswith("📁")
        name_clean = item_text[2:] if is_dir else item_text  # ตัดอีโมจิ
        local_path = os.path.join(self.current_local_path, name_clean)

        def upload_thread():
            try:
                assert self.ftp is not None  # Safeguard

                remote_base = self.current_remote_path.rstrip("/")
                remote_target = f"{remote_base}/{name_clean}" if remote_base else name_clean

                if is_dir:
                    self._upload_directory_recursive(local_path, remote_target)
                else:
                    with open(local_path, 'rb') as f:
                        self.ftp.storbinary(f'STOR {remote_target}', f)

                self.log_message(f"อัปโหลดสำเร็จ: {item_text}")
                self.root.after(0, self.refresh_remote_files)

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถอัปโหลดได้: {str(e)}"))
                self.log_message(f"อัปโหลดล้มเหลว: {str(e)}")

        threading.Thread(target=upload_thread, daemon=True).start()

    # --------------------- Helper methods for uploading directories ---------------------
    def _upload_directory_recursive(self, local_dir: str, remote_dir: str):
        """ส่งโฟลเดอร์ (และทุกไฟล์ย่อย) ไปยัง FTP แบบ recursive"""
        if self.ftp is None:
            return
        assert self.ftp is not None
        # สร้างโฟลเดอร์ปลายทาง (ถ้ายังไม่มี)
        try:
            self.ftp.mkd(remote_dir)
        except Exception:
            pass  # อาจมีอยู่แล้ว

        for root, dirs, files in os.walk(local_dir):
            rel_path = os.path.relpath(root, local_dir)
            remote_sub_dir = remote_dir if rel_path == '.' else f"{remote_dir}/{rel_path.replace(os.sep, '/')}"

            # สร้างโฟลเดอร์ย่อยใน FTP ตามโครงสร้าง
            try:
                self.ftp.mkd(remote_sub_dir)
            except Exception:
                pass

            for file in files:
                local_file_path = os.path.join(root, file)
                remote_file_path = f"{remote_sub_dir}/{file}"
                with open(local_file_path, 'rb') as fhd:
                    self.ftp.storbinary(f'STOR {remote_file_path}', fhd)
                    
    def download_file(self):
        if not self.connected:
            messagebox.showwarning("คำเตือน", "กรุณาเชื่อมต่อก่อน")
            return
            
        selection = self.remote_tree.selection()
        if not selection:
            messagebox.showwarning("คำเตือน", "กรุณาเลือกไฟล์ที่ต้องการดาวน์โหลด")
            return
            
        item_text = self.remote_tree.item(selection[0])["text"]
        if item_text.startswith("📁") or item_text == "..":
            messagebox.showwarning("คำเตือน", "ไม่สามารถดาวน์โหลดโฟลเดอร์ได้")
            return
            
        local_file = os.path.join(self.current_local_path, item_text)
        
        def download_thread():
            try:
                assert self.ftp is not None  # Safeguard
                
                with open(local_file, 'wb') as f:
                    self.ftp.retrbinary(f'RETR {item_text}', f.write)
                    
                self.log_message(f"ดาวน์โหลดสำเร็จ: {item_text}")
                self.root.after(0, self.refresh_local_files)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถดาวน์โหลดได้: {str(e)}"))
                self.log_message(f"ดาวน์โหลดล้มเหลว: {str(e)}")
                
        threading.Thread(target=download_thread, daemon=True).start()
        
    def delete_local_file(self):
        selection = self.local_tree.selection()
        if not selection:
            return
            
        item_text = self.local_tree.item(selection[0])["text"]
        if item_text == "..":
            return
            
        if messagebox.askyesno("ยืนยัน", f"ต้องการลบ '{item_text}' หรือไม่?"):
            try:
                item_path = os.path.join(self.current_local_path, item_text.replace("📁 ", ""))
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
                    
                self.refresh_local_files()
                self.log_message(f"ลบสำเร็จ: {item_text}")
                
            except Exception as e:
                messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถลบได้: {str(e)}")
                
    def delete_remote_file(self):
        if not self.connected:
            return
            
        selection = self.remote_tree.selection()
        if not selection:
            return
            
        item_text = self.remote_tree.item(selection[0])["text"]
        if item_text == "..":
            return
            
        if messagebox.askyesno("ยืนยัน", f"ต้องการลบ '{item_text}' หรือไม่?"):
            def delete_thread():
                try:
                    assert self.ftp is not None  # Safeguard
                    
                    if item_text.startswith("📁"):
                        dir_name = item_text[2:]
                        remote_base = self.current_remote_path.rstrip("/")
                        remote_path = f"{remote_base}/{dir_name}" if remote_base else dir_name
                        self._delete_remote_recursive(remote_path)
                    else:
                        self.ftp.delete(item_text)
                        
                    self.log_message(f"ลบสำเร็จ: {item_text}")
                    self.root.after(0, self.refresh_remote_files)
                    
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถลบได้: {str(e)}"))
                    
            threading.Thread(target=delete_thread, daemon=True).start()
            
    def create_local_folder(self):
        name = simpledialog.askstring("สร้างโฟลเดอร์", "ชื่อโฟลเดอร์:")
        if name:
            try:
                os.mkdir(os.path.join(self.current_local_path, name))
                self.refresh_local_files()
                self.log_message(f"สร้างโฟลเดอร์สำเร็จ: {name}")
            except Exception as e:
                messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถสร้างโฟลเดอร์ได้: {str(e)}")
                
    def create_remote_folder(self):
        if not self.connected:
            return
            
        name = simpledialog.askstring("สร้างโฟลเดอร์", "ชื่อโฟลเดอร์:")
        if name:
            def create_thread():
                try:
                    assert self.ftp is not None  # Safeguard
                    
                    self.ftp.mkd(name)
                    self.log_message(f"สร้างโฟลเดอร์สำเร็จ: {name}")
                    self.root.after(0, self.refresh_remote_files)
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถสร้างโฟลเดอร์ได้: {str(e)}"))
                    
            threading.Thread(target=create_thread, daemon=True).start()
            
    def refresh_all(self):
        self.refresh_local_files()
        if self.connected:
            self.refresh_remote_files()

    def load_configs(self):
        """อ่านไฟล์ ftp_configs.json ถ้ามี แล้วคืนค่าเป็น dict"""
        config_path = os.path.join(os.path.dirname(__file__), "ftp_configs.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            except Exception as e:
                print(f"Error loading config file: {e}")
        return {}

    def on_profile_selected(self, event=None):
        """เมื่อผู้ใช้เลือกโปรไฟล์ ให้เติมค่าลงในฟอร์ม"""
        profile_name = self.profile_var.get()
        cfg = self.configs.get(profile_name, {})
        if not cfg:
            return
        # Fill fields
        self.server_entry.delete(0, tk.END)
        self.server_entry.insert(0, cfg.get("host", ""))

        self.port_entry.delete(0, tk.END)
        self.port_entry.insert(0, str(cfg.get("port", "21")))

        self.user_entry.delete(0, tk.END)
        self.user_entry.insert(0, cfg.get("user", ""))

        self.pass_entry.delete(0, tk.END)
        self.pass_entry.insert(0, cfg.get("password", ""))

        # Set remote_dir if present, but we won't change cwd until connected
        self.current_remote_path = cfg.get("remote_dir", "/")

    # --------------------- Helper methods for deleting directories recursively ---------
    def _is_remote_dir(self, path: str) -> bool:
        if self.ftp is None:
            return False
        try:
            current = self.ftp.pwd()
            self.ftp.cwd(path)
            self.ftp.cwd(current)
            return True
        except Exception:
            return False

    def _delete_remote_recursive(self, remote_path: str):
        """ลบโฟลเดอร์บน FTP และทุกอย่างภายใน"""
        if self.ftp is None:
            return
        assert self.ftp is not None
        # รับรายการไฟล์/โฟลเดอร์ ภายใน
        try:
            entries = []
            try:
                # MLSD จะคืน (name, facts)
                entries = [ (name, facts.get('type', '')) for name, facts in self.ftp.mlsd(remote_path) ]
            except Exception:
                # NLST fallback
                entries = [ (name, '') for name in self.ftp.nlst(remote_path) ]

            for name, typ in entries:
                # ข้าม path ตัวเอง (mlsd อาจส่งกลับ '.')
                if name in ('.', '..') or name == remote_path:
                    continue

                child_path = f"{remote_path}/{name}" if not name.startswith(remote_path) else name

                is_dir = (typ == 'dir') if typ else self._is_remote_dir(child_path)

                if is_dir:
                    self._delete_remote_recursive(child_path)
                else:
                    try:
                        self.ftp.delete(child_path)
                    except Exception:
                        pass

            # ลบโฟลเดอร์หลังลบของข้างในเสร็จ
            try:
                self.ftp.rmd(remote_path)
            except Exception:
                pass
        except Exception as e:
            print(f"Error deleting remote dir: {e}")

if __name__ == "__main__":
    # Import simpledialog for folder navigation
    import tkinter.simpledialog
    
    root = tk.Tk()
    app = FTPClient(root)
    root.mainloop()