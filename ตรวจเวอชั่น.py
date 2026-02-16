# =================================================
# ตรวจสอบเวอร์ชันทั้งหมดที่โค้ดใช้
# =================================================

import sys
import os
import time
import threading
import datetime

import cv2
import numpy as np
import face_recognition
import mediapipe as mp
import pygame
from PIL import Image
import pillow_heif
import tensorflow as tf

print("==== Environment Versions ====")
print("Python:", sys.version)
print("OS module: built-in")
print("time module: built-in")
print("threading module: built-in")
print("datetime module: built-in")

print("\n==== Third-party Libraries ====")
print("numpy:", np.__version__)
print("opencv-python (cv2):", cv2.__version__)
print("face_recognition:", face_recognition.__version__)
print("mediapipe:", mp.__version__)
print("pygame:", pygame.version.ver)
print("Pillow:", Image.__version__)
print("pillow_heif:", pillow_heif.__version__)
print("tensorflow:", tf.__version__)
