import cv2
import os
import numpy as np
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont

# ================= CONFIG =================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(CURRENT_DIR, "images")
CAMERA_INDEX = 0

COLOR_BG = "#020617"       
COLOR_CARD = "#1e293b"     
COLOR_ACCENT = "#38bdf8"   
COLOR_SUCCESS = "#10b981"  
COLOR_DANGER = "#e11d48"   
COLOR_TEXT = "#f8fafc"     

ANGLES_TH = [
    "หน้าตรง", "หันซ้าย", "หันขวา", 
    "เงยหน้า", "ก้มหน้า", "ยิ้ม", 
    "เอียงซ้าย", "เอียงขวา", "หลับตา", "หน้านิ่ง"
]

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR, exist_ok=True)

class FaceCaptureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Face Registration System")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg=COLOR_BG)

        self.cap = None
        self.person_name = ""
        self.image_count = 0
        
        try:
            self.font_path = "C:/Windows/Fonts/tahoma.ttf"
            self.thai_font_lg = ImageFont.truetype(self.font_path, 50) # ฟอนต์ขนาดใหญ่พิเศษ
        except:
            self.thai_font_lg = ImageFont.load_default()

        self.build_name_page()
        self.root.bind("<Escape>", lambda e: self.exit_app())

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def build_name_page(self):
        self.clear_window()
        
        header_bar = tk.Frame(self.root, bg="#0f172a", height=60)
        header_bar.pack(fill="x")
        
        btn_top_exit = tk.Button(header_bar, text=" ปิดโปรแกรม ✕ ", font=("Tahoma", 11, "bold"), 
                                 bg=COLOR_DANGER, fg="white", relief="flat", bd=0, 
                                 padx=15, cursor="hand2", command=self.exit_app)
        btn_top_exit.pack(side="right", padx=20, pady=10)

        container = tk.Frame(self.root, bg=COLOR_BG)
        container.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(container, text="FACE REGISTRATION", bg=COLOR_BG, fg=COLOR_ACCENT, 
                 font=("Verdana", 50, "bold")).pack(pady=(0, 5))
                 
        tk.Label(container, text="ระบบลงทะเบียนใบหน้าอัตโนมัติ", bg=COLOR_BG, fg="#64748b", 
                 font=("Tahoma", 18)).pack(pady=(0, 40))

        card = tk.Frame(container, bg=COLOR_CARD, padx=60, pady=60, 
                        highlightbackground="#334155", highlightthickness=2)
        card.pack()

        tk.Label(card, text="กรุณากรอกชื่อ-นามสกุล (English Only)", bg=COLOR_CARD, fg=COLOR_TEXT, 
                 font=("Tahoma", 14, "bold")).pack(anchor="w", pady=(0, 15))

        self.name_entry = tk.Entry(card, font=("Tahoma", 24), bg="#0f172a", fg="white", 
                                   insertbackground=COLOR_ACCENT, borderwidth=0, 
                                   highlightthickness=1, highlightbackground="#334155",
                                   justify="center", width=22)
        self.name_entry.pack(pady=(0, 40), ipady=12)
        self.name_entry.focus_set()
        self.name_entry.bind("<Return>", lambda e: self.start_camera())

        btn_start = tk.Button(card, text="เริ่มขั้นตอนบันทึกภาพ", font=("Tahoma", 16, "bold"), 
                              bg=COLOR_ACCENT, fg="#020617", relief="flat", width=30, height=2, 
                              cursor="hand2", command=self.start_camera)
        btn_start.pack(pady=10)
        
        btn_cancel = tk.Button(card, text="ยกเลิกการลงทะเบียน", font=("Tahoma", 12), 
                               bg=COLOR_DANGER, fg="white", relief="flat", width=30, height=1, 
                               cursor="hand2", command=self.exit_app)
        btn_cancel.pack(pady=5)

    def build_camera_page(self):
        self.clear_window()
        
        # Header (แคบลงเพื่อให้พื้นที่ภาพมากขึ้น)
        header = tk.Frame(self.root, bg="#0f172a", height=60)
        header.pack(fill="x")
        
        tk.Label(header, text=f"🔴 ผู้ลงทะเบียน: {self.person_name}", bg="#0f172a", fg=COLOR_TEXT, 
                 font=("Tahoma", 16, "bold")).place(relx=0.02, rely=0.5, anchor="w")
        
        btn_top_exit = tk.Button(header, text=" ยกเลิก/ออก ✕ ", font=("Tahoma", 10, "bold"), 
                                 bg=COLOR_DANGER, fg="white", relief="flat", padx=15, 
                                 cursor="hand2", command=self.exit_app)
        btn_top_exit.place(relx=0.98, rely=0.5, anchor="e")

        # Camera Display (ขยายพื้นที่เต็มที่)
        video_frame = tk.Frame(self.root, bg=COLOR_BG)
        video_frame.pack(expand=True, fill="both", padx=10, pady=5)

        self.video_label = tk.Label(video_frame, bg="black")
        self.video_label.pack(expand=True, fill="both")

        # Footer Area (ส่วนเก็บคำสั่งที่ไม่อยู่บนภาพ)
        footer = tk.Frame(self.root, bg="#0f172a", height=180)
        footer.pack(fill="x", side="bottom")

        # ย้ายคำสั่งมาไว้ที่ Footer เพื่อความชัดเจน ไม่บังใบหน้า
        self.instruction_label = tk.Label(footer, text="", bg="#0f172a", fg="white", 
                                          font=("Tahoma", 32, "bold"))
        self.instruction_label.pack(pady=(10, 0))

        self.progress_label = tk.Label(footer, text="", bg="#0f172a", fg=COLOR_ACCENT, 
                                      font=("Tahoma", 14))
        self.progress_label.pack()

        self.btn_capture = tk.Button(footer, text="กดถ่ายภาพ (SPACE)", font=("Tahoma", 20, "bold"), 
                                     bg=COLOR_SUCCESS, fg="white", relief="flat", width=25, height=2, 
                                     cursor="hand2", command=self.capture_image)
        self.btn_capture.pack(pady=10)
        
        self.root.bind("<space>", lambda e: self.capture_image())
        self.update_camera()

    def start_camera(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("ข้อผิดพลาด", "กรุณาระบุชื่อผู้ลงทะเบียน")
            return

        self.person_name = name
        self.person_dir = os.path.join(BASE_DIR, name)
        
        try:
            if not os.path.exists(self.person_dir):
                os.makedirs(self.person_dir, exist_ok=True)
                
            self.cap = cv2.VideoCapture(CAMERA_INDEX)
            # ขอความละเอียดสูงสุด
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            
            if not self.cap.isOpened(): raise Exception("ไม่พบการเชื่อมต่อกล้อง")
            self.build_camera_page()
        except Exception as e:
            messagebox.showerror("System Error", str(e))

    def update_camera(self):
        if self.cap is None: return
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            
            cv2_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(cv2_img)
            draw = ImageDraw.Draw(pil_img)
            
            # วาด Oval Guide (วงรีใบหน้า) แบบโปร่งแสง
            center = (w // 2, h // 2)
            axes = (int(w * 0.18), int(h * 0.35))
            draw.ellipse([center[0]-axes[0], center[1]-axes[1], center[0]+axes[0], center[1]+axes[1]], 
                         outline=COLOR_ACCENT, width=5)

            # อัปเดตข้อความคำสั่งที่ Footer (ไม่ให้ไปทับบนหน้าคน)
            if self.image_count < len(ANGLES_TH):
                msg = f"ท่าทาง: {ANGLES_TH[self.image_count]}"
                self.instruction_label.config(text=msg, fg=COLOR_TEXT)
                self.progress_label.config(text=f"ขั้นตอนที่ {self.image_count + 1} จาก {len(ANGLES_TH)}")
            else:
                self.instruction_label.config(text="บันทึกข้อมูลสำเร็จ!", fg=COLOR_SUCCESS)
                self.btn_capture.config(state="disabled", text="เสร็จสิ้น", bg="#475569")

            # ปรับขนาดภาพให้ใหญ่ที่สุดตามขนาดจอ
            screen_h = self.root.winfo_screenheight() - 250 # กันพื้นที่ให้ Footer
            aspect_ratio = w / h
            new_w = int(screen_h * aspect_ratio)
            
            pil_img = pil_img.resize((new_w, screen_h), Image.Resampling.LANCZOS)
            
            imgtk = ImageTk.PhotoImage(image=pil_img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

        self.root.after(10, self.update_camera)

    def capture_image(self):
        if self.image_count >= len(ANGLES_TH): 
            messagebox.showinfo("Success", "บันทึกอัตลักษณ์เรียบร้อยแล้ว")
            self.build_name_page()
            return

        ret, frame = self.cap.read()
        if not ret: return

        angle_name = ANGLES_TH[self.image_count]
        file_name = f"{self.person_name}_{angle_name}.jpg"
        save_path = os.path.join(self.person_dir, file_name)
        
        is_success, im_buf_arr = cv2.imencode(".jpg", frame)
        if is_success:
            im_buf_arr.tofile(save_path)
            self.image_count += 1
            
            # Effect แฟลช
            flash = tk.Frame(self.root, bg="white")
            flash.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.root.after(50, flash.destroy)
        else:
            messagebox.showerror("Error", "ไม่สามารถบันทึกภาพได้")

    def exit_app(self):
        if self.cap: self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = FaceCaptureApp(root)
    root.mainloop()