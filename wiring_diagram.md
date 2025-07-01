# Arduino 實體電梯系統接線圖

## 硬體清單

### 主要組件
- Arduino UNO × 1
- ULN2003 步進馬達驅動板 × 1
- 28BYJ-48 步進馬達 × 1
- 微動開關 × 2 (頂部/底部位置檢測)
- 麵包板或萬用板
- 杜邦線若干

## 詳細接線說明

### 1. Arduino UNO 引腳分配

```
數位引腳:
D2  ← ULN2003 IN1 (步進馬達)
D3  ← ULN2003 IN3 (步進馬達)
D4  ← ULN2003 IN2 (步進馬達)
D5  ← ULN2003 IN4 (步進馬達)
D6  ← 頂部微動開關
D7  ← 底部微動開關

電源:
5V  → 各組件正極
GND → 各組件負極
```

### 2. ULN2003 步進馬達驅動板接線

```
ULN2003 驅動板:
VCC → Arduino 5V
GND → Arduino GND
IN1 → Arduino D8
IN2 → Arduino D9
IN3 → Arduino D10
IN4 → Arduino D11

28BYJ-48 步進馬達:
連接到 ULN2003 的馬達接口 (通常是 5 針連接器)
紅線 → VCC
其他線按順序連接
```


### 3. 微動開關接線

```
頂部微動開關:
OUT → Arduino D6
VCC  → 空接 (或根據開關類型調整)
GND  → Arduino GND (使用內部上拉電阻)

底部微動開關:
OUT → Arduino D7
VCC  → 空接
GND  → Arduino GND (使用內部上拉電阻)
```

