from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set to a secure random key in production

# Database connection function
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            database='ecomDB',
            user='root',
            password=''
        )
        if conn.is_connected():
            print("Database connected successfully.")
        return conn
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None


# Login required decorator
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("You must be logged in to access this page", category="danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__  # Ensure the original function name is preserved
    return wrapper


@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/product_page')
def product_page():
    return render_template('product_page.html')

@app.route('/user_home')
@login_required
def user_home():
    return render_template('user_home.html')

@app.route('/admin_home')
@login_required
def admin_home():
    return render_template('admin_home.html')

@app.route('/superadmin_home')
@login_required
def superadmin_home():
    return render_template('superadmin_home.html')

# Cart route for logged-in users
@app.route('/cart')
@login_required
def cart():
    return render_template('cart.html')

# Account route for logged-in users
@app.route('/account_page')
@login_required
def account():
    return render_template('account_page.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    flash("You have been logged out", category="info")
    return redirect(url_for('landing'))

@app.route('/admin_home_user', methods=['GET'])
@login_required
def admin_home_user():
    if session.get('role') != 'admin':
        flash("Access restricted", category="danger")
        return redirect(url_for('home'))
    return render_template('admin_home_user.html')


@app.route('/admin_home_sellers', methods=['GET'])
@login_required
def admin_home_sellers():
    if session.get('role') != 'admin':
        flash("Access restricted", category="danger")
        return redirect(url_for('home'))
    return render_template('admin_home_sellers.html')

@app.route('/admin_home_reg', methods=['GET'])
@login_required
def admin_home_reg():
    # Check if the user is an admin
    if session.get('role') != 'admin':
        flash("Access restricted", category="danger")
        return redirect(url_for('home'))
    
    # Establish a database connection
    conn = get_db_connection()
    if conn is None:
        flash("Failed to connect to the database", "danger")
        return redirect(url_for('home'))

    try:
        cursor = conn.cursor(dictionary=True)

        # Fetch all seller applications from the database
        cursor.execute("SELECT * FROM sellers")
        rows = cursor.fetchall()

        # Render the template and pass the sellers data
        return render_template('admin_home_reg.html', sellers=rows)

    except Error as e:
        print("Error:", e)
        flash("An error occurred while fetching seller applications", "danger")
        return redirect(url_for('home'))

    finally:
        if conn:
            conn.close()  # Close the database connection


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db_connection()
        if conn is None:
            flash("Database connection error")
            return redirect(url_for('login'))

        try:
            email = request.form.get('email')
            password = request.form.get('password')

            # Validate required fields
            if not email or not password:
                flash("Both email and password are required", category="danger")
                return redirect(url_for('login'))

            # Email format validation
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                flash("Invalid email format", category="danger")
                return redirect(url_for('login'))

            cursor = conn.cursor()

            # Fetch the user data
            query = "SELECT id, password, role FROM users WHERE email = %s"
            cursor.execute(query, (email,))
            user = cursor.fetchone()

            if user:
                # Check if the password matches (no hashing, just direct comparison)
                if user[1] == password:  # Plain-text password check
                    session['user_id'] = user[0]  # Store user ID in session
                    session['role'] = user[2]  # Store role in session

                    # Redirect based on user role
                    if session['role'] == 'admin':
                        return redirect(url_for('admin_home'))
                    elif session['role'] == 'superadmin':
                        return redirect(url_for('superadmin_home'))
                    elif session['role'] == 'user':
                        return redirect(url_for('user_home'))
                    else:
                        flash("Unknown role encountered", category="danger")
                        return redirect(url_for('login'))
                else:
                    flash("Invalid email or password", category="danger")
                    return redirect(url_for('login'))
            else:
                flash("Invalid email or password", category="danger")
                return redirect(url_for('login'))

        except Error as e:
            print(f"Login error: {e}")
            flash("An internal database error occurred", category="danger")
            return redirect(url_for('login'))
        finally:
            if conn:
                conn.close()  # Ensure connection is closed

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        conn = get_db_connection()
        if conn is None:
            flash("Failed to connect to the database")
            return redirect(url_for('signup'))

        try:
            email = request.form.get('email')
            password = request.form.get('password')
            role = 'user'  # Default role is 'user'

            # Validate required fields
            if not email or not password:
                flash("Email and password are required", category="danger")
                return redirect(url_for('signup'))

            # Email format validation
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                flash("Invalid email format", category="danger")
                return redirect(url_for('signup'))

            # Password validation (minimum length)
            if len(password) < 6:
                flash("Password must be at least 6 characters long", category="danger")
                return redirect(url_for('signup'))

            # Check if the email already exists
            cursor = conn.cursor()
            cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("Email already exists, please log in instead", category="danger")
                return redirect(url_for('login'))

            # Insert the user into the 'users' table (no hashing, storing plain text password)
            query = "INSERT INTO users (email, password, role) VALUES (%s, %s, %s)"
            cursor.execute(query, (email, password, role))  # Store plain-text password
            conn.commit()
            flash("User registered successfully!", category="success")  # Success message
            return redirect(url_for('login'))  # Redirect to login after successful signup

        except Error as e:
            print(f"Error while inserting user data: {e}")
            flash("Failed to register user", category="danger")
            return redirect(url_for('signup'))
        finally:
            if conn:
                conn.close()  # Ensure connection is closed

    return render_template('signup.html')


@app.route('/seller_registration', methods=['GET', 'POST'])
@login_required
def seller_registration():
    conn = get_db_connection()
    if conn is None:
        flash("Failed to connect to the database", "danger")
        return redirect(url_for('user_home'))

    user_id = session['user_id']
    try:
        cursor = conn.cursor(dictionary=True)

        # Check if the user already applied as a seller
        cursor.execute("SELECT * FROM sellers WHERE user_id = %s", (user_id,))
        existing_seller = cursor.fetchone()

        if existing_seller:
            if existing_seller['status'] == 'approved':
                # Check if the user hasn't seen the approval page yet
                if not session.get('seen_approval'):
                    session['seen_approval'] = True
                    return render_template('seller_approve.html')
                return redirect(url_for('seller_dashboard'))

            elif existing_seller['status'] == 'declined':
                flash("Your application was declined. You can reapply.")
            else:  # Pending status
                flash("Your application is still pending.", "info")
                return render_template('reg_after_sub.html')

        # Handle the form submission
        if request.method == 'POST':
            # Get form data
            first_name = request.form.get('firstName')
            last_name = request.form.get('lastName')
            email = request.form.get('email')
            phone_number = request.form.get('phoneNumber')
            address = request.form.get('address')
            postal_code = request.form.get('postalCode')
            business_name = request.form.get('businessName')
            description = request.form.get('description')

            # Validate required fields
            if not all([first_name, last_name, email, phone_number, address, postal_code, business_name, description]):
                flash("All fields are required.", "danger")
                return render_template('seller_registration.html')

            # Validate email format
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                flash("Invalid email format.", "danger")
                return render_template('seller_registration.html')

            # Validate phone number format (optional: add more strict validation if needed)
            if not re.match(r"^\+?\d{10,15}$", phone_number):  # Simple international phone number format
                flash("Invalid phone number. It should be a valid number.", "danger")
                return render_template('seller_registration.html')

            # Validate postal code (optional: adjust regex based on the country format)
            if not re.match(r"^\d{5,6}$", postal_code):  # Example for a 5 or 6 digit postal code
                flash("Invalid postal code format.", "danger")
                return render_template('seller_registration.html')

            # Insert seller application into the database
            cursor.execute(""" 
                INSERT INTO sellers (user_id, first_name, last_name, email, phone_number, address, postal_code, business_name, description, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            """, (user_id, first_name, last_name, email, phone_number, address, postal_code, business_name, description))
            conn.commit()

            flash("Your seller application has been submitted successfully!", "success")
            return render_template('reg_after_sub.html')

    except Error as e:
        print(f"Error during seller registration: {e}")
        flash("An error occurred. Please try again later.", "danger")
    finally:
        cursor.close()
        conn.close()

    # Render the seller registration form
    return render_template('seller_registration.html')

@app.route('/approve_seller/<int:id>', methods=['POST'])
@login_required
def approve_seller(id):
    if session.get('role') != 'admin':
        flash("Access restricted", category="danger")
        return redirect(url_for('home'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error", category="danger")
        return redirect(url_for('admin_home_reg'))

    try:
        cursor = conn.cursor()
        # Update seller's status to 'approved'
        query = "UPDATE sellers SET status = 'approved' WHERE id = %s"
        cursor.execute(query, (id,))
        conn.commit()

        flash("Seller approved successfully!", category="success")
    except Error as e:
        print(f"Error approving seller: {e}")
        flash("Failed to approve seller", category="danger")
        conn.rollback()
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin_home_reg'))



@app.route('/decline_seller/<int:id>', methods=['POST'])
@login_required
def decline_seller(id):
    if session.get('role') != 'admin':
        flash("Access restricted", category="danger")
        return redirect(url_for('home'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error", category="danger")
        return redirect(url_for('admin_home_reg'))

    try:
        cursor = conn.cursor()
        # Update seller's status to 'declined'
        query = "UPDATE sellers SET status = 'declined' WHERE id = %s"
        cursor.execute(query, (id,))
        conn.commit()

        flash("Seller declined successfully!", category="success")
    except Error as e:
        print(f"Error declining seller: {e}")
        flash("Failed to decline seller", category="danger")
        conn.rollback()
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin_home_reg'))

if __name__ == '__main__':
    app.run(debug=True)
