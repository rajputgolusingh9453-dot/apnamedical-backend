import sqlite3
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import shutil
import os
import time
from datetime import datetime

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

os.makedirs(UPLOAD_DIR, exist_ok=True)

try:
    app.mount("/static_images", StaticFiles(directory=UPLOAD_DIR), name="static_images")
except Exception:
    pass

def init_db():
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

    # 📑 4. MEDICINES TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            image_url TEXT
        )
    ''')

    # 📑 5. ORDERS TABLE 
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

    # 📑 6. ORDER ITEMS TABLE
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
    
    # Default Sample Data Insertion
    cursor.execute("SELECT COUNT(*) FROM medicines")
    if cursor.fetchone()[0] == 0:
        sample_medicines = [
            ("Paracetamol 650mg", "Pain Relief", 30.0, "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=400"),
            ("Amoxicillin 500mg", "Antibiotics", 120.0, "https://images.unsplash.com/photo-1628771065518-0d82f11181a6?w=400")
        ]
        cursor.executemany("INSERT INTO medicines (name, category, price, image_url) VALUES (?, ?, ?, ?)", sample_medicines)
        conn.commit()
        print("🎉 Saari default tables aur medicines automatic add ho gayi hain!")
        
    conn.close()

init_db()

# =======================================================
# PYDANTIC MODELS
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
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class PincodeAdd(BaseModel):
    pincode: str
    area_name: str
    is_active: Optional[bool] = True

# =======================================================
# ROUTES / ENDPOINTS
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
# 📍 LOCATION BLOCKING SYSTEM ENDPOINTS
# =======================================================

@app.get("/customer/check-service/")
def check_service(pincode: str):
    """
    App open hote hi user ka pincode yahan check hoga.
    Agar status 'Success' nahi aata, to frontend poora blank ho jayega.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT area_name, is_active FROM serviceable_pincodes WHERE pincode = ?", (pincode,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row[1] == 1:
        return {
            "status": "Success", 
            "serviceable": True, 
            "message": f"Service available in {row[0]}"
        }
    else:
        return {
            "status": "Error", 
            "serviceable": False, 
            "message": "Es area me service available nhi hai"
        }

@app.post("/admin/add-pincode/")
def add_pincode(data: PincodeAdd):
    """Admin dashboard se naye restricted delivery pincodes add karne ke liye"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO serviceable_pincodes (pincode, area_name, is_active) VALUES (?, ?, ?)", 
            (data.pincode, data.area_name, 1 if data.is_active else 0)
        )
        conn.commit()
        return {"status": "Success", "message": f"Pincode {data.pincode} successfully updated!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# =======================================================
# 🔥 FIXED: ADDRESS MANAGEMENT ENDPOINTS
# =======================================================

@app.post("/customer/add-address/")
def add_address(data: AddressCreate):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
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

@app.delete("/customer/delete-address/{address_id}/")
def delete_address(address_id: int, phone: str):
    """
    🔥 SUCCESS CODE 200 FIX:
    Ye address delete karega aur correct status 200 return karega, 
    jisse App par 404 bad response nahi aayega aur instantly change reflect hoga.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM addresses WHERE id = ? AND customer_phone = ?", (address_id, phone))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Address not found or unauthorized!")
            
        cursor.execute("DELETE FROM addresses WHERE id = ?", (address_id,))
        conn.commit()
        
        return {
            "status": "Success", 
            "message": "Address successfully deleted from database", 
            "deleted_id": address_id
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/customer/get-addresses/")
def get_addresses(phone: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
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

# =======================================================
# OTHER SYSTEM ENDPOINTS (Medicines & Orders)
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

@app.post("/customer/place-order/")
def place_order(data: OrderPlace):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        order_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("INSERT INTO orders (customer_phone, total_price, status, created_at) VALUES (?, ?, ?, ?)", (data.customer_phone, data.total_price, 'Pending', order_time))
        order_id = cursor.lastrowid
        
        for item in data.items:
            cursor.execute("INSERT INTO order_items (order_id, name, price, quantity) VALUES (?, ?, ?, ?)", (order_id, item.name, item.price, item.quantity))
            
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