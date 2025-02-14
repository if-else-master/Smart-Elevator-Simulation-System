# import tkinter as tk
# from enum import Enum
# from collections import deque
# import time

# # 定義按鈕類型和運行方向
# class ButtonType(Enum):
#     UP = 1
#     DOWN = -1
#     INTERNAL = 0

# class Direction(Enum):
#     UP = 1
#     DOWN = -1
#     IDLE = 0

# # 請求類別，包含目標樓層、請求類型及時間戳記
# class Request:
#     def __init__(self, floor, button_type):
#         self.floor = floor
#         self.button_type = button_type
#         self.timestamp = time.time()

# # 電梯模擬控制類別（利用 Tkinter 畫面顯示動畫與按鈕）
# class ElevatorControlSim:
#     def __init__(self, master):
#         self.master = master
#         master.title("電梯模擬系統")

#         # 建立畫布 (Canvas) 作為電梯井顯示區
#         self.canvas = tk.Canvas(master, width=300, height=600, bg="white")
#         self.canvas.pack(side=tk.LEFT)

#         # 定義各樓層的 Y 座標（從上至下，數值越大代表畫面下方）
#         # 此處樓層 3 在上，樓層 1 在下
#         self.floor_positions = {1: 500, 2: 300, 3: 100}
#         for floor, y in self.floor_positions.items():
#             self.canvas.create_line(0, y, 300, y, fill="black")
#             self.canvas.create_text(280, y - 10, text=f"樓層 {floor}")

#         # 定義電梯（以矩形表示）大小與初始位置（初始在 1 樓）
#         self.elevator_width = 50
#         self.elevator_height = 50
#         initial_x = 125
#         initial_y = self.floor_positions[1] - self.elevator_height
#         self.elevator_rect = self.canvas.create_rectangle(
#             initial_x, initial_y, initial_x + self.elevator_width, initial_y + self.elevator_height, fill="blue"
#         )     
#         self.current_floor = 1  # 電梯目前所在樓層
#         self.target_floor = None
#         self.direction = Direction.IDLE
#         self.is_moving_flag = False

#         # 請求管理：內部與外部請求，還有暫存的外部請求（當滿載時暫存）
#         self.internal_requests = []
#         self.external_requests = []
#         self.pending_external_requests = deque()

#         # 模擬滿載狀態（預設為 False）
#         self.full_load = False

#         # 建立右側控制面板，包含按鈕與狀態顯示
#         self.control_frame = tk.Frame(master)
#         self.control_frame.pack(side=tk.RIGHT, fill=tk.Y)

#         # 模擬「緊急按鈕」Checkbutton（打勾表示滿載，此時外部呼叫不立即回應）
#         self.full_load_var = tk.BooleanVar(value=False)
#         self.full_load_check = tk.Checkbutton(
#             self.control_frame, text="緊急按鈕", variable=self.full_load_var, command=self.toggle_full_load
#         )
#         self.full_load_check.pack(pady=10)

#         # 內部請求按鈕（電梯內的樓層選擇）   
#         tk.Label(self.control_frame, text="內部呼叫").pack(pady=5)         
#         # 為方便觀察，這裡將樓層順序從上到下排列（3、2、1）
#         self.btn_internal_floor3 = tk.Button(
#             self.control_frame, text="3", command=lambda: self.add_request(3, ButtonType.INTERNAL)
#         )
#         self.btn_internal_floor3.pack(fill=tk.X, padx=5, pady=2)    
#         self.btn_internal_floor2 = tk.Button(
#             self.control_frame, text="2", command=lambda: self.add_request(2, ButtonType.INTERNAL)
#         )
#         self.btn_internal_floor2.pack(fill=tk.X, padx=5, pady=2)               
#         self.btn_internal_floor1 = tk.Button(
#             self.control_frame, text="1", command=lambda: self.add_request(1, ButtonType.INTERNAL)
#         )
#         self.btn_internal_floor1.pack(fill=tk.X, padx=5, pady=2)       

#         # 外部請求按鈕（各樓層的上／下呼叫）
#         tk.Label(self.control_frame, text="外部呼叫").pack(pady=5)   
#         # 樓層 3 只有下呼叫
#         self.btn_ext_3_down = tk.Button(
#             self.control_frame, text="3 樓 下", command=lambda: self.add_request(3, ButtonType.DOWN)
#         )
#         self.btn_ext_3_down.pack(fill=tk.X, padx=5, pady=2)    
#         # 樓層 2 同時有上與下
#         self.btn_ext_2_up = tk.Button(
#             self.control_frame, text="2 樓 上", command=lambda: self.add_request(2, ButtonType.UP)
#         )
#         self.btn_ext_2_up.pack(fill=tk.X, padx=5, pady=2)
#         self.btn_ext_2_down = tk.Button(
#             self.control_frame, text="2 樓 下", command=lambda: self.add_request(2, ButtonType.DOWN)
#         )
#         self.btn_ext_2_down.pack(fill=tk.X, padx=5, pady=2)        
#         # 樓層 1 只有上呼叫
#         self.btn_ext_1_up = tk.Button(
#             self.control_frame, text="1 樓 上", command=lambda: self.add_request(1, ButtonType.UP)
#         )
#         self.btn_ext_1_up.pack(fill=tk.X, padx=5, pady=2)
#         # 狀態訊息顯示
#         self.info_label = tk.Label(self.control_frame, text="狀態：Idle")
#         self.info_label.pack(pady=20)

#         # 啟動定時更新的主迴圈
#         self.master.after(100, self.simulation_loop)

#     # 當緊急按鈕切換時觸發
#     def toggle_full_load(self):
#         self.full_load = self.full_load_var.get()
#         if self.full_load:
#             print("電梯已進入緊急（滿載）模式。")
#         else:
#             print("電梯已解除緊急模式。")
#             # 當緊急模式解除時，將暫存的外部請求加入處理
#             while self.pending_external_requests:
#                 req = self.pending_external_requests.popleft()
#                 self.add_request(req.floor, req.button_type)

#     # 添加請求（內部或外部）
#     def add_request(self, floor, button_type):
#         # 若內部請求的目標就是當前樓層，則忽略
#         if floor == self.current_floor and button_type == ButtonType.INTERNAL:
#             print(f"忽略當前樓層 {floor} 的內部請求。")
#             return
#         new_request = Request(floor, button_type)
#         if button_type == ButtonType.INTERNAL:
#             if not any(req.floor == floor for req in self.internal_requests):
#                 self.internal_requests.append(new_request)
#                 print(f"內部請求：樓層 {floor}")
#         else:
#             # 如果處於緊急模式，外部請求暫存起來
#             if self.full_load:
#                 self.pending_external_requests.append(new_request)
#                 print(f"外部請求：樓層 {floor}（緊急模式，暫存）")
#             else:
#                 if not any(req.floor == floor and req.button_type == button_type for req in self.external_requests):
#                     self.external_requests.append(new_request)
#                     print(f"外部請求：樓層 {floor}，方向：{button_type.name}")
#         self.info_label.config(text=f"狀態：{self.get_status_text()}")
#         # 若電梯目前不在移動，則開始處理請求
#         if not self.is_moving_flag:
#             self.master.after(100, self.process_requests)

#     # 回傳目前所有有效的請求（緊急模式下只處理內部請求）
#     def get_active_requests(self):
#         if self.full_load:
#             return self.internal_requests
#         return self.internal_requests + self.external_requests

#     # 組合狀態文字，用於 info_label 顯示
#     def get_status_text(self):
#         active = self.get_active_requests()
#         if not active:
#             return f"在 {self.current_floor} 樓待命"
#         reqs = ", ".join(f"{req.floor}({req.button_type.name})" for req in active)
#         return f"{'移動中' if self.is_moving_flag else '待命'}（{self.current_floor} 樓），請求：{reqs}"

#     # 處理請求，決定下一個停靠樓層與方向
#     def process_requests(self):
#         active_requests = self.get_active_requests()
#         if not active_requests:
#             self.info_label.config(text=f"狀態：在 {self.current_floor} 樓待命")
#             return
#         next_stop = self.get_next_stop()
#         if next_stop is not None:
#             self.target_floor = next_stop
#             if self.target_floor > self.current_floor:
#                 self.direction = Direction.UP
#             elif self.target_floor < self.current_floor:
#                 self.direction = Direction.DOWN
#             else:
#                 self.direction = Direction.IDLE
#             self.info_label.config(text=f"向 {self.target_floor} 樓 {self.direction.name} 行駛")
#             self.animate_movement(self.current_floor, self.target_floor, frames=60)
#         else:
#             self.info_label.config(text="無有效下一站")

#     # 根據目前請求決定下一個停靠樓層
#     def get_next_stop(self):
#         active_requests = self.get_active_requests()
#         if not active_requests:
#             return None
#         # 若已經在向上移動，優先找上方請求
#         if self.direction == Direction.UP:
#             upper_stops = [req.floor for req in active_requests if req.floor > self.current_floor]
#             if upper_stops:
#                 return min(upper_stops)
#         # 若在向下移動，則優先找下方請求
#         elif self.direction == Direction.DOWN:
#             lower_stops = [req.floor for req in active_requests if req.floor < self.current_floor]
#             if lower_stops:
#                 return max(lower_stops)
#         # 否則選擇距離最近的樓層
#         nearest_stop = min(active_requests, key=lambda req: abs(req.floor - self.current_floor)).floor
#         return nearest_stop

#     # 到達目標樓層後移除已完成的請求
#     def remove_completed_requests(self):
#         self.internal_requests = [req for req in self.internal_requests if req.floor != self.current_floor]
#         if not self.full_load:
#             self.external_requests = [req for req in self.external_requests if req.floor != self.current_floor]

#     # 利用 after() 實作動畫：從起始樓層移動到目標樓層，總共 frames 幀（本例設定 60 幀）
#     # 在動畫移動過程中，每約 1 秒（20 幀）檢查是否有新請求，
#     # 但只考慮移動方向相同的外部請求（內部請求始終處理）。
#     def animate_movement(self, start_floor, end_floor, frames):
#         self.is_moving_flag = True
#         # 記錄啟動移動時的起始樓層，用於判斷中途請求是否介於原本起點與目標之間
#         self.anim_start_floor = start_floor
#         start_y = self.floor_positions[start_floor] - self.elevator_height
#         end_y = self.floor_positions[end_floor] - self.elevator_height
#         self.animation_frame = 0
#         self.total_frames = frames  # 總幀數（可能因中途停靠而延長）
#         # 將 target_floor 設為目前動畫段的目標
#         self.target_floor = end_floor
#         self.dy = (end_y - start_y) / frames

#         def step():
#             if self.animation_frame < self.total_frames:
#                 # 每約 1 秒（20 幀）檢查一次中途請求（若電梯未緊急）
#                 if not self.full_load and self.animation_frame % 20 == 0:
#                     active = self.get_active_requests()
#                     coords = self.canvas.coords(self.elevator_rect)
#                     current_y = coords[1]  # 電梯目前上邊緣位置
#                     # 檢查上行的中途停靠：只考慮方向為 UP 或內部請求
#                     if self.direction == Direction.UP:
#                         possible = []
#                         for req in active:
#                             if (self.anim_start_floor < req.floor < self.target_floor and
#                                 req.button_type in (ButtonType.UP, ButtonType.INTERNAL)):
#                                 stop_y = self.floor_positions[req.floor] - self.elevator_height
#                                 if current_y > stop_y:  # 上行：尚未到達
#                                     possible.append(req.floor)
#                         if possible:
#                             new_target = min(possible)
#                             if new_target < self.target_floor:
#                                 print(f"中途請求：改為先停 {new_target} 樓")
#                                 self.target_floor = new_target
#                                 remaining_frames = 20
#                                 self.total_frames = self.animation_frame + remaining_frames
#                                 new_end_y = self.floor_positions[new_target] - self.elevator_height
#                                 self.dy = (new_end_y - current_y) / remaining_frames
#                     # 檢查下行的中途停靠：只考慮方向為 DOWN 或內部請求
#                     elif self.direction == Direction.DOWN:
#                         possible = []
#                         for req in active:
#                             if (self.anim_start_floor > req.floor > self.target_floor and
#                                 req.button_type in (ButtonType.DOWN, ButtonType.INTERNAL)):
#                                 stop_y = self.floor_positions[req.floor] - self.elevator_height
#                                 if current_y < stop_y:  # 下行：尚未到達
#                                     possible.append(req.floor)
#                         if possible:
#                             new_target = max(possible)
#                             if new_target > self.target_floor:
#                                 print(f"中途請求：改為先停 {new_target} 樓")
#                                 self.target_floor = new_target
#                                 remaining_frames = 20
#                                 self.total_frames = self.animation_frame + remaining_frames
#                                 new_end_y = self.floor_positions[new_target] - self.elevator_height
#                                 self.dy = (new_end_y - current_y) / remaining_frames

#                 self.canvas.move(self.elevator_rect, 0, self.dy)
#                 self.animation_frame += 1
#                 self.master.after(50, step)
#             else:
#                 # 動畫結束，強制將電梯位置修正到目標位置
#                 coords = self.canvas.coords(self.elevator_rect)
#                 final_y = self.floor_positions[self.target_floor] - self.elevator_height
#                 self.canvas.coords(self.elevator_rect, coords[0], final_y,
#                                    coords[0] + self.elevator_width, final_y + self.elevator_height)
#                 self.current_floor = self.target_floor
#                 self.is_moving_flag = False
#                 self.remove_completed_requests()
#                 self.info_label.config(text=f"已到 {self.current_floor} 樓。{self.get_status_text()}")
#                 # 當緊急模式解除且有暫存的外部請求時，將其加入
#                 if not self.full_load and self.pending_external_requests:
#                     while self.pending_external_requests:
#                         req = self.pending_external_requests.popleft()
#                         self.add_request(req.floor, req.button_type)
#                 # 過一會兒再檢查下一個請求
#                 self.master.after(500, self.process_requests)
#         step()

#     # 主迴圈，每隔一段時間更新狀態顯示
#     def simulation_loop(self):
#         self.info_label.config(text=f"狀態：{self.get_status_text()}")
#         self.master.after(200, self.simulation_loop)

# # 主程式：建立 Tk 主視窗並啟動模擬
# if __name__ == "__main__":
#     root = tk.Tk()
#     sim = ElevatorControlSim(root)
#     root.mainloop()


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

# 電梯模擬控制類別（整合 GUI、電梯動畫、紅色辨識與緊急模式）
class ElevatorControlSim:
    def __init__(self, master):
        self.master = master
        master.title("電梯模擬系統")

        # 建立攝影機物件（預設使用設備 0）
        self.cap = cv2.VideoCapture(0)

        # 建立左側畫布，用以顯示電梯井
        self.canvas = tk.Canvas(master, width=300, height=600, bg="white")
        self.canvas.pack(side=tk.LEFT)

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

        # 緊急模式相關：手動觸發、紅色偵測自動觸發與總狀態
        self.full_load = False        # 總緊急模式（滿載）
        self.manual_emergency = False   # 手動觸發狀態
        self.auto_emergency = False     # 自動（紅色偵測）觸發狀態

        # 右側控制面板
        self.control_frame = tk.Frame(master)
        self.control_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # 顯示攝影機畫面（包含紅色區域）
        self.camera_label = tk.Label(self.control_frame)
        self.camera_label.pack(pady=5)

        # 紅色面積資訊顯示
        self.red_info_label = tk.Label(self.control_frame, text="紅色: --%  非紅色: --%")
        self.red_info_label.pack(pady=5)

        # 緊急按鈕（手動觸發）
        self.full_load_var = tk.BooleanVar(value=False)
        self.full_load_check = tk.Checkbutton(
            self.control_frame, text="緊急按鈕", variable=self.full_load_var, command=self.toggle_full_load
        )
        self.full_load_check.pack(pady=10)

        # 內部呼叫按鈕（樓層 3,2,1，從上到下排列）
        tk.Label(self.control_frame, text="內部呼叫").pack(pady=5)
        self.btn_internal_floor3 = tk.Button(
            self.control_frame, text="3", command=lambda: self.add_request(3, ButtonType.INTERNAL)
        )
        self.btn_internal_floor3.pack(fill=tk.X, padx=5, pady=2)
        self.btn_internal_floor2 = tk.Button(
            self.control_frame, text="2", command=lambda: self.add_request(2, ButtonType.INTERNAL)
        )
        self.btn_internal_floor2.pack(fill=tk.X, padx=5, pady=2)
        self.btn_internal_floor1 = tk.Button(
            self.control_frame, text="1", command=lambda: self.add_request(1, ButtonType.INTERNAL)
        )
        self.btn_internal_floor1.pack(fill=tk.X, padx=5, pady=2)

        # 外部呼叫按鈕
        tk.Label(self.control_frame, text="外部呼叫").pack(pady=5)
        self.btn_ext_3_down = tk.Button(
            self.control_frame, text="3 樓 下", command=lambda: self.add_request(3, ButtonType.DOWN)
        )
        self.btn_ext_3_down.pack(fill=tk.X, padx=5, pady=2)
        self.btn_ext_2_up = tk.Button(
            self.control_frame, text="2 樓 上", command=lambda: self.add_request(2, ButtonType.UP)
        )
        self.btn_ext_2_up.pack(fill=tk.X, padx=5, pady=2)
        self.btn_ext_2_down = tk.Button(
            self.control_frame, text="2 樓 下", command=lambda: self.add_request(2, ButtonType.DOWN)
        )
        self.btn_ext_2_down.pack(fill=tk.X, padx=5, pady=2)
        self.btn_ext_1_up = tk.Button(
            self.control_frame, text="1 樓 上", command=lambda: self.add_request(1, ButtonType.UP)
        )
        self.btn_ext_1_up.pack(fill=tk.X, padx=5, pady=2)

        # 狀態訊息
        self.info_label = tk.Label(self.control_frame, text="狀態：Idle")
        self.info_label.pack(pady=20)

        # 啟動主迴圈與紅色偵測更新
        self.master.after(100, self.simulation_loop)
        self.master.after(100, self.update_red_detection)

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

    # 持續更新紅色辨識：讀取攝影機影像，計算紅色比例，並更新顯示
    # 同時根據紅色比例自動觸發或解除自動緊急模式
    def update_red_detection(self):
        ret, frame = self.cap.read()
        if ret:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            lower_red1 = np.array([0, 50, 50])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 50, 50])
            upper_red2 = np.array([180, 255, 255])
            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            red_mask = cv2.bitwise_or(mask1, mask2)
            red_pixels = cv2.countNonZero(red_mask)
            total_pixels = frame.shape[0] * frame.shape[1]
            red_ratio = red_pixels / total_pixels if total_pixels else 0
            red_percent = red_ratio * 100
            non_red_percent = 100 - red_percent
            self.red_info_label.config(text=f"紅色: {red_percent:.1f}%  非紅色: {non_red_percent:.1f}%")
            # 自動觸發：若紅色比例低於5%，則自動啟動；否則解除
            if red_percent < 5:
                if not self.auto_emergency:
                    print("偵測到紅色不足5%，自動啟動緊急模式")
                self.auto_emergency = True
            else:
                if self.auto_emergency:
                    print("偵測到紅色超過5%，自動解除緊急模式")
                self.auto_emergency = False
            self.update_emergency_mode()

            # 將紅色區域影像顯示於 GUI
            red_area = cv2.bitwise_and(frame, frame, mask=red_mask)
            red_area = cv2.cvtColor(red_area, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(red_area)
            image = image.resize((300, 225))
            photo = ImageTk.PhotoImage(image)
            self.camera_label.config(image=photo)
            self.camera_label.image = photo
        self.master.after(100, self.update_red_detection)

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
