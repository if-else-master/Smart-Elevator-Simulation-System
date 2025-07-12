import tkinter as tk
from tkinter import ttk
import time
import cv2
import numpy as np
from PIL import Image, ImageTk
import serial
import serial.tools.list_ports
import threading
import glob

class ArduinoController:
    def __init__(self, baud_rate=9600):
        self.baud_rate = baud_rate
        self.serial = None
        self.connected = False
        self.receive_thread = None
        self.running = False
        self.position_callback = None
        self.connection_callback = None
        self.status_callback = None
        self.last_ping_time = 0
        self.ping_interval = 5  # 5秒ping一次
        self.connect()
        
    def connect(self):
        """連接Arduino"""
        try:
            # 尋找所有可能的串口
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            arduino_ports = []
            
            for port in ports:
                # 檢查是否為Arduino相關的串口
                if ('Arduino' in port.description or 
                    'CH340' in port.description or 
                    'USB' in port.description or
                    port.device.startswith('/dev/cu.usbmodem') or
                    port.device.startswith('/dev/cu.usbserial')):
                    arduino_ports.append(port.device)
                    
            print(f"找到的串口: {[port.device for port in ports]}")
            print(f"Arduino候選串口: {arduino_ports}")
            
            if not arduino_ports:
                # 如果沒找到，使用舊的方法
                import glob
                arduino_ports = glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/cu.usbserial*')
                
            if not arduino_ports:
                print("❌ 找不到 Arduino 串口，請確認 Arduino 已連接並安裝驅動")
                self.connected = False
                if self.connection_callback:
                    self.connection_callback(False, "找不到Arduino串口")
                return False
                
            # 嘗試連接每個候選串口
            for port in arduino_ports:
                try:
                    print(f"🔄 嘗試連接串口: {port}")
                    self.serial = serial.Serial(port, self.baud_rate, timeout=1)
                    time.sleep(2)  # 等待Arduino重置
                    
                    # 測試連接
                    self.serial.write(b"PING\n")
                    time.sleep(0.5)
                    
                    self.connected = True
                    self.running = True
                    print(f"✅ Arduino 控制器連接成功: {port}")
                    
                    # 啟動接收執行緒
                    if self.receive_thread and self.receive_thread.is_alive():
                        self.running = False
                        self.receive_thread.join(timeout=1)
                        
                    self.receive_thread = threading.Thread(target=self.receive_data, daemon=True)
                    self.receive_thread.start()
                    
                    # 連接成功後立即初始化電梯在1樓
                    time.sleep(0.5)  # 等待Arduino完全準備好
                    self.send_command("INIT")
                    
                    if self.connection_callback:
                        self.connection_callback(True, f"已連接到 {port}")
                    return True
                    
                except Exception as e:
                    print(f"❌ 串口 {port} 連接失敗: {e}")
                    if self.serial:
                        try:
                            self.serial.close()
                        except:
                            pass
                        self.serial = None
                    continue
                    
            print("❌ 所有串口連接嘗試都失敗")
            self.connected = False
            if self.connection_callback:
                self.connection_callback(False, "所有串口連接嘗試都失敗")
            return False
            
        except Exception as e:
            print(f"❌ Arduino 連接過程發生錯誤: {e}")
            self.connected = False
            if self.connection_callback:
                self.connection_callback(False, f"連接錯誤: {e}")
            return False
            
    def reconnect(self):
        """重新連接"""
        print("🔄 嘗試重新連接 Arduino...")
        self.close()
        time.sleep(1)
        return self.connect()
        
    def receive_data(self):
        """接收來自Arduino的數據"""
        buffer = ""
        while self.running and self.connected:
            try:
                if self.serial and self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line:
                            self.process_arduino_message(line)
                            
                # 定期發送ping檢查連接
                current_time = time.time()
                if current_time - self.last_ping_time > self.ping_interval:
                    self.send_ping()
                    self.last_ping_time = current_time
                    
                time.sleep(0.01)
                
            except serial.SerialException as e:
                print(f"❌ 串口連接丟失: {e}")
                self.connected = False
                if self.connection_callback:
                    self.connection_callback(False, f"連接丟失: {e}")
                # 嘗試自動重連
                if self.reconnect():
                    continue
                else:
                    break
                    
            except Exception as e:
                print(f"❌ 接收數據錯誤: {e}")
                time.sleep(0.1)  # 避免快速循環
                
    def send_ping(self):
        """發送ping檢查連接"""
        try:
            if self.connected and self.serial:
                self.serial.write(b"PING\n")
        except:
            pass  # ping失敗不報錯，由receive_data處理
            
    def process_arduino_message(self, message):
        """處理來自Arduino的訊息"""
        try:
            if message == "PONG":
                # ping回應，連接正常
                return
                
            if message.startswith("POS:"):
                # 位置回報: POS:floor
                floor = int(message.split(":")[1])
                print(f"📍 位置更新: {floor}樓")
                if self.position_callback:
                    self.position_callback(floor)
                    
            elif message.startswith("MOVE_START:"):
                # 移動開始: MOVE_START:floor
                floor = int(message.split(":")[1])
                print(f"🚀 Arduino開始移動到 {floor} 樓")
                
            elif message.startswith("MOVE_COMPLETE:"):
                # 移動完成: MOVE_COMPLETE:floor
                floor = int(message.split(":")[1])
                print(f"✅ Arduino移動完成，到達 {floor} 樓")
                if self.position_callback:
                    self.position_callback(floor)
                    
            elif message.startswith("PROGRESS:"):
                # 移動進度: PROGRESS:percentage%
                progress = message.split(":")[1]
                print(f"📊 移動進度: {progress}")
                
            elif message.startswith("STATUS:"):
                # 狀態回報: STATUS:current:target:moving:emergency
                parts = message.split(":")
                if len(parts) >= 5:
                    current_floor = int(parts[1])
                    target_floor = int(parts[2])
                    moving = parts[3] == "MOVING"
                    emergency = parts[4] == "EMERGENCY"
                    if self.status_callback:
                        self.status_callback(current_floor, target_floor, moving, emergency)
                        
            elif message.startswith("LIMIT:"):
                # 微動開關觸發: LIMIT:top/bottom
                limit_type = message.split(":")[1]
                print(f"⚡ 微動開關觸發: {limit_type}")
                
            elif message.startswith("ERROR:"):
                # 錯誤訊息
                error = message.split(":", 1)[1]
                print(f"❌ Arduino錯誤: {error}")
                
            elif "校準" in message or "calibrat" in message.lower():
                # 校準相關訊息
                print(f"🔧 校準: {message}")
                
            elif "初始化" in message or "init" in message.lower():
                # 初始化相關訊息
                print(f"🏠 初始化: {message}")
                
            else:
                # 其他訊息
                print(f"📨 Arduino: {message}")
                
        except Exception as e:
            print(f"❌ 處理Arduino訊息錯誤: {e}, 原始訊息: {message}")
            
    def send_command(self, command):
        """發送命令到Arduino"""
        if not self.connected or not self.serial:
            print(f"⚠️  Arduino未連接，無法發送命令: {command}")
            return False
            
        try:
            self.serial.write(f"{command}\n".encode())
            print(f"📤 發送命令: {command}")
            return True
        except Exception as e:
            print(f"❌ 發送命令失敗: {e}")
            self.connected = False
            if self.connection_callback:
                self.connection_callback(False, f"發送失敗: {e}")
            return False
            
    def move_to_floor(self, target_floor):
        """移動到指定樓層"""
        if self.send_command(f"MOVE:{target_floor}"):
            print(f"🏢 命令Arduino移動到 {target_floor} 樓")
        
    def stop_motor(self):
        """停止馬達"""
        self.send_command("STOP")
        
    def calibrate_position(self):
        """校準位置"""
        if self.send_command("CALIBRATE"):
            print("🔧 開始校準Arduino電梯位置")
        
    def set_emergency_mode(self, enabled):
        """設置緊急模式"""
        mode = 'ON' if enabled else 'OFF'
        if self.send_command(f"EMERGENCY:{mode}"):
            print(f"🚨 設置緊急模式: {mode}")
            
    def get_status(self):
        """獲取狀態"""
        self.send_command("STATUS")
        
    def test_motor(self):
        """測試馬達"""
        self.send_command("TEST")
        
    def initialize_elevator(self):
        """初始化電梯到1樓位置（不移動馬達）"""
        if self.send_command("INIT"):
            print("🏠 初始化電梯到1樓位置")
        
    def close(self):
        """關閉連接"""
        self.running = False
        if self.receive_thread and self.receive_thread.is_alive():
            try:
                self.receive_thread.join(timeout=1)
            except:
                pass
                
        if self.serial and self.connected:
            try:
                self.serial.close()
            except:
                pass
            self.connected = False
            print("🔌 Arduino 連接已關閉")

class SimpleElevatorGUI:
    def __init__(self, master):
        self.master = master
        master.title("智能電梯控制系統 - 含MOG2監控")
        master.geometry("800x700")
        
        # 初始化 Arduino 控制器
        self.arduino = ArduinoController()
        self.arduino.position_callback = self.on_position_update
        self.arduino.connection_callback = self.on_arduino_connection_change
        self.arduino.status_callback = self.on_status_update
        
        # 攝影機和MOG2初始化
        self.cap = cv2.VideoCapture(0)
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=True
        )
        self.penetration_area = 0
        self.total_area = 0
        self.penetration_ratio = 0
        self.penetration_threshold = 0.15  # 15%閾值
        self.baseline_established = False
        self.stabilization_frames = 0
        self.display_width = 320
        self.display_height = 240
        
        # 電梯狀態
        self.current_floor = 1
        self.target_floor = 1
        self.is_moving = False
        self.emergency_mode = False
        self.auto_emergency = False  # 自動緊急模式（由MOG2觸發）
        self.manual_emergency = False  # 手動緊急模式
        
        # 電梯請求隊列系統
        self.floor_requests = set()  # 請求的樓層集合
        self.current_direction = 0  # 當前方向：1=上行, -1=下行, 0=停止
        self.pending_floors = []  # 待停靠樓層列表（按順序）
        
        self.setup_gui()
        
        # 啟動主循環
        self.master.after(1000, self.update_status)
        self.master.after(100, self.update_mog2_detection)  # MOG2檢測循環
        
    def setup_gui(self):
        """設置GUI界面"""
        # 主要布局 - 左右分割
        main_paned = tk.PanedWindow(self.master, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左側：攝影機監控
        left_frame = tk.Frame(main_paned)
        main_paned.add(left_frame, width=350)
        
        # 右側：電梯控制
        right_frame = tk.Frame(main_paned)
        main_paned.add(right_frame, width=430)
        
        # === 左側：MOG2攝影機監控 ===
        camera_title = tk.Label(left_frame, text="🎥 MOG2 安全監控", 
                               font=("Arial", 16, "bold"))
        camera_title.pack(pady=5)
        
        # 攝影機顯示區域
        self.camera_label = tk.Label(left_frame, bg="black")
        self.camera_label.pack(pady=5)
        
        # MOG2資訊顯示
        self.mog2_info_frame = tk.LabelFrame(left_frame, text="MOG2檢測資訊", 
                                           font=("Arial", 12, "bold"))
        self.mog2_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.penetration_info_label = tk.Label(
            self.mog2_info_frame, text="突破量: 0.00%", 
            font=("Arial", 12)
        )
        self.penetration_info_label.pack(pady=2)
        
        # MOG2控制
        mog2_control_frame = tk.Frame(self.mog2_info_frame)
        mog2_control_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(mog2_control_frame, text="緊急閾值:").pack(side=tk.LEFT)
        
        self.emergency_slider = tk.Scale(
            mog2_control_frame, from_=5, to=50, orient=tk.HORIZONTAL,
            command=self.update_emergency_threshold, length=150
        )
        self.emergency_slider.set(self.penetration_threshold * 100)
        self.emergency_slider.pack(side=tk.LEFT, padx=5)
        
        tk.Label(mog2_control_frame, text="%").pack(side=tk.LEFT)
        
        self.reset_bg_button = tk.Button(
            self.mog2_info_frame, text="重置MOG2背景", command=self.reset_mog2_background,
            bg="lightblue", font=("Arial", 10)
        )
        self.reset_bg_button.pack(fill=tk.X, padx=5, pady=5)
        
        # === 右側：電梯控制 ===
        # 標題
        title_label = tk.Label(right_frame, text="🏢 電梯控制系統", 
                              font=("Arial", 18, "bold"))
        title_label.pack(pady=5)
        
        # Arduino連接狀態
        self.connection_frame = tk.Frame(right_frame)
        self.connection_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.arduino_status_label = tk.Label(
            self.connection_frame, text="🔴 Arduino: 檢查連接中...", 
            font=("Arial", 11), fg="orange"
        )
        self.arduino_status_label.pack(side=tk.LEFT)
        
        self.reconnect_button = tk.Button(
            self.connection_frame, text="重新連接", command=self.reconnect_arduino,
            bg="lightcoral", font=("Arial", 9)
        )
        self.reconnect_button.pack(side=tk.RIGHT)
        
        # 電梯狀態顯示
        self.status_frame = tk.LabelFrame(right_frame, text="電梯狀態", 
                                         font=("Arial", 13, "bold"))
        self.status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 當前樓層
        tk.Label(self.status_frame, text="當前樓層:", 
                font=("Arial", 11)).grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.current_floor_label = tk.Label(self.status_frame, text="1", 
                                           font=("Arial", 20, "bold"), fg="blue")
        self.current_floor_label.grid(row=0, column=1, padx=5, pady=3)
        
        # 目標樓層
        tk.Label(self.status_frame, text="目標樓層:", 
                font=("Arial", 11)).grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self.target_floor_label = tk.Label(self.status_frame, text="1", 
                                          font=("Arial", 16), fg="green")
        self.target_floor_label.grid(row=1, column=1, padx=5, pady=3)
        
        # 移動狀態
        tk.Label(self.status_frame, text="狀態:", 
                font=("Arial", 11)).grid(row=2, column=0, sticky="w", padx=5, pady=3)
        self.move_status_label = tk.Label(self.status_frame, text="待命", 
                                         font=("Arial", 12), fg="black")
        self.move_status_label.grid(row=2, column=1, padx=5, pady=3)
        
        # 請求隊列
        tk.Label(self.status_frame, text="待停靠:", 
                font=("Arial", 11)).grid(row=3, column=0, sticky="w", padx=5, pady=3)
        self.requests_label = tk.Label(self.status_frame, text="無", 
                                      font=("Arial", 11), fg="purple")
        self.requests_label.grid(row=3, column=1, padx=5, pady=3)
        
        # 當前運行方向
        tk.Label(self.status_frame, text="運行方向:", 
                font=("Arial", 11)).grid(row=4, column=0, sticky="w", padx=5, pady=3)
        self.direction_label = tk.Label(self.status_frame, text="停止", 
                                       font=("Arial", 11), fg="gray")
        self.direction_label.grid(row=4, column=1, padx=5, pady=3)
        
        # 電梯控制按鈕
        self.control_frame = tk.LabelFrame(right_frame, text="電梯控制", 
                                          font=("Arial", 13, "bold"))
        self.control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 樓層按鈕
        floor_buttons_frame = tk.Frame(self.control_frame)
        floor_buttons_frame.pack(pady=8)
        
        tk.Label(floor_buttons_frame, text="選擇樓層:", 
                font=("Arial", 11)).pack()
        
        button_frame = tk.Frame(floor_buttons_frame)
        button_frame.pack(pady=5)
        
        self.floor_buttons = {}
        for floor in [1, 2, 3]:
            btn = tk.Button(button_frame, text=f"{floor}樓", 
                           command=lambda f=floor: self.add_floor_request(f),
                           width=7, height=2, font=("Arial", 12, "bold"),
                           bg="lightblue")
            btn.pack(side=tk.LEFT, padx=3)
            self.floor_buttons[floor] = btn
        
        # 系統控制按鈕
        self.system_frame = tk.LabelFrame(right_frame, text="系統控制", 
                                         font=("Arial", 13, "bold"))
        self.system_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 第一行按鈕
        button_row1 = tk.Frame(self.system_frame)
        button_row1.pack(fill=tk.X, pady=3)
        
        self.stop_button = tk.Button(button_row1, text="緊急停止", 
                                    command=self.emergency_stop,
                                    bg="red", fg="white", font=("Arial", 11, "bold"))
        self.stop_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        
        self.calibrate_button = tk.Button(button_row1, text="校準位置", 
                                         command=self.calibrate_elevator,
                                         bg="orange", font=("Arial", 11))
        self.calibrate_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        
        # 第二行按鈕
        button_row2 = tk.Frame(self.system_frame)
        button_row2.pack(fill=tk.X, pady=3)
        
        self.test_button = tk.Button(button_row2, text="測試馬達", 
                                    command=self.test_motor,
                                    bg="lightgreen", font=("Arial", 11))
        self.test_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        
        self.status_button = tk.Button(button_row2, text="更新狀態", 
                                      command=self.update_status,
                                      bg="lightgray", font=("Arial", 11))
        self.status_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        
        # 第三行按鈕
        button_row3 = tk.Frame(self.system_frame)
        button_row3.pack(fill=tk.X, pady=3)
        
        self.init_button = tk.Button(button_row3, text="初始化1樓", 
                                    command=self.initialize_elevator,
                                    bg="lightcyan", font=("Arial", 11))
        self.init_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        
        # 緊急模式指示
        self.emergency_frame = tk.Frame(right_frame)
        self.emergency_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.emergency_label = tk.Label(self.emergency_frame, text="", 
                                       font=("Arial", 12, "bold"))
        self.emergency_label.pack()
        
        # 狀態資訊
        self.info_frame = tk.LabelFrame(right_frame, text="系統資訊", 
                                       font=("Arial", 11, "bold"))
        self.info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 建立文字框和滾動條
        text_frame = tk.Frame(self.info_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        self.info_text = tk.Text(text_frame, height=6, font=("Courier", 9))
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=scrollbar.set)
        
        self.info_text.pack(side="left", fill=tk.BOTH, expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.log_message("系統啟動完成")
        self.log_message("MOG2背景減法器已初始化")
        
    def reset_mog2_background(self):
        """重置MOG2背景"""
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=True
        )
        self.baseline_established = False
        self.stabilization_frames = 0
        self.log_message("🔄 MOG2背景已重置，重新建立基準中...")
        
    def update_emergency_threshold(self, val):
        """更新緊急模式閾值"""
        self.penetration_threshold = float(val) / 100.0
        self.log_message(f"🎯 緊急閾值已設為: {float(val):.1f}%")
        
    def update_mog2_detection(self):
        """更新MOG2突破量檢測"""
        ret, frame = self.cap.read()
        if ret:
            if not self.baseline_established:
                # 建立背景基準階段
                self.stabilization_frames += 1
                if self.stabilization_frames > 30:  # 增加穩定幀數
                    self.baseline_established = True
                    self.log_message("✅ MOG2背景基準建立完成")
                    
                self.background_subtractor.apply(frame)
                
                # 顯示初始化進度
                display_frame = frame.copy()
                progress_text = f"建立MOG2背景基準中 ({self.stabilization_frames}/30)..."
                cv2.putText(display_frame, progress_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                self.display_camera_frame(display_frame)
                self.master.after(100, self.update_mog2_detection)
                return
                
            # MOG2突破量檢測
            self.total_area = frame.shape[0] * frame.shape[1]
            fg_mask = self.background_subtractor.apply(frame)
            
            # 形態學處理減少雜訊
            fg_mask = cv2.GaussianBlur(fg_mask, (5, 5), 0)
            _, fg_mask = cv2.threshold(fg_mask, 128, 255, cv2.THRESH_BINARY)
            
            kernel = np.ones((5, 5), np.uint8)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
            
            # 計算突破量
            self.penetration_area = cv2.countNonZero(fg_mask)
            self.penetration_ratio = (self.penetration_area / self.total_area) * 100
            
            # 更新顯示
            self.penetration_info_label.config(
                text=f"突破量: {self.penetration_ratio:.2f}% | 閾值: {self.penetration_threshold*100:.1f}%"
            )
            
            # 檢查是否觸發自動緊急模式
            prev_auto_emergency = self.auto_emergency
            if self.penetration_ratio / 100 >= self.penetration_threshold:
                if not self.auto_emergency:
                    self.auto_emergency = True
                    self.log_message(f"🚨 MOG2檢測觸發自動緊急模式！突破量: {self.penetration_ratio:.2f}%")
            else:
                if self.auto_emergency:
                    self.auto_emergency = False
                    self.log_message(f"✅ 突破量降低，自動解除緊急模式。當前: {self.penetration_ratio:.2f}%")
            
            # 更新緊急狀態
            if prev_auto_emergency != self.auto_emergency:
                self.update_emergency_mode()
            
            # 視覺化顯示
            self.create_mog2_visualization(frame, fg_mask)
            
        self.master.after(100, self.update_mog2_detection)
        
    def create_mog2_visualization(self, frame, fg_mask):
        """創建MOG2視覺化顯示"""
        # 將前景遮罩轉為彩色
        fg_mask_colored = cv2.cvtColor(fg_mask, cv2.COLOR_GRAY2BGR)
        fg_mask_colored[np.where((fg_mask_colored == [255, 255, 255]).all(axis=2))] = [0, 0, 255]
        
        # 混合原圖和前景遮罩
        alpha = 0.4
        visualization = cv2.addWeighted(frame, 1, fg_mask_colored, alpha, 0)
        
        # 添加資訊文字
        info_color = (0, 255, 0)  # 綠色
        if self.penetration_ratio / 100 >= self.penetration_threshold:
            info_color = (0, 0, 255)  # 紅色
            
        cv2.putText(visualization, f"突破量: {self.penetration_ratio:.2f}%", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, info_color, 2)
        cv2.putText(visualization, f"閾值: {self.penetration_threshold*100:.1f}%", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                   
        if self.auto_emergency:
            cv2.putText(visualization, "⚠️ 自動緊急模式", 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                       
        self.display_camera_frame(visualization)
        
    def display_camera_frame(self, frame):
        """顯示攝影機畫面"""
        # 調整大小
        frame_resized = cv2.resize(frame, (self.display_width, self.display_height))
        
        # 轉換為Tkinter可顯示的格式
        rgb_frame = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb_frame)
        photo = ImageTk.PhotoImage(image)
        
        self.camera_label.config(image=photo)
        self.camera_label.image = photo  # 保持引用
        
    def update_emergency_mode(self):
        """更新緊急模式狀態"""
        prev_emergency = self.emergency_mode
        self.emergency_mode = self.manual_emergency or self.auto_emergency
        
        if self.arduino.connected:
            self.arduino.set_emergency_mode(self.emergency_mode)
            
        # 更新GUI顯示
        if self.emergency_mode:
            if self.auto_emergency and self.manual_emergency:
                emergency_text = "🚨 自動+手動緊急模式 🚨"
            elif self.auto_emergency:
                emergency_text = "🚨 MOG2自動緊急模式 🚨"
            else:
                emergency_text = "🚨 手動緊急模式 🚨"
                
            self.emergency_label.config(text=emergency_text, fg="white", bg="red")
            self.stop_button.config(text="解除手動緊急", bg="darkred")
        else:
            self.emergency_label.config(text="", bg=self.master.cget('bg'))
            self.stop_button.config(text="緊急停止", bg="red")
        
        if prev_emergency != self.emergency_mode:
            if self.emergency_mode:
                self.log_message("🚨 緊急模式啟動")
                # 緊急模式啟動時清空移動狀態
                if self.is_moving:
                    self.is_moving = False
                    self.current_direction = 0
                    self.move_status_label.config(text="緊急停止", fg="red")
                    self.floor_requests.clear()
                    self.pending_floors.clear()
                    self.requests_label.config(text="無")
                    self.update_direction_display()
            else:
                self.log_message("✅ 緊急模式解除")
        
    def log_message(self, message):
        """記錄訊息到資訊區域"""
        timestamp = time.strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}\n"
        self.info_text.insert(tk.END, full_message)
        self.info_text.see(tk.END)  # 自動滾動到最新訊息
        
    def add_floor_request(self, floor):
        """添加樓層請求"""
        if not self.arduino.connected:
            self.log_message("❌ Arduino未連接，無法移動電梯")
            return
            
        if self.emergency_mode:
            self.log_message("⚠️ 緊急模式中，請先解除緊急狀態")
            return
            
        if floor == self.current_floor:
            self.log_message(f"ℹ️ 電梯已在 {floor} 樓")
            return
            
        # 檢查是否可以中途停靠
        if self.is_moving and not self.can_stop_at_floor(floor):
            self.log_message(f"⚠️ 電梯正在反方向移動，{floor}樓請求將稍後處理")
            
        # 添加到請求集合
        self.floor_requests.add(floor)
        self.log_message(f"🎯 添加樓層請求: {floor} 樓")
        
        # 如果電梯沒有在移動，立即開始處理請求
        if not self.is_moving:
            self.process_next_request()
        else:
            # 如果正在移動，檢查是否需要中途停靠
            if self.can_stop_at_floor(floor):
                self.log_message(f"🛑 檢測到中途停靠請求：{floor}樓，重新計算停靠順序")
                # 重新計算停靠順序，可能需要中途停靠
                old_target = self.target_floor
                self.update_pending_floors()
                
                # 如果目標樓層改變了，說明需要中途停靠
                if self.pending_floors and self.pending_floors[0] != old_target:
                    new_target = self.pending_floors[0]
                    self.target_floor = new_target
                    self.target_floor_label.config(text=str(new_target))
                    self.log_message(f"🔄 更新目標樓層：{old_target}樓 → {new_target}樓（中途停靠）")
                    # 向Arduino發送新的目標
                    self.arduino.move_to_floor(new_target)
            else:
                # 如果不能中途停靠，只更新停靠順序
                self.update_pending_floors()
            
    def move_to_floor(self, floor):
        """兼容舊接口的方法"""
        self.add_floor_request(floor)
        
    def process_next_request(self):
        """處理下一個請求"""
        if not self.floor_requests or self.emergency_mode:
            return
            
        # 計算停靠順序
        self.update_pending_floors()
        
        if self.pending_floors:
            next_floor = self.pending_floors[0]
            self.target_floor = next_floor
            self.target_floor_label.config(text=str(next_floor))
            
            # 確定移動方向
            if next_floor > self.current_floor:
                self.current_direction = 1  # 上行
                self.log_message(f"🔼 開始上行到 {next_floor} 樓")
            elif next_floor < self.current_floor:
                self.current_direction = -1  # 下行
                self.log_message(f"🔽 開始下行到 {next_floor} 樓")
            else:
                return  # 已經在目標樓層
                
            self.is_moving = True
            self.move_status_label.config(text="移動中", fg="orange")
            self.arduino.move_to_floor(next_floor)
            
            # 更新運行方向顯示
            self.update_direction_display()
            
    def update_pending_floors(self):
        """更新待停靠樓層順序"""
        if not self.floor_requests:
            self.pending_floors = []
            return
            
        requests = list(self.floor_requests)
        
        if self.current_direction == 1:  # 上行
            # 先處理上方的樓層（由近到遠）
            upper_floors = [f for f in requests if f > self.current_floor]
            upper_floors.sort()
            
            # 再處理下方的樓層（由遠到近）
            lower_floors = [f for f in requests if f < self.current_floor]
            lower_floors.sort(reverse=True)
            
            self.pending_floors = upper_floors + lower_floors
            
        elif self.current_direction == -1:  # 下行
            # 先處理下方的樓層（由近到遠）
            lower_floors = [f for f in requests if f < self.current_floor]
            lower_floors.sort(reverse=True)
            
            # 再處理上方的樓層（由近到遠）
            upper_floors = [f for f in requests if f > self.current_floor]
            upper_floors.sort()
            
            self.pending_floors = lower_floors + upper_floors
            
        else:  # 停止狀態，選擇最近的樓層
            requests.sort(key=lambda x: abs(x - self.current_floor))
            self.pending_floors = requests
            
        self.log_message(f"📋 更新停靠順序: {self.pending_floors}")
        
        # 更新GUI顯示
        if self.pending_floors:
            requests_text = " → ".join(map(str, self.pending_floors))
            self.requests_label.config(text=requests_text)
        else:
            self.requests_label.config(text="無")
        
    def can_stop_at_floor(self, floor):
        """檢查電梯是否可以在指定樓層停靠（中途停靠邏輯）"""
        if not self.is_moving:
            return True
            
        # 如果電梯正在移動，檢查是否可以中途停靠
        if self.current_direction == 1:  # 上行
            # 只能停靠在當前樓層上方且目標樓層下方或等於目標樓層的樓層
            return self.current_floor < floor <= self.target_floor
        elif self.current_direction == -1:  # 下行
            # 只能停靠在當前樓層下方且目標樓層上方或等於目標樓層的樓層
            return self.target_floor <= floor < self.current_floor
        else:
            return True
    
    def update_direction_display(self):
        """更新運行方向顯示"""
        if self.current_direction == 1:
            self.direction_label.config(text="🔼 上行", fg="green")
        elif self.current_direction == -1:
            self.direction_label.config(text="🔽 下行", fg="blue")
        else:
            self.direction_label.config(text="⏸️ 停止", fg="gray")
        
    def arrive_at_floor(self, floor):
        """到達樓層處理"""
        # 從請求中移除當前樓層
        if floor in self.floor_requests:
            self.floor_requests.remove(floor)
            self.log_message(f"✅ 到達 {floor} 樓，請求完成")
            
        # 從待停靠列表中移除
        if floor in self.pending_floors:
            self.pending_floors.remove(floor)
            
        # 檢查是否還有其他請求
        if self.floor_requests:
            self.log_message(f"🔄 剩餘請求: {sorted(list(self.floor_requests))}")
            # 延遲1秒後繼續下一個請求（模擬開門時間）
            self.master.after(1000, self.process_next_request)
        else:
            # 所有請求完成
            self.is_moving = False
            self.current_direction = 0
            self.move_status_label.config(text="待命", fg="black")
            self.target_floor = floor
            self.target_floor_label.config(text=str(floor))
            self.log_message(f"🏁 所有請求完成，電梯停在 {floor} 樓")
            self.requests_label.config(text="無")
            # 更新運行方向顯示
            self.update_direction_display()
        
    def emergency_stop(self):
        """緊急停止"""
        if not self.arduino.connected:
            self.log_message("❌ Arduino未連接")
            return
            
        if self.manual_emergency:
            # 解除手動緊急模式
            self.manual_emergency = False
            self.update_emergency_mode()
            self.log_message("✅ 手動緊急模式已解除")
        else:
            # 啟動手動緊急模式
            self.manual_emergency = True
            # 清空所有請求
            self.floor_requests.clear()
            self.pending_floors.clear()
            self.is_moving = False
            self.current_direction = 0
            self.move_status_label.config(text="緊急停止", fg="red")
            self.requests_label.config(text="無")
            # 更新運行方向顯示
            self.update_direction_display()
            self.update_emergency_mode()
            self.log_message("🚨 手動緊急模式啟動，所有請求已清空")
            
    def calibrate_elevator(self):
        """校準電梯"""
        if not self.arduino.connected:
            self.log_message("❌ Arduino未連接，無法校準")
            return
            
        self.log_message("🔧 開始校準電梯位置...")
        self.arduino.calibrate_position()
        
    def test_motor(self):
        """測試馬達"""
        if not self.arduino.connected:
            self.log_message("❌ Arduino未連接，無法測試馬達")
            return
            
        self.log_message("🔧 開始測試馬達...")
        self.arduino.test_motor()
        
    def initialize_elevator(self):
        """初始化電梯到1樓"""
        if not self.arduino.connected:
            self.log_message("❌ Arduino未連接，無法初始化")
            return
            
        self.log_message("🏠 手動初始化電梯到1樓...")
        self.arduino.initialize_elevator()
        
        # 重置GUI狀態
        self.current_floor = 1
        self.target_floor = 1
        self.is_moving = False
        self.emergency_mode = False
        self.current_direction = 0
        self.floor_requests.clear()
        self.pending_floors.clear()
        
        # 更新GUI顯示
        self.current_floor_label.config(text="1")
        self.target_floor_label.config(text="1")
        self.move_status_label.config(text="待命", fg="black")
        self.requests_label.config(text="無")
        self.update_direction_display()
        
        self.log_message("✅ 電梯已初始化到1樓")
        
    def update_status(self):
        """更新狀態"""
        if self.arduino.connected:
            self.arduino.get_status()
        
        # 定期更新
        self.master.after(2000, self.update_status)
        
    def on_position_update(self, floor):
        """處理位置更新"""
        old_floor = self.current_floor
        
        # 立即更新當前樓層顯示（包括移動中的實時更新）
        self.current_floor = floor
        self.current_floor_label.config(text=str(floor))
        
        if old_floor != floor:
            self.log_message(f"📍 電梯位置更新：{old_floor}樓 → {floor}樓")
            
            # 如果是電梯到達目標樓層或請求樓層，觸發到達邏輯
            if floor in self.floor_requests or floor == self.target_floor:
                self.arrive_at_floor(floor)
            else:
                # 如果只是路過的樓層，記錄但不觸發到達邏輯
                self.log_message(f"🚶 電梯路過 {floor} 樓")
        
    def on_status_update(self, current_floor, target_floor, moving, emergency):
        """處理狀態更新"""
        self.current_floor = current_floor
        self.target_floor = target_floor
        self.is_moving = moving
        
        # 更新GUI顯示
        self.current_floor_label.config(text=str(current_floor))
        self.target_floor_label.config(text=str(target_floor))
        
        if moving:
            self.move_status_label.config(text="移動中", fg="orange")
        else:
            self.move_status_label.config(text="待命", fg="black")
        
    def on_arduino_connection_change(self, connected, message):
        """Arduino連接狀態變化回調"""
        if connected:
            self.arduino_status_label.config(
                text=f"🟢 Arduino: 已連接", 
                fg="green"
            )
            self.log_message(f"✅ Arduino連接成功: {message}")
            
            # 自動重置GUI狀態到1樓
            self.current_floor = 1
            self.target_floor = 1
            self.is_moving = False
            self.emergency_mode = False
            self.auto_emergency = False
            self.manual_emergency = False
            self.current_direction = 0
            self.floor_requests.clear()
            self.pending_floors.clear()
            
            # 更新GUI顯示
            self.current_floor_label.config(text="1")
            self.target_floor_label.config(text="1")
            self.move_status_label.config(text="待命", fg="black")
            self.requests_label.config(text="無")
            self.update_direction_display()
            self.update_emergency_mode()
            
            self.log_message("🏠 電梯已自動初始化到1樓，可以開始使用")
        else:
            self.arduino_status_label.config(
                text=f"🔴 Arduino: 未連接", 
                fg="red"
            )
            self.log_message(f"❌ Arduino連接失敗: {message}")
        
    def reconnect_arduino(self):
        """重新連接Arduino"""
        self.reconnect_button.config(state='disabled', text='重連中...')
        self.log_message("🔄 正在重新連接Arduino...")
        
        def do_reconnect():
            success = self.arduino.reconnect()
            self.reconnect_button.config(
                state='normal', 
                text='重新連接'
            )
            if success:
                self.log_message("✅ Arduino重連成功")
            else:
                self.log_message("❌ Arduino重連失敗")
                
        # 在背景執行重連，避免阻塞GUI
        threading.Thread(target=do_reconnect, daemon=True).start()
        
    def on_closing(self):
        """關閉程序"""
        self.log_message("🔌 關閉系統...")
        if hasattr(self, 'arduino'):
            self.arduino.close()
        if hasattr(self, 'cap'):
            self.cap.release()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    sim = SimpleElevatorGUI(root)
    root.protocol("WM_DELETE_WINDOW", sim.on_closing)
    root.mainloop() 