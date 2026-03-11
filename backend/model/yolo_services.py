from ultralytics import YOLO
from PIL import Image
import io
import os

# 1. ระบุตำแหน่งไฟล์โมเดลตัวใหม่ (แก้ไขชื่อไฟล์ best.pt ให้ตรงกับที่คุณเซฟมานะครับ)
MODEL_PATH = os.path.join(os.path.dirname(__file__), "yolo11n_food.pt") 

print(f"⏳ Loading Custom YOLO11n model from {MODEL_PATH}...")
try:
    model = YOLO(MODEL_PATH)
    print("✅ Model loaded successfully!")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    print("อย่าลืมเอาไฟล์ .pt มาวางไว้ในโฟลเดอร์ model นะครับ!")

def detect_ingredients_from_image(image_bytes):
    """
    รับไฟล์รูปภาพแบบ Bytes, ให้ YOLO วิเคราะห์, และรีเทิร์นรายชื่อสิ่งที่เจอ
    """
    image = Image.open(io.BytesIO(image_bytes))
    
    # รัน Inference
    results = model(image)
    
    detected_items = []
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = model.names[class_id] # ดึงชื่อคลาสภาษาอังกฤษออกมา
            detected_items.append(class_name)
            
    # ตัดชื่อซ้ำออก
    unique_items = list(set(detected_items))
    return unique_items

# ==========================================
# 🚀 บล็อกสำหรับรันทดสอบ (Testing Block)
# ==========================================
if __name__ == "__main__":
    print("\n--- 🔍 เริ่มการทดสอบดวงตา AI (YOLO11n) ---")
    
    # ถ้ารันสคริปต์จากโฟลเดอร์ backend รูปควรจะอยู่ที่นี่
    test_image_path = "test_images/carrot3.jpg" 
    
    if not os.path.exists(test_image_path):
        print(f"\n❌ ไม่พบไฟล์รูปภาพชื่อ '{test_image_path}'")
        print("รบกวนหารูปภาพหมูสามชั้น (pork belly) หรือกะหล่ำปลี (cabbage) มาเซฟชื่อ test_image.jpg ไว้ในโฟลเดอร์ backend ก่อนนะครับ\n")
    else:
        try:
            with open(test_image_path, "rb") as f:
                image_bytes = f.read()
                
            print(f"กำลังวิเคราะห์ภาพ: {test_image_path}...")
            
            # ส่งให้ YOLO วิเคราะห์
            detected_items = detect_ingredients_from_image(image_bytes)
            
            print("\n🎉 วิเคราะห์เสร็จสิ้น!")
            print(f"รายการวัตถุดิบที่ AI มองเห็น: {detected_items}")
            
            if len(detected_items) == 0:
                print("⚠️ AI มองไม่เห็นวัตถุดิบที่รู้จักในภาพนี้ ลองเปลี่ยนมุมถ่ายหรือเปลี่ยนรูปดูนะครับ")
                
            print("------------------------------\n")
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดระหว่างทดสอบ: {e}")