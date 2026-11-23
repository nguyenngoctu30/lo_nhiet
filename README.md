# Hệ thống điều khiển nhiệt độ lò nhiệt bằng PID tối ưu bởi Giải thuật di truyền (GA-PID)
 
Đồ án điều khiển nhiệt độ nồi gia nhiệt dùng **STM32F407VET6** chạy bộ điều khiển PID, **ESP32** làm cầu nối MQTT, **giao diện Web** để giám sát và đặt nhiệt độ theo thời gian thực. Bộ thông số PID (Kp, Ki, Kd) được tìm bằng **Giải thuật di truyền (GA)** chạy trên Python, đánh giá bằng **MATLAB**.
 
Mô hình lò nhiệt (hàm truyền):
 
```
G(s) = 1/(11.4s + 1) · 250/(4.9s + 1)
```
 
---
 
## 1. Cấu trúc thư mục
 
| File / Thư mục | Chức năng |
|---|---|
| `fwdchuongtrinhga/ga_pid.py` | File Python chính chạy GA. Tự gọi MATLAB để đánh giá từng bộ thông số, sau đó gửi kết quả tốt nhất xuống STM32 qua USB-UART. Cuối file có khai báo cổng COM. |
| `fwdchuongtrinhga/eval_pid_lonhiet.m` | Hàm MATLAB chứa mô hình lò nhiệt. Nhận Kp, Ki, Kd từ Python, trả về t_xl, POT, e_xl và trạng thái ổn định. **Bắt buộc để cùng thư mục với `ga_pid.py`.** |
| `fwdchuongtrinhga/pid_lonhiet.slx` | Sơ đồ Simulink mô phỏng PID + lò nhiệt, dùng để xem trực quan khi cần. |
| `init_thuvien.txt` | Danh sách thư viện Python kèm phiên bản (pyserial, numpy, matlabengine...) để dựng lại môi trường không bị lệch bản. |
| `stm32_final` | Firmware cho STM32F407VET6: đọc cảm biến MAX6675, chạy PID, điều chế xung đóng/ngắt relay nồi, giao tiếp UART với PC và ESP32. |
| `lonhiet.ino` | Firmware cho ESP32: nhận UART từ STM32, đẩy dữ liệu lên MQTT broker và nhận lệnh đặt nhiệt độ từ Web chuyển xuống STM32. |
| `index.html` | Giao diện Web (HTML/CSS/JS trong một file), kết nối trực tiếp HiveMQ để hiển thị nhiệt độ, đồ thị thời gian thực, thông số GA-PID và nhập Setpoint. |
| `test_uart.py` | Script kiểm tra riêng luồng gửi UART từ PC xuống STM32, dùng khi cần debug. |
 
---
 
## 2. Kiến trúc hệ thống
 
```
Luồng 1 (tìm PID và nạp xuống mạch)
  Python (GA)  <-->  MATLAB Engine
       |
       | USB-TTL (UART1, 115200)
       v
     STM32
 
Luồng 2 (điều khiển và giám sát)
  Web (index.html) <--> HiveMQ (MQTT) <--> ESP32 <--UART2--> STM32 --> Relay --> Nồi
                                                               ^
                                                           MAX6675 (SPI1)
```
 
---
 
## 3. Giải thuật di truyền (GA)
 
**Đầu vào**
- Giới hạn dải tìm kiếm của 3 hệ số Kp, Ki, Kd.
- Số cá thể: **20**; số thế hệ: **25**.
- Quần thể ban đầu được sinh ngẫu nhiên.
**Quy trình**
1. `ga_pid.py` gửi từng bộ (Kp, Ki, Kd) sang MATLAB qua MATLAB Engine, vào hàm `eval_pid_lonhiet.m`.
2. MATLAB ghép PID với hàm truyền lò nhiệt, chạy đáp ứng bước và trả về 4 chỉ số:
   - thời gian xác lập `t_xl`
   - độ vọt lố `POT`
   - sai số xác lập `e_xl`
   - độ ổn định `stable`
3. Hàm mục tiêu cực tiểu hóa `t_xl`, `POT`, `e_xl` và **phạt nặng** nếu hệ mất ổn định.
4. GA thực hiện chọn lọc, lai ghép, đột biến qua các thế hệ để chọn ra bộ Kp, Ki, Kd tối ưu.
5. Chương trình tự xuất biểu đồ `dap_ung_ga_pid_matlab.png` phục vụ báo cáo.
---
 
## 4. Luồng dữ liệu chi tiết
 
### Luồng 1: Tìm PID tối ưu và nạp xuống mạch (PC, MATLAB, STM32)
 
Sau khi GA chạy xong, Python đóng gói chuỗi và gửi qua USB-TTL (UART1 của STM32, baud 115200):
 
```
GA,Kp,Ki,Kd,t_xl,pot,e_xl,stable\n
```
 
STM32 nhận xong sẽ lưu đè vào biến, bật bộ điều khiển và phản hồi `STM32_OK` về terminal của Python.
 
### Luồng 2: Điều khiển nhiệt độ và giám sát Web
 
**Chiều gửi lệnh xuống**
 
1. Nhập nhiệt độ đặt trên `index.html`, Web đẩy lên MQTT topic `lonhiet_gapid_2026/setpoint`.
2. ESP32 nhận được và gửi chuỗi sau qua UART2 (GPIO16/17, baud 115200):
```
SP,<nhiet_do>\n
```
3. STM32 cập nhật setpoint mới, kết hợp bộ Kp, Ki, Kd từ GA và **hệ số chuẩn hóa (scale)** (tính từ công suất nồi và thông số đã đo, nhằm hãm quán tính nhiệt) để đóng/ngắt relay qua chân **PB0**, giúp nồi bám sát nhiệt độ đặt.
**Chiều đẩy dữ liệu lên (mỗi 500 ms)**
 
1. STM32 đọc nhiệt độ từ **MAX6675** qua **SPI1** (chân CS là **PA4**).
2. STM32 gửi gói sau qua UART2 sang ESP32:
```
DATA,temp,sp,kp,ki,kd,t_xl,pot,e_xl,stable,relay\n
```
3. ESP32 đóng gói JSON, đẩy lên MQTT:
   - `lonhiet_gapid_2026/data`: toàn bộ dữ liệu
   - `lonhiet_gapid_2026/temp`: nhiệt độ
4. `index.html` nhận dữ liệu, cập nhật số liệu và vẽ đồ thị thời gian thực.
### Bảng tóm tắt MQTT
 
| Topic | Hướng | Nội dung |
|---|---|---|
| `lonhiet_gapid_2026/setpoint` | Web → ESP32 | Nhiệt độ đặt |
| `lonhiet_gapid_2026/data` | ESP32 → Web | JSON đầy đủ (nhiệt độ, SP, PID, chỉ số GA, trạng thái relay) |
| `lonhiet_gapid_2026/temp` | ESP32 → Web | Nhiệt độ hiện tại |
 
---
 
## 5. Sơ đồ chân
 
| Chức năng | Chân |
|---|---|
| MAX6675 CS (SPI1) | PA4 |
| Relay nồi | PB0 |
| Relay quạt 12V | PB1 |
| UART1 (USB-TTL, PC) | 115200 baud |
| UART2 (ESP32) | 115200 baud, phía ESP32 là GPIO16/17 |
 
Lưu ý: đấu UART chéo TX ↔ RX và nối chung GND giữa các board.
 
### Đấu quạt 12V
 
**Phía điều khiển (STM32 → Relay quạt)**
- Chân PB1 (STM32) → chân `IN` của Relay quạt.
- `VCC` và `GND` của Relay → nguồn 3.3V/5V và GND chung với STM32.
**Phía tải 12V (Nguồn 12V → Relay → Quạt)**
- Dây dương nguồn 12V (+) → chân `COM` của Relay.
- Chân `NO` của Relay → dây Đỏ (+) của quạt 12V.
- Dây Đen (-) của quạt 12V → dây âm nguồn 12V (-).
---
 
## 6. Cài đặt môi trường
 
### Yêu cầu
- Python 3.x
- MATLAB (bản đang dùng: **R2025a**)
- Mạch STM32F407VET6 + MAX6675, ESP32, relay, quạt 12V, cáp USB-TTL
- ST-LINK V2 và STM32CubeProgrammer (khi cần nạp lại STM32)
### Cài thư viện Python
 
```bash
pip install -r init_thuvien.txt
```
 
> **Lưu ý:** phiên bản `matlabengine` phải **khớp đúng đời MATLAB** đang cài trên máy (ví dụ MATLAB R2025a thì dùng đúng bản matlabengine tương ứng). Nếu lệch bản sẽ không kết nối được MATLAB Engine.
 
### Cấu hình ESP32
 
Mở `lonhiet.ino` và sửa **tên WiFi (SSID)** và **mật khẩu WiFi** cho phù hợp, sau đó nạp lại cho ESP32.
 
---
 
## 7. Hướng dẫn nạp firmware STM32
 
Firmware `stm32_final` đã được nạp sẵn trên mạch, thông thường **không cần nạp lại**.
 
Khi build xong, nút Run/Play trong IDE nạp có thể báo lỗi do mạch nạp trên bo. Cách nạp ổn định là dùng **STM32CubeProgrammer**:
 
1. Build project xong (nút búa) để có file `.elf`/`.hex`.
2. Mở **STM32CubeProgrammer**, chọn tab **Erasing & Programming** (biểu tượng mũi tên chĩa vào ổ cứng).
3. Cắm **ST-LINK V2** vào mạch, bấm **Connect** ở góc trên bên phải.
4. Chọn file firmware, tích đủ các ô tùy chọn (xóa trước khi nạp / verify, theo ảnh hướng dẫn kèm theo).
5. Bấm **Start Programming**.
6. Nạp xong bấm **Disconnect**, rồi bấm nút **Reset** trên mạch.
---
 
## 8. Quy trình chạy nhanh (demo / bàn giao)
 
1. **Firmware:** STM32 đã nạp `stm32_final`, ESP32 đã nạp `lonhiet.ino` (đã đổi SSID/mật khẩu WiFi). Không cần nạp lại.
2. **Cấp nguồn:** cấp nguồn cho STM32, ESP32, quạt 12V tản nhiệt và cắm cáp USB-TTL vào laptop.
3. **Chọn cổng COM:** mở *Device Manager*, xem tên cổng COM của USB-TTL, rồi sửa đúng tên cổng ở **cuối file `ga_pid.py`**.
4. **Mở giao diện Web:** mở `index.html` bằng trình duyệt. Khi góc trên báo xanh **"Đã kết nối HiveMQ"** và nhiệt độ hiển thị khoảng nhiệt độ phòng (~30°C) là luồng dữ liệu đã thông.
5. **(Tùy chọn) Chạy GA:**
```bash
python ga_pid.py
```
   Đợi khoảng 20 đến 35 giây để MATLAB và Python tiến hóa xong. Chương trình tự gửi thông số mới xuống STM32 và cập nhật các ô KP, KI, KD, T_XL, POT, E_XL trên Web.
   Bước này không bắt buộc vì firmware `stm32_final` đã được tối ưu sẵn bộ thông số.

   <img width="1554" height="705" alt="image" src="https://github.com/user-attachments/assets/9d989248-8ac3-4f57-bf2a-de4d2d45db6e" />

6. **Cắm điện 220V cho nồi và test bám nhiệt:** nhập thử các mốc 60°C, 80°C, 90°C trên Web và bấm gửi, quan sát đồ thị.
 
> ⚠️ **CẢNH BÁO AN TOÀN:** Không đặt nhiệt độ trên **95 đến 100°C**. Nồi có **rơ-le nhiệt bảo vệ cơ học** bên trong, nóng quá 100°C nồi sẽ tự ngắt điện để đảm bảo an toàn.
 
---
 
## 9. Kiểm tra và debug UART
 
Nếu STM32 không phản hồi khi gửi thông số từ PC, dùng:
 
```bash
python test_uart.py
```
 
Script này kiểm tra riêng luồng gửi UART từ PC xuống STM32 (nhớ sửa đúng cổng COM trước khi chạy).
 
---
 
## 10. Xử lý sự cố thường gặp
 
| Hiện tượng | Nguyên nhân / Cách xử lý |
|---|---|
| Web không báo "Đã kết nối HiveMQ" | Kiểm tra máy có internet; kiểm tra ESP32 đã vào WiFi (sai SSID/mật khẩu). |
| Web kết nối nhưng không có nhiệt độ | Kiểm tra dây UART2 giữa ESP32 (GPIO16/17) và STM32, đấu chéo TX/RX và chung GND. |
| `ga_pid.py` báo lỗi cổng COM | Sai tên cổng: xem lại Device Manager và sửa cuối file `ga_pid.py`; đóng các terminal khác đang chiếm cổng. |
| Python không gọi được MATLAB | Phiên bản `matlabengine` không khớp đời MATLAB (R2025a); `eval_pid_lonhiet.m` phải nằm cùng thư mục với `ga_pid.py`. |
| Nạp STM32 bằng nút Play báo lỗi | Dùng STM32CubeProgrammer theo mục 7. |
| Nồi tự ngắt khi đang chạy | Đặt quá 95 đến 100°C, rơ-le nhiệt bảo vệ đã ngắt. Để nguội rồi hạ nhiệt độ đặt. |
 
---
 
## 11. Tác giả
 
Repo: [nguyenngoctu30/lo_nhiet](https://github.com/nguyenngoctu30/lo_nhiet)
 
