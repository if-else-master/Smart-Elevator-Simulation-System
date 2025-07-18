# 智能電梯模擬系統 - Smart Elevator Simulation System

## 簡介

我們在日常生活中，特別是在高樓層，經常會面臨需要長時間等待電梯的情況。而每當進入電梯後，經常會遇到每一層樓都有人按電梯，導致電梯停不停，並且需要不停按下「關門」按鈕。這樣雖然不會花太多時間，但卻讓人感到不耐煩。本專案旨在解決這個問題。

我們使用 OpenCV 來進行顏色辨識，當攝影機偵測到紅色（代表電梯內未滿載）時，電梯會停在每一層；若未偵測到紅色（代表電梯已滿載），則電梯將直接前往目的樓層。

此外，我們還加入了一個緊急模式，當緊急按鈕被按下時，電梯將優先將使用者送到一樓，或將醫護人員送到患者樓層。我們還特別設計了警報聲，當按下緊急按鈕時會發出警報聲，提醒周圍的人有緊急情況。

## 安裝與使用

### 安裝必要的套件

```bash
python3.10 -m venv .venv
```
```bash
source .venv/bin/activate
```

```bash
pip install pillow opencv-python numpy
```

### 執行專案

1. 克隆或下載專案源代碼。
2. 使用以下命令執行模擬系統：

```bash
python elevator_simulation.py
```

### 使用說明

1. **電梯畫面**：左側顯示電梯井與樓層圖，藍色矩形代表電梯，樓層位置為 1 至 3 層。
2. **內部呼叫按鈕**：右側的控制面板有樓層按鈕，分別為 1、2、3 樓。按下對應樓層的按鈕，電梯會根據目前情況進行處理。
3. **外部呼叫按鈕**：您可以模擬外部的上樓或下樓請求（例如，從 1 樓上、2 樓下等）。
4. **緊急模式**：如果按下緊急按鈕，電梯會優先將乘客送至一樓，或將醫護人員送至指定樓層。
5. **紅色偵測功能**：如果電梯內沒有顯示紅色，系統會自動啟動緊急模式。紅色區域會在右側顯示，並顯示紅色的百分比。

## 程式碼解釋

以下是主要的程式碼結構說明：

### 類別與方法

- `ButtonType`：定義按鈕類型，分為「向上」、「向下」與「內部呼叫」。
- `Direction`：定義電梯的運行方向，包括「上」、「下」與「閒置」。
- `Request`：表示一個樓層的請求，包括目標樓層、請求類型（內部或外部）及時間戳。
- `ElevatorControlSim`：核心的電梯控制模擬類別，負責管理電梯的運行、顯示及請求處理。

### 主要功能

1. **紅色偵測與緊急模式**：利用 OpenCV 的顏色辨識技術，檢測電梯內部是否有紅色區域，並根據比例自動啟動或解除緊急模式。
2. **請求管理與處理**：模擬內部與外部的請求，並根據請求的優先順序控制電梯的運行。
3. **緊急模式的觸發**：可以手動觸發緊急模式，並優先將乘客送至一樓，或將醫護人員送至目標樓層。

### OpenCV MOG2
- 使用 **MOG2 背景減除器** 來偵測移動物體
- 根據前景像素比例判斷場景中物體數量
- 結合 **形態學操作**（如膨脹、侵蝕）改善檢測結果
- 提供 **視覺化效果** 協助觀察與理解檢測狀態
- 根據前景突破量自動 **觸發緊急模式**


## 註意事項

1. **硬體要求**：請確保您的電腦或開發板支持 OpenCV 的相機模組，並且有連接有效的攝影機。
2. **性能**：本模擬是基於 Tkinter GUI 和 OpenCV 實現的，對硬體性能有一定要求，較舊的設備可能會影響顯示效果。

## Arduino螢幕連接
| LCD 腳位 | Arduino UNO 腳位 |
|----------|-------------------|
| VCC      | 5V                |
| GND      | GND               |
| SDA      | A4                |
| SCL      | A5                |

## 預期未來的功能

- 增加更多樓層的支持。
- 提升紅色區域辨識的準確度與穩定性。
- 增加與實際硬體電梯的對接模組，實現更真實的模擬與控制。

---

聯絡我：rayc57429@gmail.com 
