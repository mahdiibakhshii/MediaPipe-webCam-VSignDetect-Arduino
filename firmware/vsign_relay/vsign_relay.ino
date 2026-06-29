/*
 * VSign Detect — relay firmware
 * ----------------------------
 * Drives a relay from the Python host over a line-based serial protocol.
 * Supports two host modes (see agents/trigger-agent.md):
 *   - follow : host holds the relay ON/OFF to track a live victory sign.
 *   - pulse  : host fires a momentary pulse per debounced gesture.
 *
 * Protocol (ASCII lines, 115200 baud, '\n' terminated):
 *   board -> host : READY            (on boot, relay OFF)
 *   host  -> board: PING             ->  PONG
 *   host  -> board: ON               ->  OK ON    (relay held ON, follow mode)
 *   host  -> board: OFF              ->  OK OFF   (relay held OFF)
 *   host  -> board: FIRE             ->  OK FIRE  (momentary pulse, pulse mode)
 *                                    ->  BUSY     (if already pulsing or relay held ON)
 *   board -> host : DONE             (pulse finished, relay OFF)
 *
 * Wiring: RELAY_PIN -> relay module IN, 5V -> VCC, GND -> GND.
 * Set ACTIVE_LOW to match your relay module (many breakouts are active-LOW).
 */

const uint8_t  RELAY_PIN  = 7;      // digital pin to relay module IN
const bool     ACTIVE_LOW = false;  // true if the module switches ON when IN = LOW
const uint32_t PULSE_MS   = 2000;   // relay ON duration per FIRE pulse (ms)
const uint32_t BAUD       = 115200;

bool     relayOn    = false;  // current physical relay state
bool     held       = false;  // true when ON was commanded (follow mode)
bool     pulsing    = false;  // true during a FIRE pulse
uint32_t pulseStart = 0;
String   buf        = "";

void relayWrite(bool on) {
  // When ACTIVE_LOW, "on" means drive the pin LOW.
  bool level = on ? !ACTIVE_LOW : ACTIVE_LOW;
  digitalWrite(RELAY_PIN, level ? HIGH : LOW);
  relayOn = on;
}

void setup() {
  pinMode(RELAY_PIN, OUTPUT);
  relayWrite(false);          // fail-safe: OFF on boot
  Serial.begin(BAUD);
  delay(50);
  Serial.println("READY");
}

void handleCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();
  if (cmd.length() == 0) return;

  if (cmd == "PING") {
    Serial.println("PONG");
  } else if (cmd == "ON") {
    held = true;
    pulsing = false;          // a hold overrides any in-flight pulse
    relayWrite(true);
    Serial.println("OK ON");
  } else if (cmd == "OFF") {
    held = false;
    pulsing = false;
    relayWrite(false);
    Serial.println("OK OFF");
  } else if (cmd == "FIRE") {
    if (held || pulsing) {
      Serial.println("BUSY");
    } else {
      pulsing = true;
      pulseStart = millis();
      relayWrite(true);
      Serial.println("OK FIRE");
    }
  }
  // unknown commands are ignored
}

void loop() {
  // End a FIRE pulse without blocking.
  if (pulsing && (millis() - pulseStart >= PULSE_MS)) {
    relayWrite(false);
    pulsing = false;
    Serial.println("DONE");
  }

  // Read incoming lines.
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (buf.length() > 0) {
        handleCommand(buf);
        buf = "";
      }
    } else {
      buf += c;
      if (buf.length() > 32) buf = "";  // guard against runaway input
    }
  }
}
