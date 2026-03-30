import sqlite3

conn = sqlite3.connect("orders.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product TEXT,
    phone TEXT,
    location TEXT,
    status TEXT
)
""")

#products Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price REAL,
    image TEXT,
    available INTEGER DEFAULT 1
)               
""")

#default products
cursor.execute("SELECT COUNT(*) FROM products")
count = cursor.fetchone()[0]

if count == 0:
    cursor.executemany(
        "INSERT INTO products (name, price, image) values (?, ?, ?)",
        [
            ("Shoes", 20, "https://images.pexels.com/photos/2529148/pexels-photo-2529148.jpeg"),
            ("Hoodie", 20, "https://images.pexels.com/photos/6311392/pexels-photo-6311392.jpeg"),
            ("Cap", 10, "https://images.pexels.com/photos/1124465/pexels-photo-1124465.jpeg"), 
        ]
    )

conn.commit()
conn.close()

print("Database ready:")