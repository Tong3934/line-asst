# 📋 คู่มือการจัดการข้อมูล Mock (mock_data.py)

## 📖 ภาพรวม

ไฟล์ `mock_data.py` ใช้สำหรับจำลองข้อมูลกรมธรรม์ประกันรถยนต์เพื่อการทดสอบระบบ

ในระบบจริง ควรแทนที่ด้วย:
- **Database**: PostgreSQL, MySQL, MongoDB
- **API**: RESTful API จากระบบ Core Insurance
- **Cloud Storage**: AWS RDS, Google Cloud SQL

## 🏗️ โครงสร้างข้อมูล

### Policy Data Structure

```python
{
    "policy_number": str,        # เลขกรมธรรม์ (ไม่ซ้ำกัน)
    "name": str,                 # ชื่อ-นามสกุลผู้เอาประกัน
    "plate": str,                # ทะเบียนรถ
    "car_model": str,            # ยี่ห้อและรุ่นรถ
    "car_year": str,             # ปีที่ผลิต
    "insurance_type": str,       # ประเภทประกัน (ชั้น 1, 2+, 2, 3+, 3)
    "insurance_company": str,    # ชื่อบริษัทประกัน
    "policy_start": str,         # วันที่เริ่มคุ้มครอง (DD/MM/YYYY)
    "policy_end": str,           # วันที่สิ้นสุดคุ้มครอง (DD/MM/YYYY)
    "coverage": {
        "own_damage": str,       # ความคุ้มครองความเสียหายต่อรถยนต์
        "third_party": str,      # ความรับผิดชอบต่อบุคคลภายนอก
        "theft": str,            # ความคุ้มครองการโจรกรรม
        "fire": str              # ความคุ้มครองอัคคีภัย
    },
    "excess": int,               # ค่าเสียหายส่วนแรก (บาท)
    "status": str                # สถานะ (active, expired, cancelled)
}
```

## ➕ วิธีเพิ่มข้อมูลกรมธรรม์ใหม่

### วิธีที่ 1: เพิ่มด้วยตนเอง (Manual)

เปิดไฟล์ `mock_data.py` และเพิ่มข้อมูลใน Dictionary `MOCK_POLICIES`:

```python
MOCK_POLICIES = {
    # ... ข้อมูลเดิม ...
    
    "นายสมศักดิ์ ใจดี_4กส7777": {
        "policy_number": "POL-2024-007777",
        "name": "นายสมศักดิ์ ใจดี",
        "plate": "4กส7777",
        "car_model": "BMW 520d M Sport",
        "car_year": "2024",
        "insurance_type": "ชั้น 1",
        "insurance_company": "บริษัท เมืองไทยประกันภัย จำกัด (มหาชน)",
        "policy_start": "01/01/2024",
        "policy_end": "31/12/2024",
        "coverage": {
            "own_damage": "คุ้มครองเต็ม (ไม่ต้องมีคู่กรณี)",
            "third_party": "ไม่จำกัดจำนวนเงิน",
            "theft": "คุ้มครอง",
            "fire": "คุ้มครอง"
        },
        "excess": 10000,  # รถหรูมักมี excess สูงกว่า
        "status": "active"
    }
}
```

**หมายเหตุ**: Key ต้องเป็น `"ชื่อ-นามสกุล_ทะเบียนรถ"` เท่านั้น

### วิธีที่ 2: ใช้ฟังก์ชัน add_policy()

สร้างสคริปต์เพื่อเพิ่มข้อมูล:

```python
from mock_data import add_policy

new_policy = {
    "policy_number": "POL-2024-008888",
    "name": "นางสาวสมหวัง มีสุข",
    "plate": "5กบ8888",
    "car_model": "Mercedes-Benz C200 AMG",
    "car_year": "2024",
    "insurance_type": "ชั้น 1",
    "insurance_company": "บริษัท กรุงเทพประกันภัย จำกัด (มหาชน)",
    "policy_start": "01/02/2024",
    "policy_end": "31/01/2025",
    "coverage": {
        "own_damage": "คุ้มครองเต็ม (ไม่ต้องมีคู่กรณี)",
        "third_party": "ไม่จำกัดจำนวนเงิน",
        "theft": "คุ้มครอง",
        "fire": "คุ้มครอง"
    },
    "excess": 12000,
    "status": "active"
}

success = add_policy("นางสาวสมหวัง มีสุข", "5กบ8888", new_policy)
if success:
    print("✅ เพิ่มข้อมูลสำเร็จ")
else:
    print("❌ ข้อมูลซ้ำ")
```

## 🔍 ฟังก์ชันที่มีให้ใช้งาน

### 1. get_policy_info(name, plate)
ค้นหากรมธรรม์จากชื่อและทะเบียนรถ

```python
from mock_data import get_policy_info

policy = get_policy_info("นายสมชาย เข็มกลัด", "1กข1234")
if policy:
    print(f"พบกรมธรรม์: {policy['policy_number']}")
else:
    print("ไม่พบข้อมูล")
```

### 2. add_policy(name, plate, policy_data)
เพิ่มกรมธรรม์ใหม่

```python
from mock_data import add_policy

success = add_policy("นายทดสอบ ระบบ", "9กท9999", {...})
```

### 3. get_all_policies()
ดึงข้อมูลกรมธรรม์ทั้งหมด

```python
from mock_data import get_all_policies

all_policies = get_all_policies()
print(f"มีกรมธรรม์ทั้งหมด: {len(all_policies)} รายการ")
```

### 4. search_policies_by_name(name)
ค้นหากรมธรรม์จากชื่อ (รองรับค้นหาบางส่วน)

```python
from mock_data import search_policies_by_name

results = search_policies_by_name("สมชาย")
print(f"พบ {len(results)} รายการ")
```

### 5. search_policies_by_plate(plate)
ค้นหากรมธรรม์จากทะเบียนรถ

```python
from mock_data import search_policies_by_plate

policy = search_policies_by_plate("1กข1234")
if policy:
    print(f"เจ้าของ: {policy['name']}")
```

## 📝 ตัวอย่างการใช้งาน

### ตัวอย่างที่ 1: ตรวจสอบข้อมูลที่มีอยู่

```python
from mock_data import get_all_policies

policies = get_all_policies()
for key, policy in policies.items():
    print(f"{policy['name']} - {policy['plate']} - {policy['insurance_type']}")
```

### ตัวอย่างที่ 2: ค้นหากรมธรรม์ที่หมดอายุ

```python
from datetime import datetime
from mock_data import get_all_policies

today = datetime.now()

for key, policy in get_all_policies().items():
    end_date = datetime.strptime(policy['policy_end'], "%d/%m/%Y")
    if end_date < today:
        print(f"⚠️ กรมธรรม์หมดอายุ: {policy['name']} ({policy['policy_number']})")
```

### ตัวอย่างที่ 3: สถิติประเภทประกัน

```python
from mock_data import get_all_policies
from collections import Counter

insurance_types = [p['insurance_type'] for p in get_all_policies().values()]
stats = Counter(insurance_types)

print("📊 สถิติประเภทประกัน:")
for insurance_type, count in stats.items():
    print(f"  - {insurance_type}: {count} รายการ")
```

## 🔄 การเปลี่ยนไปใช้ Database จริง

เมื่อพร้อมใช้งานจริง ให้แก้ไขฟังก์ชันใน `mock_data.py`:

### ตัวอย่าง: PostgreSQL + SQLAlchemy

```python
from sqlalchemy import create_engine, Column, String, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine('postgresql://user:password@localhost/insurance_db')
Session = sessionmaker(bind=engine)

class Policy(Base):
    __tablename__ = 'policies'
    
    policy_number = Column(String, primary_key=True)
    name = Column(String)
    plate = Column(String)
    # ... fields อื่นๆ

def get_policy_info(name: str, plate: str) -> Optional[Dict]:
    session = Session()
    policy = session.query(Policy).filter_by(name=name, plate=plate).first()
    session.close()
    
    if policy:
        return {
            "policy_number": policy.policy_number,
            "name": policy.name,
            "plate": policy.plate,
            # ... แปลงเป็น Dict
        }
    return None
```

### ตัวอย่าง: MongoDB + Motor

```python
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient('mongodb://localhost:27017')
db = client.insurance_db
policies_collection = db.policies

async def get_policy_info(name: str, plate: str) -> Optional[Dict]:
    policy = await policies_collection.find_one({
        "name": name,
        "plate": plate
    })
    
    if policy:
        policy['_id'] = str(policy['_id'])  # Convert ObjectId to string
        return policy
    return None
```

## 🎯 Best Practices

1. **Validation**: ตรวจสอบความถูกต้องของข้อมูลก่อนเพิ่ม
2. **Normalization**: ปรับรูปแบบข้อมูล (เช่น ทะเบียนรถเป็นตัวพิมพ์ใหญ่)
3. **Indexing**: สร้าง index สำหรับ fields ที่ค้นหาบ่อย (ใน Database จริง)
4. **Error Handling**: จัดการ error ทุกกรณี
5. **Testing**: ทดสอบก่อนนำไปใช้งานจริง

## 📌 หมายเหตุ

- Mock Data นี้ใช้สำหรับการพัฒนาและทดสอบเท่านั้น
- ในระบบจริง ต้องมีการ Authentication และ Authorization
- ควรเข้ารหัสข้อมูลสำคัญ (Encryption at rest)
- ใช้ Environment Variables สำหรับ Database Connection String

---

💡 **เคล็ดลับ**: ก่อนเปลี่ยนไปใช้ Database จริง ให้ทดสอบระบบกับ Mock Data ให้ครบถ้วนก่อน
