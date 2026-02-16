import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys

# ================= CONFIG PATH =================
# ระบุตำแหน่งโฟลเดอร์ตามที่คุณแจ้งมา
BASE_PATH = r"C:\Users\patip\OneDrive\Desktop\ject4"
# ไฟล์ระบบกล้องวงจรปิด (Detect ใบหน้า)
APP_1_PATH = os.path.join(BASE_PATH, "กล้องวงจรปิด.py")
# ไฟล์ระบบลงทะเบียน (ถ่ายรูป)
APP_2_PATH = os.path.join(BASE_PATH, "ลงทะเบียน.py")

# Palette สี Security Dashboard
COLOR_BG = "#020617"      # ดำลึก (Deep Space)
COLOR_CARD = "#0f172a"    # น้ำเงินเข้ม (Navy)
COLOR_ACCENT = "#38bdf8"  # ฟ้าสว่าง (Electric Blue)
COLOR_SUCCESS = "#22c55e" # เขียว (Security Active)
COLOR_DANGER = "#ef4444"  # แดง (Alert/Close)
COLOR_TEXT = "#f8fafc"    # ขาวนวล

class SecurityControlCenter:
    def __init__(self, root):
        self.root = root
        self.root.title("AI FACE RECOGNITION SYSTEM")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg=COLOR_BG)
        
        self.process = None
        self.setup_ui()

    def setup_ui(self):
        # --- แถบบน (Header Bar) ---
        top_bar = tk.Frame(self.root, bg=COLOR_CARD, height=60)
        top_bar.pack(fill="x", side="top")
        
        tk.Label(top_bar, text="🛡️ AI SECURITY CONTROL CENTER v3.0", 
                 font=("Consolas", 14, "bold"), bg=COLOR_CARD, fg=COLOR_ACCENT).pack(side="left", padx=30)
        
        # ปุ่มกากบาทสีแดง
        btn_close = tk.Button(top_bar, text=" ✕ CLOSE SYSTEM ", font=("Arial", 11, "bold"), 
                             bg=COLOR_DANGER, fg="white", bd=0, padx=15, cursor="hand2",
                             command=self.exit_system)
        btn_close.pack(side="right", padx=20, pady=10)

        # --- ส่วนกลาง (Main Content) ---
        main_frame = tk.Frame(self.root, bg=COLOR_BG)
        main_frame.place(relx=0.5, rely=0.5, anchor="center")

        # ส่วนหัวข้อใหญ่
        tk.Label(main_frame, text="OPERATIONAL MODES", font=("Tahoma", 52, "bold"), 
                 bg=COLOR_BG, fg=COLOR_TEXT).pack(pady=(0, 5))
        tk.Label(main_frame, text="เลือกโหมดเพื่อเริ่มต้นการทำงานของระบบ", font=("Tahoma", 16), 
                 bg=COLOR_BG, fg="#64748b").pack(pady=(0, 40))

        # เส้นแบ่ง
        tk.Frame(main_frame, height=2, width=600, bg="#1e293b").pack(pady=10)

        # สไตล์ปุ่ม
        btn_style = {
            "font": ("Tahoma", 20, "bold"),
            "width": 35,
            "height": 3,
            "relief": "flat",
            "cursor": "hand2",
            "bd": 0,
            "highlightthickness": 1,
            "highlightbackground": "#334155"
        }

        # ปุ่ม 1: ระบบกล้องวงจรปิด
        self.btn1 = tk.Button(main_frame, text="🎥 เปิดระบบกล้องวงจรปิด\n(Face Detection Monitor)", 
                              bg=COLOR_CARD, fg=COLOR_ACCENT, **btn_style,
                              command=lambda: self.run_app(APP_1_PATH))
        self.btn1.pack(pady=20)
        self.btn1.bind("<Enter>", lambda e: self.btn1.config(bg="#1e293b", highlightbackground=COLOR_ACCENT))
        self.btn1.bind("<Leave>", lambda e: self.btn1.config(bg=COLOR_CARD, highlightbackground="#334155"))

        # ปุ่ม 2: ระบบลงทะเบียน
        self.btn2 = tk.Button(main_frame, text="👤 ลงทะเบียนใบหน้าใหม่\n(Face Registration System)", 
                              bg=COLOR_CARD, fg=COLOR_SUCCESS, **btn_style,
                              command=lambda: self.run_app(APP_2_PATH))
        self.btn2.pack(pady=20)
        self.btn2.bind("<Enter>", lambda e: self.btn2.config(bg="#1e293b", highlightbackground=COLOR_SUCCESS))
        self.btn2.bind("<Leave>", lambda e: self.btn2.config(bg=COLOR_CARD, highlightbackground="#334155"))

        # แถบล่าง (Footer)
        tk.Label(self.root, text="STATUS: READY | ENCRYPTED CONNECTION", font=("Consolas", 10), 
                 bg=COLOR_BG, fg="#475569").pack(side="bottom", pady=30)

        self.root.bind("<Escape>", lambda e: self.exit_system())

    def run_app(self, file_path):
        if not os.path.exists(file_path):
            messagebox.showerror("System Error", f"ไม่พบไฟล์ระบบ:\n{file_path}")
            return

        if self.process and self.process.poll() is None:
            messagebox.showwarning("System Active", "กรุณาปิดหน้าต่างระบบเดิมก่อนเปิดใหม่")
            return

        try:
            self.root.withdraw() # ซ่อนหน้าหลัก
            # สั่งรันแอปย่อย
            self.process = subprocess.Popen([sys.executable, file_path], cwd=BASE_PATH)
            self.check_process()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.root.deiconify()

    def check_process(self):
        if self.process and self.process.poll() is not None:
            self.root.deiconify() # กลับหน้าหลักอัตโนมัติเมื่อแอปย่อยถูกปิด
        else:
            self.root.after(500, self.check_process)

    def exit_system(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SecurityControlCenter(root)
    root.mainloop()