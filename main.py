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

class MedicineCreate(BaseModel):
    name: str
    price: float
    category: str

@app.post("/customer/signup/")
def signup(data: CustomerSignup):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO customers (phone, name, password) VALUES (?, ?, ?)", (data.phone, data.name, data.password))
        conn.commit()
        return {"status": "Success", "message": "Account created successfully!"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Phone number already registered!")
    finally:
        conn.close()

@app.post("/customer/login/")
def login(data: CustomerLogin):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE phone = ? AND password = ?", (data.phone, data.password))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"status": "Success", "message": "Login successful!"}
    else:
        raise HTTPException(status_code=401, detail="Invalid phone number or password!")

@app.get("/customer/search-medicine/")
def search_medicine(query: str = "", category: str = ""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        # Agar query hai toh 'para%' yaani shuruat ki spelling match karega
        if query and category:
            cursor.execute("SELECT name, price, category FROM medicines WHERE name LIKE ? AND category = ?", (f"{query}%", category))
        elif query:
            cursor.execute("SELECT name, price, category FROM medicines WHERE name LIKE ?", (f"{query}%",))
        elif category:
            cursor.execute("SELECT name, price, category FROM medicines WHERE category = ?", (category,))
        else:
            cursor.execute("SELECT name, price, category FROM medicines")
            
        rows = cursor.fetchall()
        results = [{"name": r[0], "price": r[1], "category": r[2]} for r in rows]
        return {"status": "Success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
    
    results = [{"name": row[0], "price": row[1], "category": row[2]} for row in rows]
    return {"results": results}

@app.post("/customer/place-order/")
def place_order(data: OrderPlace):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO orders (customer_phone, total_price) VALUES (?, ?)", (data.customer_phone, data.total_price))
        order_id = cursor.lastrowid
        for item in data.items:
            cursor.execute("INSERT INTO order_items (order_id, medicine_name, quantity, price) VALUES (?, ?, ?, ?)", (order_id, item.name, item.quantity, item.price))
        conn.commit()
        return {"status": "Success", "order_id": order_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/customer/my-orders/{phone}")
def get_customer_orders(phone: str):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, total_price, status, created_at FROM orders WHERE customer_phone = ? ORDER BY id DESC", (phone,))
        orders = [dict(row) for row in cursor.fetchall()]
        for order in orders:
            cursor.execute("SELECT medicine_name, quantity, price FROM order_items WHERE order_id = ?", (order["id"],))
            order["items"] = [dict(item_row) for item_row in cursor.fetchall()]
        return {"status": "Success", "orders": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/customer/add-address/")
def add_address(data: AddressCreate):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO addresses (customer_phone, receiver_name, receiver_phone, house_no, area_details, landmark, city, state, pincode) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (data.customer_phone, data.receiver_name, data.receiver_phone, data.house_no, data.area_details, data.landmark, data.city, data.state, data.pincode)
        )
        conn.commit()
        return {"status": "Success", "message": "Address saved successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/customer/my-addresses/{phone}")
def get_addresses(phone: str):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, receiver_name, receiver_phone, house_no, area_details, landmark, city, state, pincode FROM addresses WHERE customer_phone = ?", (phone,))
        addresses = [dict(row) for row in cursor.fetchall()]
        return {"status": "Success", "addresses": addresses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/admin/add-medicine/")
def add_medicine(data: MedicineCreate):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO medicines (name, price, category) VALUES (?, ?, ?)", 
            (data.name, data.price, data.category)
        )
        conn.commit()
        return {"status": "Success", "message": f"{data.name} successfully added!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# Render Par Cloud Port Allocation setup handle karne ke liye main function block 🔥
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)