#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);

String inputString = "";
bool stringComplete = false;

void setup() {
    Serial.begin(9600);
    inputString.reserve(200);
    
    lcd.init();
    lcd.backlight();
    
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Elevator System");
    lcd.setCursor(0, 1);
    lcd.print("Ready...");
}

void loop() {
  if (stringComplete) {
    if (inputString.startsWith("L1:")) {
        String line1 = inputString.substring(3);
        lcd.setCursor(0, 0);
        lcd.print("                "); 
        lcd.setCursor(0, 0);
        lcd.print(line1);
    }
    else if (inputString.startsWith("L2:")) {
      String line2 = inputString.substring(3);
      lcd.setCursor(0, 1);
      lcd.print("                "); 
      lcd.setCursor(0, 1);
      lcd.print(line2);
    }
    
    inputString = "";
    stringComplete = false;
  }
}

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