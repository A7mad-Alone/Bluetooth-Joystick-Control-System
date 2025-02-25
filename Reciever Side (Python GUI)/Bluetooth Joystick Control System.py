import serial
import tkinter as tk
from tkinter import ttk
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
import threading
import time

# --- Constants and Global Variables ---
BLUETOOTH_PORT = 'COMX'  # Replace with your HC-05 COM port
BAUD_RATE = 9600
MOUSE_SENSITIVITY = 2  # Adjust as needed
FINE_ADJUSTMENT_ENABLED = False
MAX_SENSITIVITY = 2  # Maximum mouse sensitivity
MIN_SENSITIVITY = 0.5  # Initial low sensitivity (half the max sensitivity)
SENSITIVITY_INCREASE_DURATION = 10  # Duration (in seconds) to reach maximum sensitivity
CURRENT_SENSITIVITY = MIN_SENSITIVITY  # Current sensitivity starts at min_sensitivity

# GUI Initialization
root = tk.Tk()
root.title("Bluetooth Control System")
root.geometry("1000x1200")
root.configure(bg="lightblue")

# Serial Communication
ser = None
serial_thread_running = False
last_received_time = time.time()
is_connected = False
is_searching = True
disconnected_due_to_inactivity = False

# Control Flags
mouse_control = False
control_mode = "N/A"
active_keys = set()
action_taken = False  # Prevent repeated action
last_left_click_time = 0  # Track the last time a left-click was executed

# Arrow Key Delay for Slow Mode
last_arrow_key_time = {"up": 0, "down": 0, "left": 0, "right": 0}
ARROW_KEY_DELAY = 0.5  # Delay for slow arrow key mode

# Mouse and Keyboard Controllers
mouse = MouseController()
keyboard = KeyboardController()

# --- GUI Components ---

# Title Frame
title_frame = tk.Frame(root, bg="lightblue", pady=10)
title_frame.pack(fill=tk.X)
tk.Label(
    title_frame,
    text="Joystick Bluetooth Control System",
    font=("Arial", 16, "bold"),
    bg="lightblue"
).pack()

# Bluetooth Status Frame
bluetooth_frame = tk.Frame(root, bg="lightblue", pady=10)
bluetooth_frame.pack(fill=tk.X)

bluetooth_status_label = tk.Label(
    bluetooth_frame,
    text="Bluetooth: Not Connected",
    font=("Arial", 12),
    bg="lightblue",
    anchor="w"
)
bluetooth_status_label.pack(side=tk.LEFT, padx=20)

bluetooth_indicator = tk.Label(
    bluetooth_frame,
    width=2,
    height=1,
    bg="red",
    relief="sunken"
)
bluetooth_indicator.pack(side=tk.LEFT, padx=10)

# Control Mode and Status Frame
control_status_frame = tk.Frame(root, bg="lightblue", pady=10)
control_status_frame.pack(fill=tk.X)

control_mode_label = tk.Label(
    control_status_frame,
    text="Control Mode:",
    font=("Arial", 12),
    bg="lightblue"
)
control_mode_label.pack(side=tk.LEFT, padx=20)

control_mode_indicator = tk.Label(
    control_status_frame,
    text="Mouse",
    font=("Arial", 12),
    width=10,
    relief="groove",
    bg="yellow"
)
control_mode_indicator.pack(side=tk.LEFT, padx=10)

status_label = tk.Label(
    control_status_frame,
    text="Controlling:",
    font=("Arial", 12),
    bg="lightblue"
)
status_label.pack(side=tk.LEFT, padx=20)

status_indicator = tk.Label(
    control_status_frame,
    width=10,
    height=1,
    bg="red",
    relief="sunken",
    text="OFF",
    anchor="center",
    font=("Arial", 12)
)
status_indicator.pack(side=tk.LEFT, padx=10)

# LED Indicators Frame
led_frame = tk.Frame(root, bg="lightblue", pady=10)
led_frame.pack()

led_labels = {
    "up": tk.Label(led_frame, text="↑", font=("Arial", 14), width=5, height=2, bg="gray"),
    "down": tk.Label(led_frame, text="↓", font=("Arial", 14), width=5, height=2, bg="gray"),
    "left": tk.Label(led_frame, text="←", font=("Arial", 14), width=5, height=2, bg="gray"),
    "right": tk.Label(led_frame, text="→", font=("Arial", 14), width=5, height=2, bg="gray"),
    "action": tk.Label(led_frame, text="Action", font=("Arial", 14), width=5, height=2, bg="gray"),
}

led_labels["up"].grid(row=0, column=1, pady=5)
led_labels["left"].grid(row=1, column=0, padx=5)
led_labels["action"].grid(row=1, column=1, padx=5)
led_labels["right"].grid(row=1, column=2, padx=5)
led_labels["down"].grid(row=2, column=1, pady=5)

# Terminal Output Frame
output_frame = tk.Frame(root, bg="lightblue", pady=10)
output_frame.pack()

output_label = tk.Label(
    output_frame,
    text="Terminal Output:",
    font=("Arial", 12),
    bg="lightblue"
)
output_label.pack(anchor="w", padx=20)

output_text = tk.Text(output_frame, height=10, width=70)
output_text.pack()

clear_output_button = ttk.Button(
    output_frame,
    text="Clear Output",
    command=lambda: output_text.delete("1.0", tk.END)
)
clear_output_button.pack(pady=5)

# Options Frame
options_frame = tk.Frame(root, bg="lightblue", pady=10)
options_frame.pack()

show_messages_var = tk.BooleanVar(value=False)
ttk.Checkbutton(
    options_frame,
    text="Show Received Messages",
    variable=show_messages_var
).pack(side=tk.LEFT, padx=10)

slow_mode_var = tk.BooleanVar(value=True)
ttk.Checkbutton(
    options_frame,
    text="Slow Output Mode",
    variable=slow_mode_var
).pack(side=tk.LEFT, padx=10)

autoscroll_var = tk.BooleanVar(value=True)
ttk.Checkbutton(
    options_frame,
    text="Autoscroll",
    variable=autoscroll_var
).pack(side=tk.LEFT, padx=10)

fine_adjustment_var = tk.BooleanVar(value=False)
ttk.Checkbutton(
    options_frame,
    text="Enable Fine Adjustment",
    variable=fine_adjustment_var
).pack(side=tk.LEFT, padx=10)

slow_arrow_keys_var = tk.BooleanVar(value=False)
ttk.Checkbutton(
    options_frame,
    text="Enable Slow Arrow Keys",
    variable=slow_arrow_keys_var
).pack(side=tk.LEFT, padx=10)

# --- Functions ---

def initialize_serial():
    global ser, is_connected, is_searching
    try:
        ser = serial.Serial(BLUETOOTH_PORT, BAUD_RATE, timeout=5)
        log_message("Bluetooth connected.")
        bluetooth_status_label.config(text="Bluetooth: Connected")
        bluetooth_indicator.config(bg="green")
        reset_last_received_time()
        is_connected = True
        is_searching = False
    except serial.SerialException:
        searching_mode()

def searching_mode():
    global ser, is_connected, is_searching
    bluetooth_status_label.config(text="Bluetooth: Searching for HC-05 / Leonardo")
    bluetooth_indicator.config(bg="orange")
    close_serial_connection()
    ser = None
    is_connected = False
    is_searching = True

def close_serial_connection():
    global ser
    if ser:
        ser.close()

def reset_last_received_time():
    global last_received_time
    last_received_time = time.time()

def update_gui(mouse_status, mode):
    if mouse_status == "ON":
        status_indicator.config(bg="green", text="ON")
    else:
        status_indicator.config(bg="red", text="OFF")
    control_mode_indicator.config(text=mode if mode else "Mouse")

def log_message(message):
    output_text.insert(tk.END, message + "\n")
    if autoscroll_var.get():
        output_text.yview(tk.END)

def light_up_led(direction):
    if direction in led_labels:
        led_labels[direction].config(bg="green")
        root.after(500, lambda: led_labels[direction].config(bg="gray"))

def press_key(key):
    try:
        keyboard.press(key)
    except Exception as e:
        log_message(f"Error pressing key {key}: {e}")

def release_key(key):
    try:
        keyboard.release(key)
    except Exception as e:
        log_message(f"Error releasing key {key}: {e}")

def parse_data(data):
    try:
        parts = data.split(",")
        return tuple(part.strip() for part in parts)
    except ValueError:
        return None, None, None, None, None, None, None

def process_data(mouse_status, click_state, mode, x_movement, y_movement, x_direction, y_direction):
    global control_mode, mouse_control, action_taken, CURRENT_SENSITIVITY, fine_adjustment_start_time

    # Fine Adjustment Logic
    fine_adjustment_enabled = fine_adjustment_var.get()
    if fine_adjustment_enabled:
        if fine_adjustment_start_time is None:
            fine_adjustment_start_time = time.time()
        elapsed_time = time.time() - fine_adjustment_start_time
        CURRENT_SENSITIVITY = min_sensitivity + (max_sensitivity - min_sensitivity) * (elapsed_time / SENSITIVITY_INCREASE_DURATION)
        if elapsed_time >= SENSITIVITY_INCREASE_DURATION:
            CURRENT_SENSITIVITY = MAX_SENSITIVITY
    else:
        fine_adjustment_start_time = None
        CURRENT_SENSITIVITY = MAX_SENSITIVITY

    # Update Control Mode
    if mode != control_mode and mode in ["Mouse", "Arrow Keys"]:
        control_mode = mode
        log_message(f"Control mode changed to: {control_mode}")
        control_mode_indicator.config(text=control_mode, bg="yellow" if control_mode == "Mouse" else "green")

    update_gui(mouse_status, control_mode)

    # Handle Mouse Control
    if mouse_status == "ON" and not mouse_control:
        log_message("Controlling is ON.")
        mouse_control = True
    elif mouse_status == "OFF" and mouse_control:
        log_message("Controlling is OFF.")
        mouse_control = False

    if mouse_control:
        if control_mode == "Mouse":
            dx, dy = 0, 0
            if x_movement and x_movement != "null":
                dx = -CURRENT_SENSITIVITY * int(x_movement)
                light_up_led("left" if dx < 0 else "right")
            if y_movement and y_movement != "null":
                dy = -CURRENT_SENSITIVITY * int(y_movement)
                light_up_led("up" if dy < 0 else "down")
            if dx != 0 or dy != 0:
                mouse.move(dx, dy)

            if click_state == "PRESS" and not action_taken:
                action_taken = True
                light_up_led("action")
                mouse.press(Button.left)
            elif click_state == "RELEASE" and action_taken:
                mouse.release(Button.left)
                action_taken = False

        elif control_mode == "Arrow Keys":
            current_time = time.time()
            if slow_arrow_keys_var.get():
                if x_direction == "LEFT" and current_time - last_arrow_key_time["left"] > ARROW_KEY_DELAY:
                    press_key(Key.left)
                    light_up_led("left")
                    last_arrow_key_time["left"] = current_time
                elif x_direction == "RIGHT" and current_time - last_arrow_key_time["right"] > ARROW_KEY_DELAY:
                    press_key(Key.right)
                    light_up_led("right")
                    last_arrow_key_time["right"] = current_time
                if y_direction == "UP" and current_time - last_arrow_key_time["up"] > ARROW_KEY_DELAY:
                    press_key(Key.up)
                    light_up_led("up")
                    last_arrow_key_time["up"] = current_time
                elif y_direction == "DOWN" and current_time - last_arrow_key_time["down"] > ARROW_KEY_DELAY:
                    press_key(Key.down)
                    light_up_led("down")
                    last_arrow_key_time["down"] = current_time
            else:
                if x_direction == "LEFT":
                    press_key(Key.left)
                    light_up_led("left")
                elif x_direction == "RIGHT":
                    press_key(Key.right)
                    light_up_led("right")
                else:
                    release_key(Key.left)
                    release_key(Key.right)

                if y_direction == "UP":
                    press_key(Key.up)
                    light_up_led("up")
                elif y_direction == "DOWN":
                    press_key(Key.down)
                    light_up_led("down")
                else:
                    release_key(Key.up)
                    release_key(Key.down)

            if click_state == "PRESS" and not action_taken:
                action_taken = True
                light_up_led("action")
                keyboard.press(Key.enter)
            elif click_state == "RELEASE" and action_taken:
                keyboard.release(Key.enter)
                action_taken = False

def read_serial():
    while serial_thread_running:
        try:
            if ser and ser.is_open and ser.in_waiting > 0:
                raw_data = ser.readline().decode('utf-8').strip()
                reset_last_received_time()
                if show_messages_var.get() and (not slow_mode_var.get() or time.time() - last_received_time > 2):
                    log_message(f"Raw Data: {raw_data}")
                mouse_status, click_state, mode, x_movement, y_movement, x_direction, y_direction = parse_data(raw_data)
                if mouse_status and mode:
                    process_data(mouse_status, click_state, mode, x_movement, y_movement, x_direction, y_direction)
        except serial.SerialException:
            searching_mode()

def check_for_disconnect():
    global last_received_time, is_connected, disconnected_due_to_inactivity
    while serial_thread_running:
        if is_connected and time.time() - last_received_time > 5:
            if not is_searching:
                disconnected_due_to_inactivity = True
                log_message("Bluetooth disconnected due to inactivity. Re-entering searching mode...")
                searching_mode()
        time.sleep(1)

# --- Main Execution ---

if __name__ == "__main__":
    serial_thread = threading.Thread(target=read_serial, daemon=True)
    disconnect_thread = threading.Thread(target=check_for_disconnect, daemon=True)

    serial_thread.start()
    disconnect_thread.start()

    root.mainloop()

    if ser:
        ser.close()
    serial_thread_running = False