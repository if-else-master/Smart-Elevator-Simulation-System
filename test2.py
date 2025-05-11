import tkinter as tk
from enum import Enum
from collections import deque
import time
import cv2
import numpy as np
from PIL import Image, ImageTk

# 定義按鈕類型和運行方向
class ButtonType(Enum):
    UP = 1
    DOWN = -1
    INTERNAL = 0

class Direction(Enum):
    UP = 1
    DOWN = -1
    IDLE = 0

# 請求類別：包含目標樓層、請求類型及時間戳記
class Request:
    def __init__(self, floor, button_type):
        self.floor = floor
        self.button_type = button_type
        self.timestamp = time.time()

# 電梯模擬控制類別（整合 GUI、電梯動畫、突破量偵測與緊急模式）
class ElevatorControlSim:
    def __init__(self, master):
        self.master = master
        master.title("電梯模擬系統")

        # 建立攝影機物件（預設使用設備 0）
        self.cap = cv2.VideoCapture(0)
        
        # 背景差分器初始化
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16, detectShadows=True)
        
        # 突破量相關參數
        self.penetration_area = 0  # 當前突破面積
        self.total_area = 0  # 畫面總面積
        self.penetration_ratio = 0  # 突破量比例
        self.penetration_threshold = 0.15  # 緊急模式啟動閾值 (15%)
        
        # 初始化前一幀的遮罩
        self.prev_mask = None
        self.baseline_established = False
        self.stabilization_frames = 0
        
        # 顯示畫面的尺寸
        self.display_width = 240  # 縮小顯示尺寸
        self.display_height = 180
        
        # 建立左側畫布，用以顯示電梯井
        self.canvas = tk.Canvas(master, width=300, height=600, bg="white")
        self.canvas.pack(side=tk.LEFT, padx=5, fill=tk.Y)

        # 定義樓層位置：此處樓層 3 在上、1 在下
        self.floor_positions = {1: 500, 2: 300, 3: 100}
        for floor, y in self.floor_positions.items():
            self.canvas.create_line(0, y, 300, y, fill="black")
            self.canvas.create_text(280, y - 10, text=f"樓層 {floor}")

        # 建立電梯圖形（藍色矩形），初始在 1 樓
        self.elevator_width = 50
        self.elevator_height = 50
        initial_x = 125
        initial_y = self.floor_positions[1] - self.elevator_height
        self.elevator_rect = self.canvas.create_rectangle(
            initial_x, initial_y, initial_x + self.elevator_width, initial_y + self.elevator_height, fill="blue"
        )
        self.current_floor = 1
        self.target_floor = None
        self.direction = Direction.IDLE
        self.is_moving_flag = False

        # 請求管理
        self.internal_requests = []
        self.external_requests = []
        self.pending_external_requests = deque()

        # 緊急模式相關：手動觸發、突破量偵測自動觸發與總狀態
        self.full_load = False        # 總緊急模式（滿載）
        self.manual_emergency = False   # 手動觸發狀態
        self.auto_emergency = False     # 自動（突破量偵測）觸發狀態

        # 右側控制面板
        self.control_frame = tk.Frame(master)
        self.control_frame.pack(side=tk.RIGHT, fill=tk.Y, expand=True, padx=5)

        # 建立一個框架來容納攝影機畫面和相關控制項
        self.camera_frame = tk.Frame(self.control_frame)
        self.camera_frame.pack(fill=tk.X, pady=5)

        # 顯示攝影機畫面（帶有突破量資訊）- 尺寸更小
        self.camera_label = tk.Label(self.camera_frame)
        self.camera_label.pack(pady=2)

        # 突破量資訊顯示
        self.penetration_info_label = tk.Label(self.camera_frame, text=f"突破量: {self.penetration_ratio:.2f}%")
        self.penetration_info_label.pack(pady=2)
        
        # 建立控制項框架
        self.controls_frame = tk.Frame(self.control_frame)
        self.controls_frame.pack(fill=tk.X, pady=5)
        
        # 重置背景按鈕
        self.reset_bg_button = tk.Button(
            self.controls_frame, text="重置背景", command=self.reset_background
        )
        self.reset_bg_button.pack(fill=tk.X, padx=5, pady=2)
        
        # 緊急閾值調整滑桿
        tk.Label(self.controls_frame, text="緊急模式閾值 (%):").pack(pady=2)
        self.emergency_slider = tk.Scale(self.controls_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                         command=self.update_emergency_threshold)
        self.emergency_slider.set(self.penetration_threshold * 100)
        self.emergency_slider.pack(fill=tk.X, padx=5, pady=2)

        # 緊急按鈕（手動觸發）
        self.full_load_var = tk.BooleanVar(value=False)
        self.full_load_check = tk.Checkbutton(
            self.controls_frame, text="緊急按鈕", variable=self.full_load_var, command=self.toggle_full_load
        )
        self.full_load_check.pack(pady=5)

        # 建立呼叫按鈕框架
        self.buttons_frame = tk.Frame(self.control_frame)
        self.buttons_frame.pack(fill=tk.X, pady=5)
        
        # 內部呼叫框架
        self.internal_frame = tk.Frame(self.buttons_frame)
        self.internal_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 內部呼叫按鈕（樓層 3,2,1，從上到下排列）
        tk.Label(self.internal_frame, text="內部呼叫").pack(pady=2)
        self.btn_internal_floor3 = tk.Button(
            self.internal_frame, text="3", command=lambda: self.add_request(3, ButtonType.INTERNAL)
        )
        self.btn_internal_floor3.pack(fill=tk.X, padx=2, pady=1)
        self.btn_internal_floor2 = tk.Button(
            self.internal_frame, text="2", command=lambda: self.add_request(2, ButtonType.INTERNAL)
        )
        self.btn_internal_floor2.pack(fill=tk.X, padx=2, pady=1)
        self.btn_internal_floor1 = tk.Button(
            self.internal_frame, text="1", command=lambda: self.add_request(1, ButtonType.INTERNAL)
        )
        self.btn_internal_floor1.pack(fill=tk.X, padx=2, pady=1)

        # 外部呼叫框架
        self.external_frame = tk.Frame(self.buttons_frame)
        self.external_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        
        # 外部呼叫按鈕
        tk.Label(self.external_frame, text="外部呼叫").pack(pady=2)
        self.btn_ext_3_down = tk.Button(
            self.external_frame, text="3↓", width=4, command=lambda: self.add_request(3, ButtonType.DOWN)
        )
        self.btn_ext_3_down.pack(fill=tk.X, padx=2, pady=1)
        self.btn_ext_2_up = tk.Button(
            self.external_frame, text="2↑", width=4, command=lambda: self.add_request(2, ButtonType.UP)
        )
        self.btn_ext_2_up.pack(fill=tk.X, padx=2, pady=1)
        self.btn_ext_2_down = tk.Button(
            self.external_frame, text="2↓", width=4, command=lambda: self.add_request(2, ButtonType.DOWN)
        )
        self.btn_ext_2_down.pack(fill=tk.X, padx=2, pady=1)
        self.btn_ext_1_up = tk.Button(
            self.external_frame, text="1↑", width=4, command=lambda: self.add_request(1, ButtonType.UP)
        )
        self.btn_ext_1_up.pack(fill=tk.X, padx=2, pady=1)

        # 狀態訊息
        self.info_label = tk.Label(self.control_frame, text="狀態：Idle", wraplength=280)
        self.info_label.pack(pady=10)

        # 啟動主迴圈與突破量偵測更新
        self.master.after(100, self.simulation_loop)
        self.master.after(100, self.update_penetration_detection)
    
    # 重置背景
    def reset_background(self):
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16, detectShadows=True)
        self.baseline_established = False
        self.stabilization_frames = 0
        print("背景已重置，將重新建立基準。")
    
    # 更新緊急模式閾值
    def update_emergency_threshold(self, val):
        self.penetration_threshold = float(val) / 100.0

    # 更新總緊急模式：總狀態 = 手動 OR 自動
    def update_emergency_mode(self):
        self.full_load = self.manual_emergency or self.auto_emergency

    # 手動觸發緊急模式：由緊急按鈕決定
    def toggle_full_load(self):
        self.manual_emergency = self.full_load_var.get()
        self.update_emergency_mode()
        if self.manual_emergency:
            print("手動：電梯已進入緊急（滿載）模式。")
        else:
            print("手動：電梯已解除緊急模式。")
            # 緊急解除時，處理暫存的外部請求
            while self.pending_external_requests:
                req = self.pending_external_requests.popleft()
                self.add_request(req.floor, req.button_type)

    # 添加請求（內部或外部）
    def add_request(self, floor, button_type):
        # 如果內部呼叫的目標即為當前樓層則忽略
        if floor == self.current_floor and button_type == ButtonType.INTERNAL:
            print(f"忽略當前樓層 {floor} 的內部請求。")
            return
        new_request = Request(floor, button_type)
        if button_type == ButtonType.INTERNAL:
            if not any(req.floor == floor for req in self.internal_requests):
                self.internal_requests.append(new_request)
                print(f"內部請求：樓層 {floor}")
        else:
            # 外部請求：若已處於緊急模式（無論是手動或自動）則暫存
            if self.full_load:
                self.pending_external_requests.append(new_request)
                print(f"外部請求：樓層 {floor}（緊急模式，暫存）")
            else:
                if not any(req.floor == floor and req.button_type == button_type for req in self.external_requests):
                    self.external_requests.append(new_request)
                    print(f"外部請求：樓層 {floor}，方向：{button_type.name}")
        self.info_label.config(text=f"狀態：{self.get_status_text()}")
        # 若電梯不在移動，則開始處理請求
        if not self.is_moving_flag:
            self.master.after(100, self.process_requests)

    # 回傳目前所有有效請求（緊急模式下僅處理內部請求）
    def get_active_requests(self):
        if self.full_load:
            return self.internal_requests
        return self.internal_requests + self.external_requests

    # 組合狀態文字，並顯示各項狀態
    def get_status_text(self):
        active = self.get_active_requests()
        reqs = "無請求" if not active else ", ".join(f"{req.floor}({req.button_type.name})" for req in active)
        overall = "啟動" if self.full_load else "解除"
        manual = "啟動" if self.manual_emergency else "解除"
        auto = "啟動" if self.auto_emergency else "解除"
        return (f"{'移動中' if self.is_moving_flag else '待命'}（{self.current_floor} 樓），請求：{reqs}；"
                f" 緊急模式(總:{overall}, 手動:{manual}, 自動:{auto})")

    # 根據請求決定下一個停靠樓層與方向
    def process_requests(self):
        active_requests = self.get_active_requests()
        if not active_requests:
            self.info_label.config(text=f"狀態：在 {self.current_floor} 樓待命")
            return
        next_stop = self.get_next_stop()
        if next_stop is not None:
            self.target_floor = next_stop
            if self.target_floor > self.current_floor:
                self.direction = Direction.UP
            elif self.target_floor < self.current_floor:
                self.direction = Direction.DOWN
            else:
                self.direction = Direction.IDLE
            self.info_label.config(text=f"向 {self.target_floor} 樓 {self.direction.name} 行駛")
            self.animate_movement(self.current_floor, self.target_floor, frames=60)
        else:
            self.info_label.config(text="無有效下一站")

    # 選擇距離最近或符合方向優先的停靠樓層
    def get_next_stop(self):
        active_requests = self.get_active_requests()
        if not active_requests:
            return None
        if self.direction == Direction.UP:
            upper_stops = [req.floor for req in active_requests if req.floor > self.current_floor]
            if upper_stops:
                return min(upper_stops)
        elif self.direction == Direction.DOWN:
            lower_stops = [req.floor for req in active_requests if req.floor < self.current_floor]
            if lower_stops:
                return max(lower_stops)
        nearest_stop = min(active_requests, key=lambda req: abs(req.floor - self.current_floor)).floor
        return nearest_stop

    # 到達目標樓層後移除已完成的請求
    def remove_completed_requests(self):
        self.internal_requests = [req for req in self.internal_requests if req.floor != self.current_floor]
        if not self.full_load:
            self.external_requests = [req for req in self.external_requests if req.floor != self.current_floor]

    # 利用 after() 實作動畫：從起始樓層移動到目標樓層（60 幀預設）
    # 移動過程中每約 1 秒（20 幀）檢查新請求，但只考慮方向相同的外部請求（內部請求始終處理）
    def animate_movement(self, start_floor, end_floor, frames):
        self.is_moving_flag = True
        self.anim_start_floor = start_floor
        start_y = self.floor_positions[start_floor] - self.elevator_height
        end_y = self.floor_positions[end_floor] - self.elevator_height
        self.animation_frame = 0
        self.total_frames = frames  # 可能因中途停靠而延長
        self.target_floor = end_floor
        self.dy = (end_y - start_y) / frames

        def step():
            if self.animation_frame < self.total_frames:
                if not self.full_load and self.animation_frame % 20 == 0:
                    active = self.get_active_requests()
                    coords = self.canvas.coords(self.elevator_rect)
                    current_y = coords[1]
                    if self.direction == Direction.UP:
                        possible = []
                        for req in active:
                            if (self.anim_start_floor < req.floor < self.target_floor and
                                req.button_type in (ButtonType.UP, ButtonType.INTERNAL)):
                                stop_y = self.floor_positions[req.floor] - self.elevator_height
                                if current_y > stop_y:
                                    possible.append(req.floor)
                        if possible:
                            new_target = min(possible)
                            if new_target < self.target_floor:
                                print(f"中途請求：改為先停 {new_target} 樓")
                                self.target_floor = new_target
                                remaining_frames = 20
                                self.total_frames = self.animation_frame + remaining_frames
                                new_end_y = self.floor_positions[new_target] - self.elevator_height
                                self.dy = (new_end_y - current_y) / remaining_frames
                    elif self.direction == Direction.DOWN:
                        possible = []
                        for req in active:
                            if (self.anim_start_floor > req.floor > self.target_floor and
                                req.button_type in (ButtonType.DOWN, ButtonType.INTERNAL)):
                                stop_y = self.floor_positions[req.floor] - self.elevator_height
                                if current_y < stop_y:
                                    possible.append(req.floor)
                        if possible:
                            new_target = max(possible)
                            if new_target > self.target_floor:
                                print(f"中途請求：改為先停 {new_target} 樓")
                                self.target_floor = new_target
                                remaining_frames = 20
                                self.total_frames = self.animation_frame + remaining_frames
                                new_end_y = self.floor_positions[new_target] - self.elevator_height
                                self.dy = (new_end_y - current_y) / remaining_frames

                self.canvas.move(self.elevator_rect, 0, self.dy)
                self.animation_frame += 1
                self.master.after(50, step)
            else:
                coords = self.canvas.coords(self.elevator_rect)
                final_y = self.floor_positions[self.target_floor] - self.elevator_height
                self.canvas.coords(self.elevator_rect, coords[0], final_y,
                                   coords[0] + self.elevator_width, final_y + self.elevator_height)
                self.current_floor = self.target_floor
                self.is_moving_flag = False
                self.remove_completed_requests()
                self.info_label.config(text=f"已到 {self.current_floor} 樓。{self.get_status_text()}")
                if not self.full_load and self.pending_external_requests:
                    while self.pending_external_requests:
                        req = self.pending_external_requests.popleft()
                        self.add_request(req.floor, req.button_type)
                self.master.after(500, self.process_requests)
        step()

    # 持續更新突破量偵測：計算畫面中移動物體佔用的面積
    def update_penetration_detection(self):
        ret, frame = self.cap.read()
        if ret:
            # 建立初始的基準畫面
            if not self.baseline_established:
                self.stabilization_frames += 1
                # 忽略前 10 幀，讓背景減法器先學習背景
                if self.stabilization_frames > 10:
                    self.baseline_established = True
                    print("背景基準已建立完成。")
                # 先套用背景差分器學習背景
                self.background_subtractor.apply(frame)
                
                # 建立影像複本
                display_frame = frame.copy()
                # 顯示建立基準中的訊息
                cv2.putText(display_frame, f"建立背景基準中 ({self.stabilization_frames}/10)...", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # 調整顯示大小
                display_frame = cv2.resize(display_frame, (self.display_width, self.display_height))
                
                # 轉換為 Tkinter 可顯示的格式
                rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(rgb_frame)
                photo = ImageTk.PhotoImage(image)
                self.camera_label.config(image=photo)
                self.camera_label.image = photo
                
                self.master.after(100, self.update_penetration_detection)
                return
            
            # 計算總面積
            self.total_area = frame.shape[0] * frame.shape[1]
            
            # 應用背景差分器
            fg_mask = self.background_subtractor.apply(frame)
            
            # 處理前景遮罩以減少雜訊
            # 先使用高斯模糊
            fg_mask = cv2.GaussianBlur(fg_mask, (5, 5), 0)
            
            # 二值化，將陰影去除
            _, fg_mask = cv2.threshold(fg_mask, 128, 255, cv2.THRESH_BINARY)
            
            # 形態學操作 (開運算然後閉運算) 去除小雜訊並填補空洞
            kernel = np.ones((5, 5), np.uint8)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
            
            # 計算非零像素（突破面積）
            self.penetration_area = cv2.countNonZero(fg_mask)
            
            # 計算突破量比例
            self.penetration_ratio = (self.penetration_area / self.total_area) * 100
            
            # 更新突破量顯示
            self.penetration_info_label.config(text=f"突破量: {self.penetration_ratio:.2f}%")
            
            # 繪製顯示影像
            # 創建有顏色的前景遮罩 (用於視覺化)
            fg_mask_colored = cv2.cvtColor(fg_mask, cv2.COLOR_GRAY2BGR)
            fg_mask_colored[np.where((fg_mask_colored == [255, 255, 255]).all(axis=2))] = [0, 0, 255]  # 紅色顯示前景
            
            # 混合原始影像和前景遮罩
            alpha = 0.5
            visualization = cv2.addWeighted(frame, 1, fg_mask_colored, alpha, 0)
            
            # 添加突破量資訊
            cv2.putText(visualization, f"突破量: {self.penetration_ratio:.2f}%", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 如果突破量超過設定閾值，顯示警告
            if self.penetration_ratio / 100 >= self.penetration_threshold:
                cv2.putText(visualization, "⚠️ 物體過多", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # 自動觸發緊急模式
                if not self.auto_emergency:
                    print(f"偵測到突破量 {self.penetration_ratio:.2f}% 已超過閾值 {self.penetration_threshold * 100:.0f}%，自動啟動緊急模式")
                self.auto_emergency = True
            else:
                # 解除自動緊急模式
                if self.auto_emergency:
                    print(f"偵測到突破量 {self.penetration_ratio:.2f}% 已低於閾值 {self.penetration_threshold * 100:.0f}%，自動解除緊急模式")
                self.auto_emergency = False
            
            self.update_emergency_mode()
            
            # 調整顯示大小
            visualization = cv2.resize(visualization, (self.display_width, self.display_height))
            
            # 轉換為 Tkinter 可顯示的格式
            rgb_frame = cv2.cvtColor(visualization, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_frame)
            photo = ImageTk.PhotoImage(image)
            self.camera_label.config(image=photo)
            self.camera_label.image = photo
            
        self.master.after(100, self.update_penetration_detection)

    # 主迴圈更新狀態顯示
    def simulation_loop(self):
        self.info_label.config(text=f"狀態：{self.get_status_text()}")
        self.master.after(200, self.simulation_loop)

    # 關閉視窗前釋放攝影機資源
    def on_closing(self):
        self.cap.release()
        self.master.destroy()

# 主程式
if __name__ == "__main__":
    root = tk.Tk()
    sim = ElevatorControlSim(root)
    root.protocol("WM_DELETE_WINDOW", sim.on_closing)
    root.mainloop()