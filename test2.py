import tkinter as tk
from enum import Enum
from collections import deque
import time
import cv2
import numpy as np
from PIL import Image, ImageTk

class ButtonType(Enum):
    UP = 1
    DOWN = -1
    INTERNAL = 0

class Direction(Enum):
    UP = 1
    DOWN = -1
    IDLE = 0

class Request:
    def __init__(self, floor, button_type):
        self.floor = floor
        self.button_type = button_type
        self.timestamp = time.time()

class ElevatorControlSim:
    def __init__(self, master):
        self.master = master
        master.title("電梯模擬系統")
        self.cap = cv2.VideoCapture(0)
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16, detectShadows=True)    
        self.penetration_area = 0 
        self.total_area = 0
        self.penetration_ratio = 0 
        self.penetration_threshold = 0.15 
        self.prev_mask = None
        self.baseline_established = False
        self.stabilization_frames = 0
        self.display_width = 240
        self.display_height = 180
        
        self.canvas = tk.Canvas(master, width=300, height=600, bg="white")
        self.canvas.pack(side=tk.LEFT, padx=5, fill=tk.Y)

        self.floor_positions = {1: 500, 2: 300, 3: 100}
        for floor, y in self.floor_positions.items():
            self.canvas.create_line(0, y, 300, y, fill="black")
            self.canvas.create_text(280, y - 10, text=f"樓層 {floor}")

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

        self.internal_requests = []
        self.external_requests = []
        self.pending_external_requests = deque()

        self.full_load = False        
        self.manual_emergency = False   
        self.auto_emergency = False     

        self.control_frame = tk.Frame(master)
        self.control_frame.pack(side=tk.RIGHT, fill=tk.Y, expand=True, padx=5)

        self.camera_frame = tk.Frame(self.control_frame)
        self.camera_frame.pack(fill=tk.X, pady=5)

        self.camera_label = tk.Label(self.camera_frame)
        self.camera_label.pack(pady=2)

        self.penetration_info_label = tk.Label(self.camera_frame, text=f"突破量: {self.penetration_ratio:.2f}%")
        self.penetration_info_label.pack(pady=2)
        
        self.controls_frame = tk.Frame(self.control_frame)
        self.controls_frame.pack(fill=tk.X, pady=5)
        
        self.reset_bg_button = tk.Button(
            self.controls_frame, text="重置背景", command=self.reset_background
        )
        self.reset_bg_button.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(self.controls_frame, text="緊急模式閾值 (%):").pack(pady=2)
        self.emergency_slider = tk.Scale(self.controls_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                         command=self.update_emergency_threshold)
        self.emergency_slider.set(self.penetration_threshold * 100)
        self.emergency_slider.pack(fill=tk.X, padx=5, pady=2)

        self.full_load_var = tk.BooleanVar(value=False)
        self.full_load_check = tk.Checkbutton(
            self.controls_frame, text="緊急按鈕", variable=self.full_load_var, command=self.toggle_full_load
        )
        self.full_load_check.pack(pady=5)

        self.buttons_frame = tk.Frame(self.control_frame)
        self.buttons_frame.pack(fill=tk.X, pady=5)
        
        self.internal_frame = tk.Frame(self.buttons_frame)
        self.internal_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
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

        self.external_frame = tk.Frame(self.buttons_frame)
        self.external_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        
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

        self.info_label = tk.Label(self.control_frame, text="狀態：Idle", wraplength=280)
        self.info_label.pack(pady=10)

        self.master.after(100, self.simulation_loop)
        self.master.after(100, self.update_penetration_detection)
    
    def reset_background(self):
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16, detectShadows=True)
        self.baseline_established = False
        self.stabilization_frames = 0
        print("背景已重置，將重新建立基準。")
    
    def update_emergency_threshold(self, val):
        self.penetration_threshold = float(val) / 100.0

    def update_emergency_mode(self):
        self.full_load = self.manual_emergency or self.auto_emergency

    def toggle_full_load(self):
        prev_emergency = self.full_load
        self.manual_emergency = self.full_load_var.get()
        self.update_emergency_mode()
        
        if self.manual_emergency:
            print("🚨 手動：電梯已進入緊急模式 - 等待緊急內部請求")
        else:
            print("✅ 手動：電梯已解除緊急模式")
            # 如果之前是緊急模式，現在解除了，需要恢復正常運作
            if prev_emergency:
                print("電梯從緊急待命狀態恢復正常運作")
                # 處理暫存的外部請求
                if self.pending_external_requests:
                    pending_count = len(self.pending_external_requests)
                    print(f"重新處理 {pending_count} 個暫存的外部請求")
                    while self.pending_external_requests:
                        req = self.pending_external_requests.popleft()
                        self.add_request(req.floor, req.button_type)
                # 如果電梯閒置，嘗試處理請求
                if not self.is_moving_flag:
                    self.master.after(100, self.process_requests)

    def add_request(self, floor, button_type):
        if floor == self.current_floor and button_type == ButtonType.INTERNAL:
            print(f"忽略當前樓層 {floor} 的內部請求。")
            return
            
        new_request = Request(floor, button_type)
        
        if button_type == ButtonType.INTERNAL:
            if self.full_load:
                # 緊急模式下，只接受第一個內部請求
                if len(self.internal_requests) == 0:
                    self.internal_requests.append(new_request)
                    print(f"緊急模式：接受緊急內部請求 - 樓層 {floor}")
                else:
                    print(f"緊急模式：忽略額外的內部請求 - 樓層 {floor}（緊急救援進行中）")
                    return
            else:
                # 正常模式下的內部請求處理
                if not any(req.floor == floor for req in self.internal_requests):
                    self.internal_requests.append(new_request)
                    print(f"內部請求：樓層 {floor}")
        else:
            # 外部請求處理
            if self.full_load:
                self.pending_external_requests.append(new_request)
                print(f"外部請求：樓層 {floor}（緊急模式，暫存）")
            else:
                if not any(req.floor == floor and req.button_type == button_type for req in self.external_requests):
                    self.external_requests.append(new_request)
                    print(f"外部請求：樓層 {floor}，方向：{button_type.name}")
                    
        self.info_label.config(text=f"狀態：{self.get_status_text()}")
        if not self.is_moving_flag:
            self.master.after(100, self.process_requests)

    def get_active_requests(self):
        if self.full_load:
            return self.internal_requests
        return self.internal_requests + self.external_requests

    def get_status_text(self):
        if self.full_load:
            # 緊急模式下的狀態顯示
            if len(self.internal_requests) == 0:
                return f"🚨 緊急模式：在 {self.current_floor} 樓待命，等待緊急內部請求"
            else:
                target = self.internal_requests[0].floor
                if self.is_moving_flag:
                    return f"🚨 緊急救援：前往 {target} 樓"
                else:
                    return f"🚨 緊急模式：準備前往 {target} 樓"
        else:
            # 正常模式下的狀態顯示
            active = self.get_active_requests()
            reqs = "無請求" if not active else ", ".join(f"{req.floor}({req.button_type.name})" for req in active)
            overall = "啟動" if self.full_load else "解除"
            manual = "啟動" if self.manual_emergency else "解除"
            auto = "啟動" if self.auto_emergency else "解除"
            return (f"{'移動中' if self.is_moving_flag else '待命'}（{self.current_floor} 樓），請求：{reqs}；"
                    f" 緊急模式(總:{overall}, 手動:{manual}, 自動:{auto})")

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

    def get_next_stop(self):
        active_requests = self.get_active_requests()
        if not active_requests:
            return None
        
        # 在緊急模式下，優化內部請求的處理順序
        if self.full_load:
            return self.get_next_internal_stop(active_requests)
        
        # 非緊急模式下的原有邏輯
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
    
    def get_next_internal_stop(self, internal_requests):
        """緊急模式下的內部請求處理邏輯 - 只處理第一個請求，直達目標樓層"""
        if not internal_requests:
            return None
        
        # 緊急模式下只處理第一個內部請求，直接前往該樓層
        # 這代表有人遇到緊急情況需要快速前往特定樓層
        target_floor = internal_requests[0].floor
        print(f"緊急模式：直達 {target_floor} 樓（緊急救援）")
        return target_floor

    def remove_completed_requests(self):
        self.internal_requests = [req for req in self.internal_requests if req.floor != self.current_floor]
        if not self.full_load:
            self.external_requests = [req for req in self.external_requests if req.floor != self.current_floor]

    def animate_movement(self, start_floor, end_floor, frames):
        self.is_moving_flag = True
        self.anim_start_floor = start_floor
        start_y = self.floor_positions[start_floor] - self.elevator_height
        end_y = self.floor_positions[end_floor] - self.elevator_height
        self.animation_frame = 0
        self.total_frames = frames
        self.target_floor = end_floor
        self.dy = (end_y - start_y) / frames

        def step():
            if self.animation_frame < self.total_frames:
                # 緊急模式下不允許中途停靠，直達目標樓層
                if not self.full_load and self.animation_frame % 20 == 0:
                    active = self.get_active_requests()
                    coords = self.canvas.coords(self.elevator_rect)
                    current_y = coords[1]
                    if self.direction == Direction.UP:
                        possible = []
                        for req in active:
                            if req.button_type in (ButtonType.UP, ButtonType.INTERNAL):
                                if (self.anim_start_floor < req.floor < self.target_floor):
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
                            if req.button_type in (ButtonType.DOWN, ButtonType.INTERNAL):
                                if (self.anim_start_floor > req.floor > self.target_floor):
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
                print(f"電梯已到達 {self.current_floor} 樓")
                
                # 如果是緊急模式，清除所有內部請求並等待緊急模式解除
                if self.full_load:
                    # 緊急救援完成，清除所有內部請求
                    self.internal_requests.clear()
                    print("🚨 緊急救援完成！電梯將在此樓層待命，等待緊急情況解除")
                    self.info_label.config(text=f"緊急救援完成 - 在 {self.current_floor} 樓待命")
                    return  # 不再處理其他請求，直到緊急模式解除
                
                self.info_label.config(text=f"已到 {self.current_floor} 樓。{self.get_status_text()}")
                
                # 如果不是緊急模式且有暫存的外部請求，重新加入處理
                if not self.full_load and self.pending_external_requests:
                    pending_count = len(self.pending_external_requests)
                    print(f"緊急模式已解除，重新處理 {pending_count} 個暫存的外部請求")
                    while self.pending_external_requests:
                        req = self.pending_external_requests.popleft()
                        self.add_request(req.floor, req.button_type)
                
                self.master.after(500, self.process_requests)
        step()

    def update_penetration_detection(self):
        ret, frame = self.cap.read()
        if ret:
            if not self.baseline_established:
                self.stabilization_frames += 1
                if self.stabilization_frames > 10:
                    self.baseline_established = True
                    print("背景基準已建立完成。")
                self.background_subtractor.apply(frame)
                
                display_frame = frame.copy()
                cv2.putText(display_frame, f"建立背景基準中 ({self.stabilization_frames}/10)...", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                display_frame = cv2.resize(display_frame, (self.display_width, self.display_height))
                
                rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(rgb_frame)
                photo = ImageTk.PhotoImage(image)
                self.camera_label.config(image=photo)
                self.camera_label.image = photo
                
                self.master.after(100, self.update_penetration_detection)
                return
            
            self.total_area = frame.shape[0] * frame.shape[1]
            
            fg_mask = self.background_subtractor.apply(frame)
            
            fg_mask = cv2.GaussianBlur(fg_mask, (5, 5), 0)
            
            _, fg_mask = cv2.threshold(fg_mask, 128, 255, cv2.THRESH_BINARY)
            
            kernel = np.ones((5, 5), np.uint8)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
            
            self.penetration_area = cv2.countNonZero(fg_mask)
            
            self.penetration_ratio = (self.penetration_area / self.total_area) * 100
            
            self.penetration_info_label.config(text=f"突破量: {self.penetration_ratio:.2f}%")
            
            fg_mask_colored = cv2.cvtColor(fg_mask, cv2.COLOR_GRAY2BGR)
            fg_mask_colored[np.where((fg_mask_colored == [255, 255, 255]).all(axis=2))] = [0, 0, 255]
            
            alpha = 0.5
            visualization = cv2.addWeighted(frame, 1, fg_mask_colored, alpha, 0)
            
            cv2.putText(visualization, f"突破量: {self.penetration_ratio:.2f}%", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if self.penetration_ratio / 100 >= self.penetration_threshold:
                cv2.putText(visualization, "⚠️ 物體過多", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                if not self.auto_emergency:
                    print(f"偵測到突破量 {self.penetration_ratio:.2f}% 已超過閾值 {self.penetration_threshold * 100:.0f}%")
                    print("🚨 自動啟動緊急模式 - 等待緊急內部請求")
                self.auto_emergency = True
            else:
                if self.auto_emergency:
                    prev_emergency = self.full_load
                    print(f"偵測到突破量 {self.penetration_ratio:.2f}% 已低於閾值 {self.penetration_threshold * 100:.0f}%")
                    print("✅ 自動解除緊急模式 - 電梯將恢復正常運作")
                    self.auto_emergency = False
                    
                    # 更新緊急模式狀態
                    self.update_emergency_mode()
                    
                    # 如果之前是緊急模式，現在解除了，需要恢復正常運作
                    if prev_emergency and not self.full_load:
                        print("電梯從緊急待命狀態恢復正常運作")
                        # 處理暫存的外部請求
                        if self.pending_external_requests:
                            pending_count = len(self.pending_external_requests)
                            print(f"重新處理 {pending_count} 個暫存的外部請求")
                            while self.pending_external_requests:
                                req = self.pending_external_requests.popleft()
                                self.add_request(req.floor, req.button_type)
                        # 如果電梯閒置，嘗試處理請求
                        if not self.is_moving_flag:
                            self.master.after(100, self.process_requests)
            
            self.update_emergency_mode()
            
            visualization = cv2.resize(visualization, (self.display_width, self.display_height))
            
            rgb_frame = cv2.cvtColor(visualization, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_frame)
            photo = ImageTk.PhotoImage(image)
            self.camera_label.config(image=photo)
            self.camera_label.image = photo
            
        self.master.after(100, self.update_penetration_detection)

    def simulation_loop(self):
        self.info_label.config(text=f"狀態：{self.get_status_text()}")
        self.master.after(200, self.simulation_loop)

    def on_closing(self):
        self.cap.release()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    sim = ElevatorControlSim(root)
    root.protocol("WM_DELETE_WINDOW", sim.on_closing)
    root.mainloop()