import tkinter as tk
from enum import Enum
import time
from queue import Queue

class Direction(Enum):
    UP = 1
    DOWN = -1
    IDLE = 0

class ElevatorSimulator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("電梯模擬系統")
        self.geometry("800x600")
        
        # 電梯狀態
        self.current_floor = 1
        self.direction = Direction.IDLE
        self.target_floor = None
        self.is_full = False
        self.request_queue = Queue()
        self.pending_requests = []
        
        # GUI元件初始化
        self.create_widgets()
        self.running = True
        self.update_interval = 100  # 更新間隔(毫秒)
        
        # 啟動電梯控制循環
        self.after(self.update_interval, self.control_loop)
        
    def create_widgets(self):
        # 電梯井道視覺化
        self.canvas = tk.Canvas(self, width=200, height=500, bg="gray")
        self.canvas.pack(side=tk.LEFT, padx=20)
        
        # 電梯車廂
        self.elevator = self.canvas.create_rectangle(50, 400, 150, 450, fill="silver")
        
        # 樓層標示
        for i, y in enumerate([50, 200, 350]):
            self.canvas.create_text(20, y+25, text=f"{3-i}F", font=("Arial", 14))
        
        # 控制面板
        control_frame = tk.Frame(self)
        control_frame.pack(side=tk.RIGHT, padx=20)
        
        # 外部按鈕
        btn_frame = tk.Frame(control_frame)
        btn_frame.pack(pady=10)
        self.external_btns = {
            1: {'up': None},
            2: {'up': None, 'down': None},
            3: {'down': None}
        }
        for floor in [3,2,1]:
            floor_frame = tk.Frame(btn_frame)
            floor_frame.pack()
            tk.Label(floor_frame, text=f"{floor}F").pack(side=tk.LEFT)
            if floor in self.external_btns:
                if 'up' in self.external_btns[floor]:
                    btn = tk.Button(floor_frame, text="▲", command=lambda f=floor: self.add_request(f, 'up'))
                    btn.pack(side=tk.LEFT, padx=5)
                    self.external_btns[floor]['up'] = btn
                if 'down' in self.external_btns[floor]:
                    btn = tk.Button(floor_frame, text="▼", command=lambda f=floor: self.add_request(f, 'down'))
                    btn.pack(side=tk.LEFT, padx=5)
                    self.external_btns[floor]['down'] = btn

        # 內部按鈕
        internal_frame = tk.Frame(control_frame)
        internal_frame.pack(pady=20)
        tk.Label(internal_frame, text="內部按鈕").pack()
        self.internal_btns = {}
        for floor in [1,2,3]:
            btn = tk.Button(internal_frame, text=str(floor), width=3,
                           command=lambda f=floor: self.add_request(f, 'internal'))
            btn.pack(side=tk.LEFT, padx=5)
            self.internal_btns[floor] = btn
        
        # 狀態顯示
        status_frame = tk.Frame(control_frame)
        status_frame.pack(pady=20)
        self.status_labels = {
            'floor': tk.Label(status_frame, text="當前樓層: 1", font=("Arial", 14)),
            'direction': tk.Label(status_frame, text="方向: IDLE", font=("Arial", 14)),
            'full': tk.Label(status_frame, text="滿載: 否", font=("Arial", 14))
        }
        for label in self.status_labels.values():
            label.pack(anchor=tk.W)
            
        # 滿載模擬按鈕
        self.full_btn = tk.Button(control_frame, text="切換滿載狀態", command=self.toggle_full)
        self.full_btn.pack(pady=10)
        
    def toggle_full(self):
        self.is_full = not self.is_full
        self.status_labels['full'].config(text=f"滿載: {'是' if self.is_full else '否'}")
        self.canvas.config(bg="red" if self.is_full else "gray")
        
    def add_request(self, floor, btn_type):
        if floor == self.current_floor and btn_type == 'internal':
            return
        self.request_queue.put((floor, btn_type))
        self.highlight_button(floor, btn_type)
        
    def highlight_button(self, floor, btn_type):
        if btn_type == 'internal':
            self.internal_btns[floor].config(bg="yellow")
        else:
            if btn_type == 'up':
                self.external_btns[floor]['up'].config(bg="yellow")
            else:
                self.external_btns[floor]['down'].config(bg="yellow")
                
    def reset_button(self, floor, btn_type):
        if btn_type == 'internal':
            self.internal_btns[floor].config(bg="SystemButtonFace")
        else:
            if btn_type == 'up':
                self.external_btns[floor]['up'].config(bg="SystemButtonFace")
            else:
                self.external_btns[floor]['down'].config(bg="SystemButtonFace")
    
    def move_elevator(self, target_floor):
        # 如果目標樓層與當前樓層相同，則不移動
        if target_floor == self.current_floor:
            return
        
        steps = abs(target_floor - self.current_floor)
        step_size = 150 // steps  # 每層高度150像素
        direction = 1 if target_floor > self.current_floor else -1
        
        for _ in range(steps):
            self.canvas.move(self.elevator, 0, -direction * step_size)
            self.update()
            time.sleep(0.1)
            
        self.current_floor = target_floor
        self.status_labels['floor'].config(text=f"當前樓層: {self.current_floor}")
        
    def control_loop(self):
        if not self.request_queue.empty():
            floor, btn_type = self.request_queue.get()
            self.target_floor = floor
            self.direction = Direction.UP if floor > self.current_floor else Direction.DOWN
            
            self.status_labels['direction'].config(text=f"方向: {self.direction.name}")
            self.move_elevator(floor)
            self.reset_button(floor, btn_type)
            self.direction = Direction.IDLE
            self.status_labels['direction'].config(text="方向: IDLE")
            
        if self.running:
            self.after(self.update_interval, self.control_loop)
            
    def on_closing(self):
        self.running = False
        self.destroy()

if __name__ == "__main__":
    app = ElevatorSimulator()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()