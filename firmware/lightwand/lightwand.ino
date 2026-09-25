#include <WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <FastLED.h>

// ========================================================
// Wi-Fi
// ========================================================
#include "secrets.h"

struct WiFiNetwork {
  const char* ssid;
  const char* password;
};

WiFiNetwork networks[] = {
  { WIFI_PRIMARY_SSID, WIFI_PRIMARY_PASSWORD },
  { WIFI_FALLBACK_SSID, WIFI_FALLBACK_PASSWORD }
};

const int NUM_NETWORKS =
  sizeof(networks) / sizeof(networks[0]);

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

const char* DISCOVERY_REQUEST = "LIGHTWAND_DISCOVER";
const char* DISCOVERY_RESPONSE = "LIGHTWAND_HERE";

uint8_t packetBuffer[FRAME_BYTES];

// ========================================================
// Timing / state
// ========================================================

unsigned long lastStatusPrint = 0;
unsigned long lastReconnectAttempt = 0;

const unsigned long RECONNECT_INTERVAL = 15000;

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
  Serial.println("Searching for known Wi-Fi networks...");

  // Give radios / access points a moment after startup
  delay(2000);

  for (int i = 0; i < NUM_NETWORKS; i++) {

    Serial.print("Trying: ");
    Serial.println(networks[i].ssid);

    // Clean up previous attempt
    WiFi.disconnect(false);
    delay(500);

    WiFi.begin(
      networks[i].ssid,
      networks[i].password
    );

    unsigned long attemptStart = millis();

    // Give each network about 10 seconds
    while (
      WiFi.status() != WL_CONNECTED &&
      millis() - attemptStart < 10000
    ) {
      delay(500);
      Serial.print(".");
    }

    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {

      Serial.println("Wi-Fi CONNECTED!");

      Serial.print("Network: ");
      Serial.println(networks[i].ssid);

      Serial.print("IP address: ");
      Serial.println(WiFi.localIP());

      Serial.print("Signal strength: ");
      Serial.print(WiFi.RSSI());
      Serial.println(" dBm");

      wasConnected = true;

      return;
    }

    Serial.println("Connection failed.");
  }

  Serial.println();
  Serial.println("No known Wi-Fi networks available.");
  Serial.println("Firmware will keep retrying.");

  wasConnected = false;
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
  // UDP: discovery + LED stream
  // ------------------------------------------------------

  int packetSize = udp.parsePacket();

  if (packetSize > 0) {

    // ----------------------------------------------------
    // Normal 100-pixel RGB frame
    // ----------------------------------------------------

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

    // ----------------------------------------------------
    // Discovery request
    // ----------------------------------------------------

    else if (packetSize == strlen(DISCOVERY_REQUEST)) {

      char discoveryBuffer[32];

      int bytesRead = udp.read(
        discoveryBuffer,
        sizeof(discoveryBuffer) - 1
      );

      discoveryBuffer[bytesRead] = '\0';

      if (
        strcmp(
          discoveryBuffer,
          DISCOVERY_REQUEST
        ) == 0
      ) {

        IPAddress senderIP = udp.remoteIP();
        uint16_t senderPort = udp.remotePort();

        Serial.print("Discovery request from ");
        Serial.println(senderIP);

        udp.beginPacket(senderIP, senderPort);
        udp.print(DISCOVERY_RESPONSE);
        udp.endPacket();
      }
    }

    // ----------------------------------------------------
    // Anything else is invalid
    // ----------------------------------------------------

    else {

      while (udp.available()) {
        udp.read();
      }

      Serial.print(
        "Ignored UDP packet of size "
      );

      Serial.println(packetSize);
    }
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