from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import os

app = Flask(__name__)
user_sessions = {}
user_cart = {}

def get_products():
    conn = sqlite3.connect("orders.db")
    c = conn.cursor()
    c.execute("SELECT id, name, price, image FROM products WHERE available = 1")
    rows = c.fetchall()
    conn.close()

    products = {}
    for row in rows:
        products[str(row[0])] ={
            "name": row[1],
            "price": row[2],
            "image": row[3]
        }
    return products

def save_order(product, phone, location):
    try:
        conn = sqlite3.connect("orders.db")
        c = conn.cursor()

        c.execute(
            "INSERT INTO orders(product, phone, location, status) VALUES (?, ?, ?, ?)",
            (product, phone, location, "pending")
        )

        order_id = c.lastrowid

        conn.commit()
        conn.close()

        return order_id

    except Exception as e:
        print("DATABASE ERROR", e)
        return 0


@app.route("/whatsapp", methods=["POST"])
def reply():
    incoming_msg = request.form.get("Body", "").strip().lower()
    from_number = request.form.get("From")

    response = MessagingResponse()
    msg = response.message()

    
    if "orders" in incoming_msg:
        conn = sqlite3.connect("orders.db")
        c = conn.cursor()

        c.execute("SELECT id, product, location, status FROM orders")
        rows = c.fetchall()

        if not rows:
            msg.body("No orders yet.")
        else:
            text = "Orders:\n\n"

        
            for r in rows:
                text += f"#{r[0]} - {r[1]} - {r[3]}\n"

            msg.body(text)

        conn.close()

        return str(response)

    
    elif "order" in incoming_msg:
        user_sessions[from_number] = "waiting_product"
        products = get_products()

        menu = "what products would you like to order?\n\n"
        for i, (key, value) in enumerate (products.items(), start=1):
            menu +=f"{i}. {value['name']} - ${value['price']}\n"
        menu += "\nReply with the number of your choice."

        msg.body(menu)
        return str(response)


    elif user_sessions.get(from_number) == "waiting_product":
            products = get_products()
            products_list = list(products.values())

            if incoming_msg.isdigit() and 1 <= int(incoming_msg) <= len(products_list):
                selected = products_list[int(incoming_msg) - 1]
                product = selected["name"]
                price = selected["price"]
                image = selected["image"]

                #add item to cart
                if from_number not in user_cart:
                    user_cart[from_number] = []
                user_cart[from_number].append({"name": product, "price": price})

                msg.body(
                    f"✅ {product} added to your cart!\n\n"
                    "Type 'more' to add another item\n"
                    "or 'checkout' to place your order."
                )

                if image.startswith("http"):
                    msg.media(image)
                user_sessions[from_number] = "waiting_product"

            elif incoming_msg == "more":
                products = get_products()
                menu = "What would you like to add?\n\n"
                for i, (key, value) in enumerate (products.items(), start=1):
                    menu += f"{i}. {value['name']} - ${value['price']}\n"
                menu += "\nReply with the number of your choice."
                msg.body(menu)
                user_sessions[from_number] = "waiting_product"
                
            elif incoming_msg == "checkout":
                cart = user_cart.get(from_number, [])

                if not cart:
                    msg.body("Your cart is empty. Type 'order' to start shopping. ")
                else:
                    #order summary
                    summary = "🛒 your order:\n\n"
                    total = 0

                    for item in cart:
                        summary += f"- {item['name']}: ${item['price']}\n"
                        total += item['price']

                    summary += f"\nTotal: ${total}"

                    #save each item as one order

                    product_names = ", ".join([item['name'] for item in cart])
                    order_id = save_order(product_names, from_number, "not provided")

                    summary +=f"\n\n✅ Order #{order_id} placed succesfully!\nWe will contact you soon."

                    msg.body(summary)

                    #clear cart and session
                    user_cart.pop(from_number, None)
                    user_sessions.pop(from_number, None)

            else:
                msg.body("Please reply with a valid number: 1, 2 or 3.")

            return str(response)


            

    elif "menu" in incoming_msg:
        products = get_products()
        menu = "Our products:\n\n"
        for i, (key, value) in enumerate(products.items(), start=1):
            menu += f"{i}. {value['name']} - ${value['price']}\n"
        menu += "\nType 'order' to place an order."
        msg.body(menu)
        return str(response)
    
    elif "hello" in incoming_msg:

            msg.body(
                "Hello! Welcome to our shop. 👋\n\n"
                "Type 'menu' to see products\n"
                "or 'order' to place an order."
            )

        

            return str(response)

    else:
            msg.body("Send 'menu' to see products or 'order' to place an order.")

    return str(response)


@app.route("/orders")
def view_orders():
    conn = sqlite3.connect("orders.db")
    c = conn.cursor()

    c.execute("SELECT * FROM orders")
    rows = c.fetchall()

    conn.close()

    html = "<h1>Orders</h1><br>"

    for r in rows:
        html += f"""
        Order #{r[0]} <br>
        Product: {r[1]} <br>
        Phone: {r[2]} <br>
        Location: {r[3]} <br>
        Status: {r[4]} <br>
        <hr>
        """

    return html

@app.route("/admin")
def admin():
    conn = sqlite3.connect("orders.db")
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()

    html = """
    <h1>Admin Panel</h1>
    <h2>Add New Product</h2>
    <form method="POST" action="/admin/add" enctype="multipart/form-data">
        Name: <input type="text" name="name"><br><br>
        Price: <input type="number" name="price"><br><br>
        Image File: <input type="file" name="image" accept="image/*"><br><br>
        Or Image URL: <input type="text" name="image_url" placeholder="https://..."><br><br>
        <input type="submit" value="Add Product">
    </form> 
    <h2>Current Products</h2>
    """

    for p in products:
        status = "In Stock" if p[4] == 1 else "Out of Stock"
        html += f"""
        <hr>
        <b>{p[1]}</b> - ${p[2]} - {status}<br>
        <img src="{p[3]}" width="100"><br>
        <a href="/admin/toggle/{p[0]}">Toggle Stock</a> | 
        <a href="/admin/delete/{p[0]}">Delete</a>
        <br>
        """

    return html


@app.route("/admin/add", methods=["POST"])
def admin_add():
    name = request.form.get("name")
    price = request.form.get("price")
    image_url = request.form.get("image_url", "").strip()
    image_file = request.files.get("image")

    if image_url:
        pass  # use the URL directly
    elif image_file and image_file.filename != "":
        filename = image_file.filename
        image_file.save(f"static/uploads/{filename}")
        image_url = f"/static/uploads/{filename}"
    else:
        image_url = ""

    conn = sqlite3.connect("orders.db")
    c = conn.cursor()
    c.execute("INSERT INTO products (name, price, image) VALUES (?, ?, ?)", (name, price, image_url))
    conn.commit()
    conn.close()

    return "<p>Product added! <a href='/admin'>Go back</a></p>"

@app.route("/admin/toggle/<int:product_id>")
def admin_toggle(product_id):
    conn = sqlite3.connect("orders.db")
    c = conn.cursor()
    c.execute("SELECT available FROM products WHERE id = ?", (product_id,))
    current = c.fetchone()[0]
    new_status = 0 if current == 1 else 1
    c.execute("UPDATE products SET available = ? WHERE id = ?", (new_status, product_id))
    conn.commit()
    conn.close()

    return "<p>Updated! <a href='/admin'>Go back</a></p>"


@app.route("/admin/delete/<int:product_id>")
def admin_delete(product_id):
    conn = sqlite3.connect("orders.db")
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

    return "<p>Deleted! <a href='/admin'>Go back</a></p>"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
