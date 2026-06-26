import sqlite3
import os

DB_NAME = "apna_medical.db"

def get_db_connection():
    """Database se connect karne aur rows ko dictionary format mein laane ke liye function"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Isse data keys/columns ke naam se access hota hai
    return conn

def init_db():
    """Saare tables ko ek sath create aur verify karne ke liye function"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Customers Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # 2. Medicines Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT
        )
    ''')
    
    # 3. Orders Table (Main Order Summary)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_phone TEXT,
            total_price REAL,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4. Order Items Table (Dawaon ki detailed list)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            medicine_name TEXT,
            quantity INTEGER,
            price REAL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    ''')
    
    # Agar medicines table khali hai toh test data daalein
    cursor.execute("SELECT COUNT(*) FROM medicines")
    if cursor.fetchone()[0] == 0:
        test_medicines = [
            ("Paracetamol 650mg", 15.0, "Bukhar aur dard ke liye"),
            ("Amoxicillin 500mg", 45.5, "Antibiotic capsule"),
            ("Cetirizine 10mg", 12.0, "Allergy aur jukham ke liye"),
            ("Combiflam", 22.0, "Body pain aur swelling ke liye")
        ]
        cursor.executemany("INSERT INTO medicines (name, price, description) VALUES (?, ?, ?)", test_medicines)
        print("💡 Test medicines successfully database mein jor di gayi hain!")
        
    conn.commit()
    conn.close()
    print("🚀 Database aur saare tables ekdum ready hain!")

# Agar is file ko direct run karein toh database initialize ho jaye
if __name__ == "__main__":
    init_db()