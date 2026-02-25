#git clone 
import tkinter as tk
from tkinter import Label
import cv2
from picamera2 import Picamera2
import RPi.GPIO as GPIO
from gpiozero import LED, MotionSensor
import threading
import time
import sys

class StabilizedSecuritySystem:
    def __init__(self, window):
        self.window = window
        self.window.title("Stable Face Detection System")
        self.window.geometry("500x350")
        self.window.configure(bg='#121212')

        # --- GPIO Setup (Direct RPi.GPIO for Servo) ---
        self.pwm_pin = 13
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pwm_pin, GPIO.OUT)
        
        self.pwm = GPIO.PWM(self.pwm_pin, 50) 
        self.pwm.start(0) 
        
        # Ensure servo is at 0 degrees initially
        self.set_servo_angle(0)

        # --- Gpiozero for Sensors/LEDs ---
        self.red_led = LED(17)
        self.green_led = LED(27)
        self.pir = MotionSensor(25, pull_up=False)
        self.picam2 = Picamera2()
        
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # --- UI ---
        self.lbl_status = Label(window, text="SYSTEM ARMED", font=("Arial", 18), 
                                bg='#121212', fg='#3498db')
        self.lbl_status.pack(expand=True)
        
        self.is_processing = False
        self.window.protocol("WM_DELETE_WINDOW", self.cleanup)

        threading.Thread(target=self.monitor_pir, daemon=True).start()

    def set_servo_angle(self, angle):
        """Standard Servo Angle to Duty Cycle conversion with jitter protection."""
        duty = (angle / 18) + 2
        self.pwm.ChangeDutyCycle(duty)
        time.sleep(0.5)        
        self.pwm.ChangeDutyCycle(0) 

    def monitor_pir(self):
        while True:
            if self.pir.motion_detected and not self.is_processing:
                self.run_cycle()
            time.sleep(0.1)

    def run_cycle(self):
        self.is_processing = True
        self.lbl_status.config(text="MOTION DETECTED", fg="#f1c40f")
        
        # Servo stays at 0 initially (Already set, but ensuring state)
        # self.set_servo_angle(0) 

        try:
            # 1. Start Camera and Detection
            config = self.picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
            self.picam2.configure(config)
            self.picam2.start()
            self.green_led.on()

            face_found = False
            start_time = time.time()
            
            # 2. 10 Second Detection Window
            while time.time() - start_time < 10: 
                frame = self.picam2.capture_array()
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

                if len(faces) > 0:
                    face_found = True
                    break 
                
                cv2.imshow("Security Feed", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            # 3. Stop Camera immediately after result
            self.picam2.stop()
            cv2.destroyAllWindows()
            self.green_led.off()

            # 4. Logical Action based on detection
            if face_found:
                self.lbl_status.config(text="ACCESS GRANTED", fg="#2ecc71")
                print("Face Detected: Moving to 90 degrees...")
                self.set_servo_angle(90)
                time.sleep(3) # Wait 3 seconds as requested
                print("Returning to 0 degrees...")
                self.set_servo_angle(0)
            else:
                self.lbl_status.config(text="TIMEOUT: NO FACE", fg="#e74c3c")
                self.red_led.on()
                time.sleep(2)
                self.red_led.off()

        except Exception as e:
            print(f"Error: {e}")

        # 5. Anti-loop: Wait for PIR to go quiet
        while self.pir.motion_detected:
            time.sleep(0.5)
            
        self.lbl_status.config(text="SYSTEM ARMED", fg="#3498db")
        self.is_processing = False

    def cleanup(self):
        self.pwm.stop()
        GPIO.cleanup()
        self.picam2.close()
        cv2.destroyAllWindows()
        self.window.destroy()
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = StabilizedSecuritySystem(root)
    root.mainloop()
