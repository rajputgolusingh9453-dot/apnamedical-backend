import sqlite3
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import shutil
import os
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "apna_medical.db"
UPLOAD_DIR = "static_images"

# Ensure local storage folder exists for images
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
    
    # UPDATED: medicines table mein 'image_url' aur 'UNIQUE' constraints pehle se set hain 🔥
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        price REAL,
        category TEXT DEFAULT 'All',
        image_url TEXT
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

# Database initialization call
init_db()

# Static files configuration for hosting images publicly
try:
    app.mount("/static_images", StaticFiles(directory=UPLOAD_DIR), name="static_images")
except RuntimeException:
    pass

# =======================================================
# PYDANTIC MODELS DEFINITION
# =======================================================
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

class MedicineCreate(BaseModel):
    name: str
    price: float
    category: str
    image_url: Optional[str] = "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=200"

# =======================================================
# API ROUTES & BLINKIT IMAGE UPLOAD ENGINE
# =======================================================

@app.post("/admin/add-medicine-with-image/")
async def add_medicine_with_image(
    name: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    image: UploadFile = File(...)
):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        # File ko local folder mein safe name ke sath save karna
        file_location = f"{UPLOAD_DIR}/{int(time.time())}_{image.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        # Public live URL template
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

# Note: Aapke baki endpoints (Login, Signup, Search) jo pehle bane the, unhe iske neeche add kar sakte hain.
