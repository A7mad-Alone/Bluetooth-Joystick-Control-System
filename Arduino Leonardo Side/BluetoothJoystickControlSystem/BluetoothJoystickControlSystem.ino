/*
 Bluetooth Joystick Controller 
  This program allows a joystick to control mouse movements or arrow keys via Bluetooth.
  It supports two modes: Mouse mode and Arrow Keys mode.
*/

// Libraries
#include <Wire.h>
#include <SoftwareSerial.h>
#include <Mouse.h>
#include <avr/wdt.h>

// Bluetooth Communication Pins
const int BLUETOOTH_RX_PIN = 10;
const int BLUETOOTH_TX_PIN = 11;

// Button and Switch Pins
const int SWITCH_PIN = 2;          // Toggle mouse control
const int MODE_BUTTON_PIN = 3;     // Mode switching button
const int MOUSE_BUTTON_PIN = 7;    // Pushbutton for left-click (In Mouse Mode) or Enter (In Arrow Keys Mode)

// Joystick Pins
const int JOYSTICK_X_AXIS_PIN = A0;
const int JOYSTICK_Y_AXIS_PIN = A1;

// LED Pins
const int CONTROL_LED_PIN = 5;     // LED to indicate control state (On or Off)
const int MOUSE_MODE_LED_PIN = 6;  // LED for Mouse mode
const int ARROW_KEYS_LED_PIN = 8;  // LED for Arrow Keys mode

// Joystick Calibration Constants
const int JOYSTICK_RANGE = 5;      // Output range of X or Y movement
const int JOYSTICK_THRESHOLD = JOYSTICK_RANGE / 2; // Resting threshold for joystick
const int JOYSTICK_NEUTRAL_CENTER_X = 425; // Center value for the X-axis
const int JOYSTICK_NEUTRAL_CENTER_Y = 440; // Center value for the Y-axis
const int JOYSTICK_DEAD_ZONE = 15; // Dead zone around the center

// Speed Management Constants
const unsigned long SPEED_INCREASE_INTERVAL = 500; // Increase speed every 500ms
const int MAX_SPEED = JOYSTICK_RANGE;
const int MIN_SPEED = JOYSTICK_RANGE / 2;

// Modes
enum Mode { MOUSE, ARROW_KEYS };
Mode currentMode = MOUSE;

// States
bool mouseIsActive = false;       // Whether mouse control is active
int lastSwitchState = HIGH;       // Previous switch state
int lastModeButtonState = HIGH;   // Previous mode button state
bool mouseClicked = false;        // State of the mouse click

// Axis State Structure
struct AxisState {
  int speed;
  unsigned long lastMovementTime;
};
AxisState xState = {MIN_SPEED, 0};
AxisState yState = {MIN_SPEED, 0};

// Initialization
void setup() {
  Serial.begin(9600);
  SoftwareSerial Bluetooth(BLUETOOTH_RX_PIN, BLUETOOTH_TX_PIN); // RX, TX
  Bluetooth.begin(9600);

  // Pin configuration
  pinMode(SWITCH_PIN, INPUT_PULLUP);
  pinMode(MODE_BUTTON_PIN, INPUT_PULLUP);
  pinMode(MOUSE_BUTTON_PIN, INPUT_PULLUP);
  pinMode(CONTROL_LED_PIN, OUTPUT);
  pinMode(MOUSE_MODE_LED_PIN, OUTPUT);
  pinMode(ARROW_KEYS_LED_PIN, OUTPUT);

  // Initialize Mouse control
  Mouse.begin();
  digitalWrite(MOUSE_MODE_LED_PIN, HIGH); // Default to Mouse mode
}

// Main Loop
void loop() {
  handleModeSwitch();    // Handle mode switching
  handleMouseToggle();   // Toggle mouse control
  handleMouseClick();    // Handle mouse clicks or Enter key
  sendControlData();     // Send control data via Bluetooth
  delay(5);              // Small delay for stability
}

// Toggle Mouse Control
void handleMouseToggle() {
  int switchState = digitalRead(SWITCH_PIN);
  if (switchState != lastSwitchState && switchState == LOW) {
    mouseIsActive = !mouseIsActive;
    digitalWrite(CONTROL_LED_PIN, mouseIsActive ? HIGH : LOW); // Update control state LED
    Serial.println(mouseIsActive ? "Mouse Control: ON" : "Mouse Control: OFF");
  }
  lastSwitchState = switchState;
}

// Handle Mode Switching
void handleModeSwitch() {
  int modeButtonState = digitalRead(MODE_BUTTON_PIN);
  if (modeButtonState != lastModeButtonState && modeButtonState == LOW) {
    currentMode = static_cast<Mode>((currentMode + 1) % 2); // Cycle between modes
    Serial.println("Mode switched to: " + String(currentMode == MOUSE ? "Mouse" : "Arrow Keys"));
    updateModeLEDs(); // Update mode indicator LEDs
  }
  lastModeButtonState = modeButtonState;
}

// Handle Mouse Click or Enter Key
void handleMouseClick() {
  int mouseButtonReading = digitalRead(MOUSE_BUTTON_PIN);

  if (currentMode == MOUSE) {
    if (mouseButtonReading == LOW && !mouseClicked) {
      Mouse.press(); // Press left mouse button
      mouseClicked = true;
    } else if (mouseButtonReading == HIGH && mouseClicked) {
      Mouse.release(); // Release left mouse button
      mouseClicked = false;
    }
  } else if (currentMode == ARROW_KEYS) {
    if (mouseButtonReading == LOW && !mouseClicked) {
      Serial.println("Enter Key Pressed"); // Simulate Enter key press
      mouseClicked = true;
    } else if (mouseButtonReading == HIGH && mouseClicked) {
      mouseClicked = false;
    }
  }
}

// Read Axis and Map to Movement
int readAxis(int axisPin, int neutralCenter, AxisState &state) {
  int reading = analogRead(axisPin);

  if (abs(reading - neutralCenter) < JOYSTICK_DEAD_ZONE) {
    state.speed = MIN_SPEED; // Reset speed in the dead zone
    state.lastMovementTime = millis(); // Reset timer
    return 0;
  }

  int movementDirection = (reading - neutralCenter > 0) ? 1 : -1;

  // Gradually increase speed if direction remains the same
  if (millis() - state.lastMovementTime >= SPEED_INCREASE_INTERVAL) {
    state.speed = min(state.speed + 1, MAX_SPEED);
    state.lastMovementTime = millis();
  }

  int mappedValue = map(reading, 6, 865, -state.speed, state.speed);
  mappedValue = constrain(mappedValue, -state.speed, state.speed);
  return movementDirection * abs(mappedValue); // Ensure correct direction
}

// Send Structured Data via Bluetooth
void sendControlData() {
  String controlState = mouseIsActive ? "ON" : "OFF"; // Control state
  String clickState = mouseClicked ? "PRESS" : "RELEASE"; // Mouse click state
  String controlMode = currentMode == MOUSE ? "Mouse" : "Arrow Keys"; // Current mode

  String xMovementMouse = "null";
  String yMovementMouse = "null";
  String xDirectionArrow = "null";
  String yDirectionArrow = "null";

  if (currentMode == MOUSE && mouseIsActive) {
    xMovementMouse = String(readAxis(JOYSTICK_X_AXIS_PIN, JOYSTICK_NEUTRAL_CENTER_X, xState));
    yMovementMouse = String(readAxis(JOYSTICK_Y_AXIS_PIN, JOYSTICK_NEUTRAL_CENTER_Y, yState));

    // Move the mouse
    Mouse.move(xMovementMouse.toInt(), yMovementMouse.toInt());
  } else if (currentMode == ARROW_KEYS && mouseIsActive) {
    int xReading = analogRead(JOYSTICK_X_AXIS_PIN);
    int yReading = analogRead(JOYSTICK_Y_AXIS_PIN);

    if (xReading < 300) xDirectionArrow = "LEFT";
    else if (xReading > 650) xDirectionArrow = "RIGHT";

    if (yReading < 300) yDirectionArrow = "UP";
    else if (yReading > 650) yDirectionArrow = "DOWN";
  }

  // Create and send the data packet
  String dataPacket = controlState + "," + clickState + "," + controlMode + "," +
                      xMovementMouse + "," + yMovementMouse + "," +
                      xDirectionArrow + "," + yDirectionArrow;

  SoftwareSerial Bluetooth(BLUETOOTH_RX_PIN, BLUETOOTH_TX_PIN);
  Bluetooth.println(dataPacket);
  Serial.println(dataPacket);
}

// Update Mode Indicator LEDs
void updateModeLEDs() {
  digitalWrite(MOUSE_MODE_LED_PIN, LOW);
  digitalWrite(ARROW_KEYS_LED_PIN, LOW);

  if (currentMode == MOUSE) {
    digitalWrite(MOUSE_MODE_LED_PIN, HIGH);
  } else if (currentMode == ARROW_KEYS) {
    digitalWrite(ARROW_KEYS_LED_PIN, HIGH);
  }
}