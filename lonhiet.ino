#include <WiFi.h>
#include <PubSubClient.h>

// ================= CAU HINH WI-FI & HIVEMQ =================
const char* STA_SSID    = "Anh Quoc_2.4G"; // Thay ten Wi-Fi 2.4GHz khi ban giao
const char* STA_PASS    = "12345677";      // Thay mat khau Wi-Fi

const char* MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PORT   = 1883;

const char* TOPIC_DATA     = "lonhiet_gapid/data";
const char* TOPIC_TEMP     = "lonhiet_gapid/temp";
const char* TOPIC_SETPOINT = "lonhiet_gapid/setpoint";

WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Bien luu du lieu nhan tu STM32 qua Serial2 (GPIO16=RX, GPIO17=TX)
float temp_c = 0.0, sp_c = 40.0;
float kp = 43.52, ki = 2.54, kd = 149.34;
float t_xl = 0.0654, pot = 0.000, e_xl = 0.0;
int stable = 1, relay_st = 0, fan_st = 0;

String rxLine = "";
unsigned long lastReconnectAttempt = 0;

// Ham nhan lenh Setpoint tu Web / MQTT -> gui xuong STM32
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (unsigned int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }
  msg.trim();
  Serial.println("<< Nhan tu MQTT [" + String(topic) + "]: " + msg);

  if (String(topic) == TOPIC_SETPOINT) {
    // Tu dong tach so cho ca kieu gui "60" lan kieu JSON {"sp": 60}
    int idx = msg.indexOf(':');
    int start = (idx != -1) ? idx + 1 : 0;
    while (start < (int)msg.length() && !isDigit(msg[start]) && msg[start] != '.') {
      start++;
    }
    float newSp = msg.substring(start).toFloat();

    if (newSp >= 20.0 && newSp <= 150.0) {
      sp_c = newSp;
      Serial2.printf("SP,%.1f\n", newSp);
      Serial.printf(">> Da gui Setpoint %.1f C xuong STM32!\n", newSp);
    }
  }
}

void reconnectMQTT() {
  if (WiFi.status() != WL_CONNECTED) return;
  if (millis() - lastReconnectAttempt < 3000) return; // Thu lai moi 3s khong chan UART
  lastReconnectAttempt = millis();

  String clientId = "ESP32_LoNhiet_" + String((uint32_t)ESP.getEfuseMac(), HEX);
  Serial.print("Dang ket noi HiveMQ... ");
  if (mqttClient.connect(clientId.c_str())) {
    Serial.println("THANH CONG!");
    mqttClient.subscribe(TOPIC_SETPOINT);
    Serial.println("Da dang ky nhan lenh tai: " + String(TOPIC_SETPOINT));
  } else {
    Serial.print("That bai, ma loi rc=");
    Serial.println(mqttClient.state());
  }
}

void setup() {
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, 16, 17);

  WiFi.mode(WIFI_STA);
  WiFi.begin(STA_SSID, STA_PASS);
  Serial.print("Dang ket noi Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n--> Da vao Wi-Fi! IP: " + WiFi.localIP().toString());

  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setBufferSize(512);
  mqttClient.setCallback(mqttCallback);
}

void loop() {
  if (!mqttClient.connected()) {
    reconnectMQTT();
  } else {
    mqttClient.loop();
  }

  // Doc goi DATA tu STM32 va day thang len HiveMQ (ho tro ca 10 lan 11 truong)
  while (Serial2.available()) {
    char c = Serial2.read();
    if (c == '\n') {
      rxLine.trim();
      if (rxLine.startsWith("DATA,")) {
        fan_st = 0;
        int parsed = sscanf(rxLine.c_str(), "DATA,%f,%f,%f,%f,%f,%f,%f,%f,%d,%d,%d",
                            &temp_c, &sp_c, &kp, &ki, &kd, &t_xl, &pot, &e_xl, &stable, &relay_st, &fan_st);
        if (parsed >= 10 && mqttClient.connected()) {
          char jsonBuf[256];
          snprintf(jsonBuf, sizeof(jsonBuf),
                   "{\"temp\":%.2f,\"sp\":%.1f,\"kp\":%.2f,\"ki\":%.2f,\"kd\":%.2f,"
                   "\"t_xl\":%.4f,\"pot\":%.3f,\"e_xl\":%.4f,\"stable\":%d,\"relay\":%d,\"fan\":%d}",
                   temp_c, sp_c, kp, ki, kd, t_xl, pot, e_xl, stable, relay_st, fan_st);

          mqttClient.publish(TOPIC_DATA, jsonBuf);

          char tempBuf[16];
          snprintf(tempBuf, sizeof(tempBuf), "%.2f", temp_c);
          mqttClient.publish(TOPIC_TEMP, tempBuf);

          Serial.println(">> MQTT PUB: " + String(jsonBuf));
        }
      }
      rxLine = "";
    } else {
      rxLine += c;
    }
  }
}