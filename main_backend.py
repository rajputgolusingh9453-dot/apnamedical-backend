import sqlite3
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import shutil
import os
import time
from datetime import datetime # 🔥 Real-time timestamps capture karne ke liye jodha hai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "apna_medical_v3.db"
UPLOAD_DIR = "static_images"

# Ensure image upload folder exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Static files mount config for serving product images
try:
    app.mount("/static_images", StaticFiles(directory=UPLOAD_DIR), name="static_images")
except Exception:
    pass

def init_db():
    import sqlite3
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 📑 1. CUSTOMERS TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            phone TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # 📑 2. ADDRESSES TABLE
    # 🔥 FIX: latitude/longitude columns add kiye — pehle yeh table me the
    # hi nahi, isliye Flutter app se bheji gayi GPS location kabhi save
    # nahi ho rahi thi (chahe Flutter sahi values bhej rahi thi). Isi
    # wajah se "auto nearest-store assignment" kaam nahi kar raha tha.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_phone TEXT NOT NULL,
            receiver_name TEXT NOT NULL,
            receiver_phone TEXT NOT NULL,
            house_no TEXT NOT NULL,
            area_details TEXT,
            landmark TEXT,
            city TEXT,
            state TEXT,
            pincode TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            FOREIGN KEY(customer_phone) REFERENCES customers(phone)
        )
    ''')

    # 🔥 FIX: Agar database file PEHLE se maujood hai (naye columns wali
    # CREATE TABLE tabhi chalti hai jab table bilkul nayi banti hai — agar
    # 'addresses' table pehle se hai to CREATE TABLE IF NOT EXISTS use
    # skip kar deta hai, aur purani table me naye columns nahi aate).
    # Isliye yahan ALTER TABLE se manually add kar rahe hain, aur agar
    # column already exist karta hai to error safely ignore ho jaata hai.
    for column in ["latitude", "longitude"]:
        try:
            cursor.execute(f"ALTER TABLE addresses ADD COLUMN {column} REAL")
        except sqlite3.OperationalError:
            pass  # column already exists — theek hai, kuch karne ki zaroorat nahi

    # 📑 3. MEDICINES TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            image_url TEXT
        )
    ''')

    # 📑 4. ORDERS TABLE 
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_phone TEXT NOT NULL,
            total_price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY(customer_phone) REFERENCES customers(phone)
        )
    ''')

    # 📑 5. ORDER ITEMS TABLE (Fixed Schema to align with exact keys)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(order_id)
        )
    ''')
    
    # 📑 6. Check karna aur sample medicines automatic load karna
    cursor.execute("SELECT COUNT(*) FROM medicines")
    if cursor.fetchone()[0] == 0:
        sample_medicines = [
            ("Paracetamol 650mg", "Pain Relief", 30.0, "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=400"),
            ("Amoxicillin 500mg", "Antibiotics", 120.0, "https://images.unsplash.com/photo-1628771065518-0d82f11181a6?w=400"),
            ("Neurobion Forte", "Vitamins", 35.0, "https://images.unsplash.com/photo-1616679911721-fe6eec13fcd5?w=400"),
            ("Himalaya Baby Powder", "Baby Care", 95.0, "https://images.unsplash.com/photo-1515488042361-404e9250afef?w=400"),
            ("Combiflam Tablet", "Pain Relief", 45.0, "https://images.unsplash.com/photo-1550572017-edd951b55104?w=400"),
            ("Betadine Ointment", "First Aid", 65.0, "https://images.unsplash.com/photo-1607619275116-0d1800a82b4b?w=400"),
            ("Dettol Liquid 100ml", "First Aid", 52.0, "https://images.unsplash.com/photo-1583947215259-38e31be8751f?w=400"),
            ("Limcee Vitamin C", "Vitamins", 25.0, "https://images.unsplash.com/photo-1576071804486-b8bc22106dbf?w=400"),
            ("Nivea Body Milk", "Personal Care", 199.0, "https://images.unsplash.com/photo-1556229010-aa3f7ff66b24?w=400")
        ]
        
        cursor.executemany(
            "INSERT INTO medicines (name, category, price, image_url) VALUES (?, ?, ?, ?)",
            sample_medicines
        )
        conn.commit()
        print("🎉 Saari default tables aur medicines automatic add ho gayi hain!")
        
    conn.close()

# System startup activation lock
init_db()

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
    # 🔥 FIX: yeh 2 fields pehle model me the hi nahi, isliye FastAPI
    # inhe silently drop kar deta tha chahe Flutter app bhej rahi ho.
    # Optional rakha hai taaki purane clients bhi bina crash hue chalte rahein.
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class MedicineCreate(BaseModel):
    name: str
    price: float
    category: str
    image_url: Optional[str] = "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=200"

# =======================================================
# AUTHENTICATION & CORE API ROUTES
# =======================================================
@app.post("/customer/signup/")
def signup(data: CustomerSignup):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO customers (phone, name, password) VALUES (?, ?, ?)", (data.phone, data.name, data.password))
        conn.commit()
        return {"status": "Success", "message": "Signup Successful!"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Phone number already registered!")
    finally:
        conn.close()

@app.post("/customer/login/")
def login(data: CustomerLogin):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, password FROM customers WHERE phone = ?", (data.phone,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row[1] == data.password:
        return {"status": "Success", "message": "Login Successful!", "customer_name": row[0]}
    else:
        raise HTTPException(status_code=401, detail="Invalid phone or password!")

# =======================================================
# BLINKIT INSTANT SPELLING SEARCH LOGIC 🔍
# =======================================================
@app.get("/customer/search-medicine/")
def search_medicine(query: str = "", category: str = ""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        if query and category:
            cursor.execute("SELECT name, price, category, image_url FROM medicines WHERE name LIKE ? AND category = ?", (f"{query}%", category))
        elif query:
            cursor.execute("SELECT name, price, category, image_url FROM medicines WHERE name LIKE ?", (f"{query}%",))
        elif category:
            cursor.execute("SELECT name, price, category, image_url FROM medicines WHERE category = ?", (category,))
        else:
            cursor.execute("SELECT name, price, category, image_url FROM medicines")
            
        rows = cursor.fetchall()
        results = [{"name": r[0], "price": r[1], "category": r[2], "image_url": r[3]} for r in rows]
        return {"status": "Success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# =======================================================
# BLINKIT STYLE REAL IMAGE UPLOAD ROUTE 📸
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
        file_location = f"{UPLOAD_DIR}/{int(time.time())}_{image.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        live_image_url = f"https://apnamedical-backend.onrender.com/{file_location}"
        
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

# =======================================================
# ORDERS & ADDRESSES ENDPOINTS
# =======================================================
@app.post("/customer/add-address/")
def add_address(data: AddressCreate):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        # 🔥 FIX: latitude/longitude ko bhi INSERT statement me include
        # kiya — pehle yeh column hi nahi tha isliye save hi nahi hota tha.
        cursor.execute("""
        INSERT INTO addresses (customer_phone, receiver_name, receiver_phone, house_no, area_details, landmark, city, state, pincode, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data.customer_phone, data.receiver_name, data.receiver_phone, data.house_no, data.area_details, data.landmark, data.city, data.state, data.pincode, data.latitude, data.longitude))
        conn.commit()
        return {"status": "Success", "message": "Address Saved Successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/customer/get-addresses/")
def get_addresses(phone: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 🔥 FIX: latitude/longitude ko SELECT me bhi jodha — pehle yeh response
    # me kabhi jaate hi nahi the, isliye Flutter app/Admin dashboard ko
    # hamesha "null" milta tha chahe database me value ho bhi.
    cursor.execute("SELECT id, receiver_name, receiver_phone, house_no, area_details, landmark, city, state, pincode, latitude, longitude FROM addresses WHERE customer_phone = ?", (phone,))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "id": r[0], "receiver_name": r[1], "receiver_phone": r[2],
            "house_no": r[3], "area_details": r[4], "landmark": r[5],
            "city": r[6], "state": r[7], "pincode": r[8],
            "latitude": r[9], "longitude": r[10]
        })
    return {"status": "Success", "addresses": results}

# ✅ FIXED: NOW ENFORCES REAL TIMESTAMPS AND MAPS PROPER TABLE KEYS
@app.post("/customer/place-order/")
def place_order(data: OrderPlace):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        # Automated time tag generation string format configuration matching system setup
        order_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        cursor.execute(
            "INSERT INTO orders (customer_phone, total_price, status, created_at) VALUES (?, ?, ?, ?)", 
            (data.customer_phone, data.total_price, 'Pending', order_time)
        )
        order_id = cursor.lastrowid
        
        for item in data.items:
            cursor.execute("""
                INSERT INTO order_items (order_id, name, price, quantity)
                VALUES (?, ?, ?, ?)
            """, (order_id, item.name, item.price, item.quantity))
            
        conn.commit()
        return {"status": "Success", "message": "Order Placed Successfully!", "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ✅ FIXED: ALIGNED QUERY MAP BACKEND INTEGRITY SEAMLESSLY
@app.get("/customer/my-orders/")
def my_orders(phone: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT order_id, total_price, status, created_at FROM orders WHERE customer_phone = ? ORDER BY order_id DESC", (phone,))
        order_rows = cursor.fetchall()
        
        orders = []
        for o in order_rows:
            current_id = o[0]
            cursor.execute("SELECT name, quantity, price FROM order_items WHERE order_id = ?", (current_id,))
            item_rows = cursor.fetchall()
            items = [{"name": i[0], "quantity": i[1], "price": i[2]} for i in item_rows]
            
            orders.append({
                "order_id": current_id,
                "total_price": o[1],
                "status": o[2],
                "created_at": o[3],
                "items": items
            })
        return {"status": "Success", "orders": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
