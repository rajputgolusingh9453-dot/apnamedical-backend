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

DB_NAME = "apna_medical_v3.db"
UPLOAD_DIR = "static_images"

# Ensure image upload folder exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Static files mount config for serving product images
try:
    app.mount("/static_images", StaticFiles(directory=UPLOAD_DIR), name="static_images")
except RuntimeException:
    pass

def init_db():
    import sqlite3
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 📑 1. CUSTOMERS TABLE (Jo missing thi aur crash kar rahi thi)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            phone TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # 📑 2. ADDRESSES TABLE (Delivery addresses save karne ke liye)
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
            FOREIGN KEY(customer_phone) REFERENCES customers(phone)
        )
    ''')
    
    # 📑 3. MEDICINES TABLE (Aapki default products table)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            image_url TEXT
        )
    ''')
    
    # 📑 4. Check karna aur sample medicines automatic load karna
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
# Initialize Database on Startup
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
        # LIKE 'query%' lagaya hai taaki starting spelling filter ho sake ekdum blinkit ki tarah
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
        # File name ke sath file save karna
        file_location = f"{UPLOAD_DIR}/{int(time.time())}_{image.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        # Public URL structure for render cloud hosting
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
        cursor.execute("""
        INSERT INTO addresses (customer_phone, receiver_name, receiver_phone, house_no, area_details, landmark, city, state, pincode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data.customer_phone, data.receiver_name, data.receiver_phone, data.house_no, data.area_details, data.landmark, data.city, data.state, data.pincode))
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
    cursor.execute("SELECT id, receiver_name, receiver_phone, house_no, area_details, landmark, city, state, pincode FROM addresses WHERE customer_phone = ?", (phone,))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "id": r[0], "receiver_name": r[1], "receiver_phone": r[2],
            "house_no": r[3], "area_details": r[4], "landmark": r[5],
            "city": r[6], "state": r[7], "pincode": r[8]
        })
    return {"status": "Success", "addresses": results}

@app.post("/customer/place-order/")
def place_order(data: OrderPlace):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO orders (customer_phone, total_price) VALUES (?, ?)", (data.customer_phone, data.total_price))
        order_id = cursor.lastrowid
        
        for item in data.items:
            cursor.execute("""
            INSERT INTO order_items (order_id, medicine_name, quantity, price)
            VALUES (?, ?, ?, ?)
            """, (order_id, item.name, item.quantity, item.price))
            
        conn.commit()
        return {"status": "Success", "message": "Order Placed Successfully!", "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/customer/my-orders/")
def my_orders(phone: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, total_price, status, created_at FROM orders WHERE customer_phone = ? ORDER BY id DESC", (phone,))
    order_rows = cursor.fetchall()
    
    orders = []
    for o in order_rows:
        order_id = o[0]
        cursor.execute("SELECT medicine_name, quantity, price FROM order_items WHERE order_id = ?", (order_id,))
        item_rows = cursor.fetchall()
        items = [{"name": i[0], "quantity": i[1], "price": i[2]} for i in item_rows]
        
        orders.append({
            "order_id": order_id,
            "total_price": o[1],
            "status": o[2],
            "created_at": o[3],
            "items": items
        })
    conn.close()
    return {"status": "Success", "orders": orders}