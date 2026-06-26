import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional # Optional ko add kiya query params handle karne ke liye

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "apna_medical.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        phone TEXT PRIMARY KEY,
        name TEXT,
        password TEXT
    )
    """)
    
    # UPDATED: medicines table mein category column jod diya hai 🔥
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        category TEXT DEFAULT 'All'
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_phone TEXT,
        total_price REAL,
        status TEXT DEFAULT 'Pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        medicine_name TEXT,
        quantity INTEGER,
        price REAL
    )
    """)

    # Addresses Table: Name, Phone, aur Pincode specifications ke sath
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS addresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_phone TEXT,
        receiver_name TEXT,
        receiver_phone TEXT,
        house_no TEXT,
        area_details TEXT,
        landmark TEXT,
        city TEXT,
        state TEXT,
        pincode TEXT
    )
    """)
    
    conn.commit()
    conn.close()

# Database structures ko initialize karne ke liye function call
init_db()

class CustomerSignup(BaseModel):
    name: str
    phone: str
    password: str

class CustomerLogin(BaseModel):
    phone: str
    password: str

class CartItem(BaseModel):
    name: str
    price: float
    quantity: int

class OrderPlace(BaseModel):
    customer_phone: str
    total_price: float
    items: List[CartItem]

class AddressCreate(BaseModel):
    customer_phone: str
    receiver_name: str
    receiver_phone: str
    house_no: str
    area_details: str
    landmark: str
    city: str
    state: str
    pincode: str

# 1. Pydantic Model mein image_url jodhna
class MedicineCreate(BaseModel):
    name: str
    price: float
    category: str
    image_url: Optional[str] = "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=200" # Default image agar blank chhodein toh

# 2. Database Table Creation Query mein update
# (Jahan table create ho rahi hai wahan 'image_url TEXT' add kar dein)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        price REAL,
        category TEXT,
        image_url TEXT
    )
""")

# =======================================================
# BLINKIT STYLE REAL IMAGE UPLOAD ENGINE 📸 (FULLY FIXED)
# =======================================================
from fastapi import UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
import shutil
import os
import time
import sqlite3

UPLOAD_DIR = "static_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Static files mount agar upar nahi hua hai toh yahan ensure karein
try:
    app.mount("/static_images", StaticFiles(directory=UPLOAD_DIR), name="static_images")
except RuntimeException:
    # Agar pehle se mounted hoga toh error nahi aayega
    pass

@app.post("/admin/add-medicine-with-image/")
async def add_medicine_with_image(
    name: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    image: UploadFile = File(...)
):
    # 🔥 Agar upar DB_NAME variable hai toh use lega, nahi toh medical.db chalega
    db_file = DB_NAME if 'DB_NAME' in globals() else "medical.db"
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    try:
        # File ko local folder mein save karna
        file_location = f"{UPLOAD_DIR}/{int(time.time())}_{image.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        # Public URL create karna
        live_image_url = f"https://apnamedical-backend.onrender.com/{file_location}"
        
        # Database query chalana
        cursor.execute(
            "INSERT INTO medicines (name, price, category, image_url) VALUES (?, ?, ?, ?)",
            (name, price, category, live_image_url)
        )
        conn.commit()
        return {
            "status": "Success", 
            "message": f"{name} real image ke sath add ho gayi!", 
            "url": live_image_url
        }
        
    except sqlite3.IntegrityError:
        return {"status": "Error", "detail": "Medicine already exists!"}
    except Exception as e:
        return {"status": "Error", "detail": str(e)}
    finally:
        conn.close()