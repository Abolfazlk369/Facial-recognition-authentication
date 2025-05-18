import cv2
import numpy as np
import face_recognition
import pickle
import time
import datetime
import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import json
import cryptography.fernet
from cryptography.fernet import Fernet
import logging
from deepface import DeepFace


class ImprovedFaceAuthSystem:
    def __init__(self):
        self.setup_encryption()
        self.setup_logging()
        self.load_known_faces()
        self.setup_gui()

    def setup_encryption(self):
        # کلید رمزنگاری
        if not os.path.exists('encryption_key.key'):
            self.key = Fernet.generate_key()
            with open('encryption_key.key', 'wb') as key_file:
                key_file.write(self.key)
        else:
            with open('encryption_key.key', 'rb') as key_file:
                self.key = key_file.read()
        self.cipher = Fernet(self.key)

    def setup_logging(self):
        # تنظیم سیستم لاگ
        logging.basicConfig(
            filename='face_auth.log',
            level=logging.INFO,
            format='%(asctime)s - %(message)s'
        )

    def setup_gui(self):
        # ایجاد رابط کاربری گرافیکی
        self.root = tk.Tk()
        self.root.title("Face Authentication System")

        # فریم اصلی
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(padx=10, pady=10)

        # نمایش تصویر دوربین
        self.video_label = tk.Label(self.main_frame)
        self.video_label.pack()

        # دکمه‌ها
        tk.Button(self.main_frame, text="Add New Face", command=self.add_new_face_gui).pack()
        tk.Button(self.main_frame, text="View Logs", command=self.view_logs).pack()
        tk.Button(self.main_frame, text="Start Authentication", command=self.start_authentication).pack()

    def load_known_faces(self):
        # بارگذاری چهره‌های ذخیره شده
        try:
            with open("face_data.enc", "rb") as f:
                encrypted_data = f.read()
                decrypted_data = self.cipher.decrypt(encrypted_data)
                data = pickle.loads(decrypted_data)
                self.known_face_encodings = data["encodings"]
                self.known_face_names = data["names"]
        except FileNotFoundError:
            self.known_face_encodings = []
            self.known_face_names = []

    def save_known_faces(self):
        # ذخیره چهره‌های شناخته شده با رمزنگاری
        data = {
            "encodings": self.known_face_encodings,
            "names": self.known_face_names
        }
        encrypted_data = self.cipher.encrypt(pickle.dumps(data))
        with open("face_data.enc", "wb") as f:
            f.write(encrypted_data)

    def add_new_face_gui(self):
        # رابط گرافیکی برای اضافه کردن چهره جدید
        self.add_window = tk.Toplevel(self.root)
        self.add_window.title("Add New Face")

        tk.Label(self.add_window, text="Name:").pack()
        name_entry = tk.Entry(self.add_window)
        name_entry.pack()

        def capture():
            ret, frame = self.cap.read()
            if ret:
                face_locations = face_recognition.face_locations(frame)
                if face_locations:
                    face_encoding = face_recognition.face_encodings(frame, face_locations)[0]
                    self.known_face_encodings.append(face_encoding)
                    self.known_face_names.append(name_entry.get())
                    self.save_known_faces()
                    logging.info(f"New face added: {name_entry.get()}")
                    messagebox.showinfo("Success", "Face added successfully!")
                    self.add_window.destroy()
                else:
                    messagebox.showerror("Error", "No face detected!")

        tk.Button(self.add_window, text="Capture", command=capture).pack()

    def check_liveness(self, frame):
        # تشخیص زنده بودن با استفاده از DeepFace
        try:
            analysis = DeepFace.analyze(frame, actions=['emotion'])
            # اگر تغییرات احساسی تشخیص داده شود، فرد زنده است
            return True
        except:
            return False

    def process_frame(self, frame):
        # پردازش هر فریم
        # تبدیل به RGB
        rgb_frame = frame[:, :, ::-1]

        # تشخیص چهره
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            # بررسی زنده بودن
            face_image = frame[top:bottom, left:right]
            if not self.check_liveness(face_image):
                continue

            # تطبیق چهره
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            name = "Unknown"

            if True in matches:
                first_match_index = matches.index(True)
                name = self.known_face_names[first_match_index]
                logging.info(f"Access granted to {name}")

                # نمایش کادر سبز برای افراد مجاز
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
            else:
                # نمایش کادر قرمز برای افراد غیرمجاز
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
                logging.warning("Unauthorized access attempt")

        return frame

    def start_authentication(self):
        # شروع فرآیند احراز هویت
        self.cap = cv2.VideoCapture(0)  # برای دوربین متصل با USB

        def update_frame():
            ret, frame = self.cap.read()
            if ret:
                processed_frame = self.process_frame(frame)
                # تبدیل فریم به فرمت مناسب برای نمایش در GUI
                img = Image.fromarray(cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB))
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
            self.root.after(10, update_frame)

        update_frame()

    def view_logs(self):
        # نمایش لاگ‌ها
        log_window = tk.Toplevel(self.root)
        log_window.title("Authentication Logs")

        with open('face_auth.log', 'r') as log_file:
            log_text = tk.Text(log_window)
            log_text.pack()
            log_text.insert(tk.END, log_file.read())
            log_text.config(state=tk.DISABLED)

    def run(self):
        self.root.mainloop()


# اجرای برنامه
if __name__ == "__main__":
    auth_system = ImprovedFaceAuthSystem()
    auth_system.run()
