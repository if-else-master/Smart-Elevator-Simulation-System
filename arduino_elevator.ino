#include <Unistep2.h>

// === 硬體配置 ===
// 步進馬達設定 (28BYJ-48 + ULN2003) - 使用Unistep2庫
const int stepsPerRevolution = 4096;  // 28BYJ-48 全步模式每圈步數
Unistep2 myStepper(8, 9, 10, 11, stepsPerRevolution, 1000);  // IN1, IN2, IN3, IN4, 總step數, 每步延遲(微秒)

// 引腳定義
// 微動開關
const int limitSwitchTop = 12;     // 頂部微動開關
const int limitSwitchBottom = 13;  // 底部微動開關

// === 全域變數 ===
// 電梯狀態
int currentFloor = 1;           // 當前樓層
int targetFloor = 1;            // 目標樓層
bool isMoving = false;          // 是否正在移動
bool emergencyMode = false;     // 緊急模式
bool isCalibrating = false;     // 是否正在校準

// 位置計算
long currentPosition = 0;       // 當前步進馬達位置
long stepsPerFloor = 1000;      // 每層樓的步數（需要校準）
long floorPositions[4];         // 各樓層的位置（索引0不用，1-3對應樓層）

// 串口通訊
String inputString = "";
bool stringComplete = false;

// 移動控制變數
long targetPosition = 0;        // 目標位置
bool movingUp = false;          // 移動方向
int moveProgress = 0;           // 移動進度

// === 初始化設定 ===
void setup() {
  // 串口初始化
  Serial.begin(9600);
  inputString.reserve(200);
  
  // 引腳模式設定
  pinMode(limitSwitchTop, INPUT_PULLUP);
  pinMode(limitSwitchBottom, INPUT_PULLUP);
  
  // 馬達測試 - 小幅度移動確認馬達正常
  Serial.println("馬達測試中...");
  
  // 測試馬達轉動 - 使用Unistep2
  myStepper.move(100);
  while(myStepper.stepsToGo() != 0) {
    myStepper.run();
    delay(1);
  }
  delay(500);
  
  myStepper.move(-100);
  while(myStepper.stepsToGo() != 0) {
    myStepper.run();
    delay(1);
  }
  
  Serial.println("馬達測試完成");
  
  // 初始化樓層位置
  calibrateFloorPositions();
  
  Serial.println("Arduino Elevator Ready");
}

// === 主循環 ===
void loop() {
  // 馬達運轉 - Unistep2需要持續調用run()
  myStepper.run();
  
  // 處理串口命令
  if (stringComplete) {
    processCommand(inputString);
    inputString = "";
    stringComplete = false;
  }
  
  // 檢查微動開關
  checkLimitSwitches();
  
  // 更新電梯位置和移動狀態
  updateMovementStatus();
  
  // 更新電梯位置
  updatePosition();
  
  delay(1);  // 短暫延遲，讓Unistep2正常工作
}

// === 更新移動狀態 ===
void updateMovementStatus() {
  if (isMoving && myStepper.stepsToGo() == 0) {
    // 移動完成
    isMoving = false;
    currentFloor = calculateCurrentFloor();
    
    Serial.print("MOVE_COMPLETE:");
    Serial.println(currentFloor);
  }
  
  // 報告移動進度
  if (isMoving) {
    long totalSteps = abs(targetPosition - currentPosition);
    if (totalSteps > 0) {
      long remainingSteps = abs(myStepper.stepsToGo());
      int newProgress = ((totalSteps - remainingSteps) * 100) / totalSteps;
      
      if (newProgress != moveProgress && newProgress % 10 == 0) {
        moveProgress = newProgress;
        Serial.print("PROGRESS:");
        Serial.print(moveProgress);
        Serial.println("%");
      }
    }
  }
}

// === 微動開關檢查 ===
void checkLimitSwitches() {
  static bool lastTopState = HIGH;
  static bool lastBottomState = HIGH;
  
  bool topState = digitalRead(limitSwitchTop);
  bool bottomState = digitalRead(limitSwitchBottom);
  
  // 頂部微動開關觸發
  if(topState == LOW && lastTopState == HIGH) {
    Serial.println("LIMIT:top");
    if(isCalibrating) {
      floorPositions[3] = currentPosition;  // 3樓位置
    }
    // 安全停止
    if(isMoving) {
      myStepper.move(0);  // Unistep2停止方式
      isMoving = false;
      Serial.println("到達頂部限位，強制停止");
    }
  }
  
  // 底部微動開關觸發
  if(bottomState == LOW && lastBottomState == HIGH) {
    Serial.println("LIMIT:bottom");
    if(isCalibrating) {
      floorPositions[1] = currentPosition;  // 1樓位置
      currentPosition = 0;  // 重置位置
      currentFloor = 1;
    }
    // 安全停止
    if(isMoving) {
      myStepper.move(0);  // Unistep2停止方式
      isMoving = false;
      Serial.println("到達底部限位，強制停止");
    }
  }
  
  lastTopState = topState;
  lastBottomState = bottomState;
}

// === 位置更新 ===
void updatePosition() {
  // 根據當前位置判斷樓層
  if(!isCalibrating && !isMoving) {
    int newFloor = calculateCurrentFloor();
    if(newFloor != currentFloor) {
      currentFloor = newFloor;
      Serial.print("POS:");
      Serial.println(currentFloor);
    }
  }
}

// === 計算當前樓層 ===
int calculateCurrentFloor() {
  // 找到最接近的樓層
  int closestFloor = 1;
  long minDistance = abs(currentPosition - floorPositions[1]);
  
  for(int floor = 2; floor <= 3; floor++) {
    long distance = abs(currentPosition - floorPositions[floor]);
    if(distance < minDistance) {
      minDistance = distance;
      closestFloor = floor;
    }
  }
  
  return closestFloor;
}

// === 校準樓層位置 ===
void calibrateFloorPositions() {
  isCalibrating = true;
  
  Serial.println("開始校準：移動到底部");
  
  // 先移動到底部 - 使用Unistep2
  currentPosition = 0;
  int stepCount = 0;
  myStepper.move(-10000);  // 大步數往下移動
  
  while(digitalRead(limitSwitchBottom) == HIGH && stepCount < 10000) {
    myStepper.run();
    if (myStepper.stepsToGo() == 0) {
      break;  // 如果馬達停止但還沒碰到限位開關，可能有問題
    }
    stepCount++;
    if(stepCount % 100 == 0) {
      Serial.print("步數: ");
      Serial.println(stepCount);
    }
    delay(1);
  }
  
  // 停止馬達並設定1樓位置
  myStepper.move(0);
  while(myStepper.stepsToGo() != 0) {
    myStepper.run();
    delay(1);
  }
  
  currentPosition = 0;
  floorPositions[1] = 0;
  
  Serial.println("1樓位置校準完成");
  delay(1000);
  
  // 移動到頂部，計算總行程
  Serial.println("移動到頂部");
  
  stepCount = 0;
  myStepper.move(10000);  // 大步數往上移動
  
  while(digitalRead(limitSwitchTop) == HIGH && stepCount < 10000) {
    myStepper.run();
    if (myStepper.stepsToGo() == 0) {
      break;  // 如果馬達停止但還沒碰到限位開關，可能有問題
    }
    stepCount++;
    currentPosition++;
    if(stepCount % 200 == 0) {
      Serial.print("總步數: ");
      Serial.println(currentPosition);
    }
    delay(1);
  }
  
  // 停止馬達並設定3樓位置
  myStepper.move(0);
  while(myStepper.stepsToGo() != 0) {
    myStepper.run();
    delay(1);
  }
  
  // 設定3樓位置
  floorPositions[3] = currentPosition;
  
  // 計算2樓位置（中間）
  floorPositions[2] = (floorPositions[1] + floorPositions[3]) / 2;
  stepsPerFloor = (floorPositions[3] - floorPositions[1]) / 2;
  
  Serial.println("校準完成");
  Serial.print("1樓位置: "); Serial.println(floorPositions[1]);
  Serial.print("2樓位置: "); Serial.println(floorPositions[2]);
  Serial.print("3樓位置: "); Serial.println(floorPositions[3]);
  Serial.print("每層步數: "); Serial.println(stepsPerFloor);
  
  delay(2000);
  
  // 回到1樓
  moveToFloor(1);
  
  isCalibrating = false;
  
  Serial.println("校準完成");
  delay(2000);
}

// === 移動到指定樓層 ===
void moveToFloor(int floor) {
  if(floor < 1 || floor > 3 || emergencyMode) return;
  
  targetFloor = floor;
  targetPosition = floorPositions[floor];
  long stepsToMove = targetPosition - currentPosition;
  
  if (abs(stepsToMove) < 10) {
    // 已經很接近目標位置
    Serial.print("MOVE_COMPLETE:");
    Serial.println(floor);
    return;
  }
  
  isMoving = true;
  moveProgress = 0;
  
  Serial.print("MOVE_START:");
  Serial.println(floor);
  
  if(stepsToMove > 0) {
    // 向上移動
    Serial.print("向上移動 ");
    Serial.print(stepsToMove);
    Serial.println(" 步");
    movingUp = true;
  } else {
    // 向下移動
    Serial.print("向下移動 ");
    Serial.print(-stepsToMove);
    Serial.println(" 步");
    movingUp = false;
  }
  
  // 使用Unistep2移動
  myStepper.move(stepsToMove);
  
  // 更新當前位置
  currentPosition = targetPosition;
}

// === 處理串口命令 ===
void processCommand(String command) {
  command.trim();
  
  if(command == "PING") {
    // Ping檢查命令
    Serial.println("PONG");
    return;
  }
  else if(command.startsWith("MOVE:")) {
    // 移動命令: MOVE:樓層
    int floor = command.substring(5).toInt();
    if(floor >= 1 && floor <= 3) {
      moveToFloor(floor);
    }
  }
  else if(command == "STOP") {
    // 停止命令
    myStepper.move(0);  // Unistep2停止方式
    isMoving = false;
    emergencyMode = false;
    Serial.println("馬達停止");
  }
  else if(command == "CALIBRATE") {
    // 校準命令
    calibrateFloorPositions();
  }
  else if(command == "TEST") {
    // 馬達測試命令
    Serial.println("開始馬達測試");
    myStepper.move(200);
    while(myStepper.stepsToGo() != 0) {
      myStepper.run();
      delay(1);
    }
    delay(500);
    myStepper.move(-200);
    while(myStepper.stepsToGo() != 0) {
      myStepper.run();
      delay(1);
    }
    Serial.println("馬達測試完成");
  }
  else if(command.startsWith("EMERGENCY:")) {
    // 緊急模式設定
    if(command.substring(10) == "ON") {
      emergencyMode = true;
      myStepper.move(0);  // Unistep2停止方式
      isMoving = false;
      Serial.println("緊急模式啟動");
    } else {
      emergencyMode = false;
      Serial.println("緊急模式解除");
    }
  }
  else if(command == "STATUS") {
    // 狀態查詢
    Serial.print("STATUS:");
    Serial.print(currentFloor);
    Serial.print(":");
    Serial.print(targetFloor);
    Serial.print(":");
    Serial.print(isMoving ? "MOVING" : "IDLE");
    Serial.print(":");
    Serial.println(emergencyMode ? "EMERGENCY" : "NORMAL");
  }
}

// === 串口事件處理 ===
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }
}