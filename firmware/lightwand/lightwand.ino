#include <WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <FastLED.h>

// ========================================================
// Wi-Fi
// ========================================================
#include "secrets.h"

const char* ssid = WIFI_SSID;
const char* password = WIFI_PASSWORD;

// ========================================================
// LED setup
// ========================================================

#define LED_PIN     27
#define NUM_LEDS    100
#define BRIGHTNESS  60
#define LED_TYPE    WS2812B
#define COLOR_ORDER GRB

CRGB leds[NUM_LEDS];

// ========================================================
// UDP streaming
// ========================================================

WiFiUDP udp;

const uint16_t UDP_PORT = 7777;
const int FRAME_BYTES = NUM_LEDS * 3;

uint8_t packetBuffer[FRAME_BYTES];

// ========================================================
// Timing / state
// ========================================================

unsigned long lastStatusPrint = 0;
unsigned long lastReconnectAttempt = 0;

const unsigned long RECONNECT_INTERVAL = 5000;

bool wasConnected = false;

// ========================================================
// LED helpers
// ========================================================

void clearLEDs() {
  fill_solid(leds, NUM_LEDS, CRGB::Black);
  FastLED.show();
}

void flashColor(CRGB color, int durationMs) {
  fill_solid(leds, NUM_LEDS, color);
  FastLED.show();
  delay(durationMs);
  clearLEDs();
}

void blueStartupSweep() {

  clearLEDs();

  for (int i = 0; i < NUM_LEDS; i++) {
    leds[i] = CRGB::Blue;
    FastLED.show();
    delay(8);
  }

  delay(300);
  clearLEDs();
}

// ========================================================
// Start / restart UDP
// ========================================================

void startUDP() {

  udp.stop();
  delay(50);

  if (udp.begin(UDP_PORT)) {
    Serial.print("UDP listening on port ");
    Serial.println(UDP_PORT);
  } else {
    Serial.println("ERROR: UDP failed to start");
  }
}

// ========================================================
// Wi-Fi event handler
// ========================================================

void onWiFiEvent(WiFiEvent_t event, WiFiEventInfo_t info) {

  if (event == ARDUINO_EVENT_WIFI_STA_CONNECTED) {

    Serial.println("WiFi event: Connected to access point");

  }

  else if (event == ARDUINO_EVENT_WIFI_STA_GOT_IP) {

    Serial.print("WiFi event: Got IP: ");
    Serial.println(WiFi.localIP());

  }

  else if (event == ARDUINO_EVENT_WIFI_STA_DISCONNECTED) {

    uint8_t reason = info.wifi_sta_disconnected.reason;

    Serial.print("WiFi event: DISCONNECTED. Reason = ");
    Serial.print(reason);
    Serial.print(" - ");

    Serial.println(
      WiFi.STA.disconnectReasonName(
        (wifi_err_reason_t)reason
      )
    );
  }
}

// ========================================================
// Connect to Wi-Fi at startup
// ========================================================

void connectWiFi() {

  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  // Give ESP32 / router a moment after startup
  delay(3000);

  // Clean up any previous station state
  WiFi.disconnect(false);
  delay(500);
  WiFi.begin(ssid, password);

  unsigned long attemptStart = millis();

  // First attempt: give it 12 seconds
  while (
    WiFi.status() != WL_CONNECTED &&
    millis() - attemptStart < 12000
  ) {
    delay(500);
    Serial.print(".");
  }

  // If first attempt failed, explicitly try again
  if (WiFi.status() != WL_CONNECTED) {

    Serial.println();
    Serial.println("First Wi-Fi attempt failed.");
    Serial.println("Trying again...");

    WiFi.disconnect(false);
    delay(2000);

    WiFi.begin(ssid, password);

    attemptStart = millis();

    while (
      WiFi.status() != WL_CONNECTED &&
      millis() - attemptStart < 15000
    ) {
      delay(500);
      Serial.print(".");
    }
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {

    Serial.println("Wi-Fi CONNECTED!");

    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());

    Serial.print("Signal strength: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");

    wasConnected = true;

  } else {

    Serial.println("Wi-Fi connection failed.");
    Serial.println("Firmware will keep retrying.");
    wasConnected = false;
  }
}

// ========================================================
// Setup
// ========================================================

void setup() {

  Serial.begin(115200);
  delay(500);

  Serial.println();
  Serial.println("============================");
  Serial.println("Light Wand starting...");
  Serial.println("============================");

  // ------------------------------------------------------
  // LEDs
  // ------------------------------------------------------

  FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(
    leds,
    NUM_LEDS
  );

  FastLED.setBrightness(BRIGHTNESS);

  // Blue = board booted / LEDs working
  blueStartupSweep();

  // ------------------------------------------------------
  // Wi-Fi configuration
  // ------------------------------------------------------

  WiFi.mode(WIFI_STA);

  // Important for real-time UDP streaming
  WiFi.setSleep(false);

  // Allow ESP32 Wi-Fi stack to reconnect automatically
  WiFi.setAutoReconnect(true);

  // Diagnostic event reporting
  WiFi.onEvent(onWiFiEvent);

  // Initial connection
  connectWiFi();

  // ------------------------------------------------------
  // OTA
  // ------------------------------------------------------

  ArduinoOTA.setHostname("lightwand");
  ArduinoOTA.setPort(3232);
  ArduinoOTA.setPassword("wandota");

  ArduinoOTA.onStart([]() {

    Serial.println();
    Serial.println("OTA update starting...");

    clearLEDs();
  });

  ArduinoOTA.onEnd([]() {

    Serial.println();
    Serial.println("OTA update complete.");
  });

  ArduinoOTA.onProgress(
    [](unsigned int progress, unsigned int total) {

      Serial.printf(
        "OTA progress: %u%%\r",
        (progress * 100) / total
      );
    }
  );

  ArduinoOTA.onError([](ota_error_t error) {

    Serial.printf("OTA Error [%u]: ", error);

    if (error == OTA_AUTH_ERROR) {
      Serial.println("Authentication failed");
    }
    else if (error == OTA_BEGIN_ERROR) {
      Serial.println("Begin failed");
    }
    else if (error == OTA_CONNECT_ERROR) {
      Serial.println("Connect failed");
    }
    else if (error == OTA_RECEIVE_ERROR) {
      Serial.println("Receive failed");
    }
    else if (error == OTA_END_ERROR) {
      Serial.println("End failed");
    }
  });

  ArduinoOTA.begin();

  Serial.println("OTA ready.");
  Serial.println("OTA hostname: lightwand.local");
  Serial.println("OTA port: 3232");

  // ------------------------------------------------------
  // UDP
  // ------------------------------------------------------

  if (WiFi.status() == WL_CONNECTED) {

    startUDP();

    // Green = Wi-Fi + OTA + UDP ready
    flashColor(CRGB::Green, 500);
  }

  Serial.println();
  Serial.println("============================");
  Serial.println("Light Wand ready.");
  Serial.println("============================");

  if (WiFi.status() == WL_CONNECTED) {

    Serial.print("Wand IP: ");
    Serial.println(WiFi.localIP());

    Serial.print("Python UDP target: ");
    Serial.print(WiFi.localIP());
    Serial.print(":");
    Serial.println(UDP_PORT);
  }
}

// ========================================================
// Main loop
// ========================================================

void loop() {

  bool connected =
    (WiFi.status() == WL_CONNECTED);

  // ------------------------------------------------------
  // Detect Wi-Fi loss
  // ------------------------------------------------------

  if (!connected && wasConnected) {

    wasConnected = false;

    Serial.println();
    Serial.println("Wi-Fi LOST.");

    // Red = connection lost
    flashColor(CRGB::Red, 250);
  }

  // ------------------------------------------------------
  // Wi-Fi reconnect fallback
  // ------------------------------------------------------

  if (!connected) {

    if (
      millis() - lastReconnectAttempt
      >= RECONNECT_INTERVAL
    ) {

      lastReconnectAttempt = millis();

      Serial.println(
        "Attempting Wi-Fi reconnect..."
      );

      WiFi.reconnect();
    }

    delay(10);
    return;
  }

  // ------------------------------------------------------
  // Detect successful reconnection
  // ------------------------------------------------------

  if (connected && !wasConnected) {

    wasConnected = true;

    Serial.println();
    Serial.println("Wi-Fi RESTORED!");

    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());

    Serial.print("RSSI: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");

    // Rebind UDP after Wi-Fi reconnect
    startUDP();

    // Green = network restored
    flashColor(CRGB::Green, 1000);
  }

  // ------------------------------------------------------
  // OTA
  // ------------------------------------------------------

  ArduinoOTA.handle();

  // ------------------------------------------------------
  // UDP LED stream
  // ------------------------------------------------------

  int packetSize = udp.parsePacket();

  if (packetSize == FRAME_BYTES) {

    int bytesRead =
      udp.read(packetBuffer, FRAME_BYTES);

    if (bytesRead == FRAME_BYTES) {

      for (int i = 0; i < NUM_LEDS; i++) {

        int offset = i * 3;

        leds[i].r = packetBuffer[offset];
        leds[i].g = packetBuffer[offset + 1];
        leds[i].b = packetBuffer[offset + 2];
      }

      FastLED.show();
    }
  }

  else if (packetSize > 0) {

    // Discard malformed UDP packets
    while (udp.available()) {
      udp.read();
    }

    Serial.print(
      "Ignored UDP packet of size "
    );

    Serial.println(packetSize);
  }

  // ------------------------------------------------------
  // Diagnostics every 5 seconds
  // ------------------------------------------------------

  if (
    millis() - lastStatusPrint >= 5000
  ) {

    lastStatusPrint = millis();

    Serial.print("Wand IP: ");
    Serial.print(WiFi.localIP());

    Serial.print("  RSSI: ");
    Serial.print(WiFi.RSSI());

    Serial.println(" dBm");
  }
}