import email
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import requests
from flask_mysqldb import MySQL
import re
import MySQLdb
import pickle
import numpy as np
import sklearn
import csv
from csv import writer
from sklearn.preprocessing import MinMaxScaler
import xgboost

app = Flask(__name__)
price_model = pickle.load(open('xgb_regression_model.pkl','rb'))
rent_model = pickle.load(open('random_forest_regression_rent_model_V2 (1).pkl','rb'))
# price_model = 123
# rent_model = 324

### Flask Secret Key
app.secret_key = 'Admin@HousePricePrediction'

### Database Connection
app.config['MYSQL_HOST'] = '*********'
app.config['MYSQL_USER'] = '****'
app.config['MYSQL_PASSWORD'] = '***********'
app.config['MYSQL_DB'] = '********'

# Intialize MySQL
mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login',methods=['GET','POST'])
def login():
    ###Output message if something went wrong
    msg=''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        # Create variables for easy access
        email = request.form['email']
        password = request.form['password']

        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE email = %s AND password = %s', (email, password,))
        # Fetch one record and return result
        account = cursor.fetchone()

        # If account exists in accounts table in out database
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account['id']
            session['email'] = account['email']
            session['firstname'] = account['firstname']
            session['lastname'] = account['lastname']

            # Redirect to home page
            return redirect(url_for('home'))
        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect username/password!'

    return render_template('signin.html',msg=msg)

# http://localhost:5000/python/logout - this will be the logout page
@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('email', None)
   # Redirect to login page
   return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'] )
def register():
    # Output message if something goes wrong...
    msg = ''
    # Check if "firstname","lastname","email","phone" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'firstname' in request.form and 'lastname' in request.form and 'email' in request.form and 'phone' in request.form and 'password' in request.form:
        # Create variables for easy access
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE email = %s', (email,))
        account = cursor.fetchone()
        cursor.execute('SELECT * FROM accounts WHERE phone = %s', (phone,))
        phone_num = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            msg = 'Account with same email already exists!'
        elif phone_num:
            msg = "Account with same phone number already exists!"
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', firstname) or not re.match(r'[A-Za-z0-9]+', lastname):
            msg = 'firstname and lastname must contain only characters and numbers!'
        elif not firstname or not lastname or not email or not phone or not password:
            msg = 'Please fill out the form!'
        else:
            # Account doesn't exists and the form data is valid, now insert new account into accounts table
            cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s, %s, %s, NOW())', (firstname, lastname, email, phone, password,))
            mysql.connection.commit()
            msg = 'You have successfully registered!'

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)

@app.route('/home')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        return render_template('home.html', firstname=session['firstname'])
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    # Check if user is loggedin
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/predict_price', methods=['GET','POST'])
def predict_price():

    if request.method == 'POST':

        try:
            Area = int(request.form['area'])
            Area=Area/1000
        except ValueError:
            return jsonify({'error': 'Invalid input. Please enter a valid number for Area.'}), 400
        
        try:
            Bedroom = int(request.form['bedroom'])
        except ValueError:
            return jsonify({'error': 'Invalid input. Please enter a valid number for Bedrooms.'}), 400
        
        try:
            Bathroom = int(request.form['bathroom'])
        except ValueError:
            return jsonify({'error': 'Invalid input. Please enter a valid number for Bathrooms.'}), 400
        
        is_ready_to_move = 0
        ready = request.form['ready_to_move']
        if(ready=='Yes'):
            is_ready_to_move = 1
        elif(ready=='No'):
            is_ready_to_move = 0

        property_status_verified = 0
        status = request.form['property_status']
        if(status=='Yes'):
            property_status_verified = 1
        elif(status=='No'):
            property_status_verified = 0

        is_RERA_registered = 0
        Rera = request.form['rera']
        if(Rera=='Yes'):
            is_RERA_registered = 1
        elif(Rera=='No'):
            is_RERA_registered = 0

        is_studio = 0
        Studio = request.form['studio']
        if(Studio=='Yes'):
            is_studio = 1
        elif(Studio=='No'):
            is_studio = 0

        city_Ahmedabad = 0
        city_Bangalore = 0
        city_Chennai = 0
        city_Delhi = 0
        city_Hyderabad = 0
        city_Kolkata = 0
        city_Lucknow = 0
        city_Mumbai = 0
        City = request.form['city']
        if(City == 'Ahmedabad'): 
            city_Ahmedabad = 1
        elif(City == "Bangalore"): 
            city_Bangalore	= 1
        elif(City== "Chennai"): 
            city_Chennai = 1 
        elif(City == "Delhi"):
            city_Delhi = 1
        elif(City == "Hyderabad"): 
            city_Hyderabad = 1
        elif(City== "Kolkata"): 
            city_Kolkata = 1
        elif(City == "Lucknow"):
            city_Lucknow = 1
        elif(City == "Mumbai"):
            city_Mumbai = 1


        property_type_Apartment = 0
        property_type_Independent_Floor = 0
        property_type_Independent_House = 0
        property_type_Residential_Plot = 0
        property_type_Villa = 0
        Property = request.form['property_type']
        if(Property == "Apartment"): 
            property_type_Apartment = 1
        elif(Property == "Independent_Floor"): 
            property_type_Independent_Floor	= 1
        elif(Property == "Independent_House"): 
            property_type_Independent_House = 1
        elif(Property == "Residential_Plot"): 
            property_type_Residential_Plot = 1
        elif(Property == "Villa"): 
            property_type_Villa = 1



        furnish_type_Furnished = 0
        furnish_type_Semi_Furnished = 0
        furnish_type_Unfurnished = 0
        Furnish = request.form['furnish_type']
        if(Furnish == "Furnished"): 
            furnish_type_Furnished = 1
        elif(Furnish == "Semi Furnished"): 
            furnish_type_Semi_Furnished	= 1
        elif(Furnish == "Unfurnished"): 
            furnish_type_Unfurnished = 1

        price_data = [[Bedroom,Area,is_ready_to_move,property_status_verified,is_RERA_registered,is_studio,property_type_Apartment,property_type_Independent_Floor,property_type_Independent_House,property_type_Residential_Plot,property_type_Villa,furnish_type_Furnished,furnish_type_Semi_Furnished,furnish_type_Unfurnished,city_Ahmedabad,city_Bangalore,city_Chennai,city_Delhi,city_Hyderabad,city_Kolkata,city_Lucknow,city_Mumbai]]
        
        with open('price_user_input.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            new_Area = Area*1000
            writer.writerow([Bedroom,new_Area,Bathroom,is_ready_to_move,property_status_verified,is_RERA_registered,is_studio,property_type_Apartment,property_type_Independent_Floor,property_type_Independent_House,property_type_Residential_Plot,property_type_Villa,furnish_type_Furnished,furnish_type_Semi_Furnished,furnish_type_Unfurnished,city_Ahmedabad,city_Bangalore,city_Chennai,city_Delhi,city_Hyderabad,city_Kolkata,city_Lucknow,city_Mumbai])

        price_prediction = price_model.predict([[Bedroom,Area,is_ready_to_move,property_status_verified,is_RERA_registered,is_studio,property_type_Apartment,property_type_Independent_Floor,property_type_Independent_House,property_type_Residential_Plot,property_type_Villa,furnish_type_Furnished,furnish_type_Semi_Furnished,furnish_type_Unfurnished,city_Ahmedabad,city_Bangalore,city_Chennai,city_Delhi,city_Hyderabad,city_Kolkata,city_Lucknow,city_Mumbai]])
        price_prediction = price_prediction*10000000
        output=round(price_prediction[0],2)
        if output<0:
            return render_template('model_price_prediction.html',prediction_text="Sorry You Can't Sell The House")
        else:
            return render_template('model_price_prediction.html',prediction_text="You Can Sell The House At {}".format(output))

    else:
        return render_template('model_price.html')

@app.route('/predict_rent', methods=['GET','POST'])
def predict_rent():
    if request.method == 'POST':

        try:
            Area = int(request.form['area'])
            Area=Area/1000
        except ValueError:
            return jsonify({'error': 'Invalid input. Please enter a valid number for Area.'}), 400
        
        try:
            Bedroom = int(request.form['bedroom'])
        except ValueError:
            return jsonify({'error': 'Invalid input. Please enter a valid number for Bedrooms.'}), 400
        
        try:
            Bathroom = int(request.form['bathroom'])
        except ValueError:
            return jsonify({'error': 'Invalid input. Please enter a valid number for Bathrooms.'}), 400
        
        Area = int(request.form['area'])
        Area = Area/1000
        
        Bedroom = int(request.form['bedroom'])
        
        Bathroom = int(request.form['bathroom'])

        city_Ahmedabad = 0
        city_Bangalore	= 0
        city_Chennai = 0
        city_Delhi = 0
        city_Hyderabad = 0
        city_Kolkata = 0
        city_Mumbai = 0
        city_Pune = 0
        City = request.form['city']
        if(City == 'Ahmedabad'): 
            city_Ahmedabad = 1
        elif(City == "Bangalore"): 
            city_Bangalore	= 1
        elif(City== "Chennai"): 
            city_Chennai = 1 
        elif(City == "Delhi"):
            city_Delhi = 1
        elif(City == "Hyderabad"): 
            city_Hyderabad = 1
        elif(City== "Kolkata"): 
            city_Kolkata = 1
        elif(City == "Mumbai"):
            city_Mumbai = 1
        elif(City == "Pune"):
            city_Pune = 1

        property_type_Apartment = 0
        property_type_Independent_Floor = 0
        property_type_Independent_House = 0
        property_type_Penthouse = 0
        property_type_Studio_Apartment = 0
        property_type_Villa = 0
        Property = request.form['property_type']
        if(Property == "Apartment"): 
            property_type_Apartment = 1
        elif(Property == "Independent_Floor"): 
            property_type_Independent_Floor	= 1
        elif(Property == "Independent_House"): 
            property_type_Independent_House = 1
        elif(Property == "Penthouse"): 
            property_type_Penthouse = 1
        elif(Property == "Studio_Apartment"): 
            property_type_Studio_Apartment = 1
        elif(Property == "Villa"): 
            property_type_Villa = 1

        layout_type_BHK = 0
        layout_type_RK = 0
        Layout = request.form['layout_type']
        if(Layout == "BHK"): 
            layout_type_BHK = 1
        elif(Layout == "RK"): 
            layout_type_RK = 1

        furnish_type_Furnished = 0
        furnish_type_Semi_Furnished = 0
        furnish_type_Unfurnished = 0
        Furnish = request.form['furnish_type']
        if(Furnish == "Furnished"): 
            furnish_type_Furnished = 1
        elif(Furnish == "Semi Furnished"): 
            furnish_type_Semi_Furnished	= 1
        elif(Furnish == "Unfurnished"): 
            furnish_type_Unfurnished = 1

        seller_type_AGENT = 0
        seller_type_BUILDER = 0
        seller_type_OWNER = 0            
        Seller = request.form['seller_type']
        if(Seller == "Agent"): 
            seller_type_AGENT = 1
        elif(Seller == "Builder"): 
            seller_type_BUILDER	= 1
        elif(Seller == "Owner"): 
            seller_type_OWNER = 1
         
        rent_data = [[Bedroom,Area,Bathroom,seller_type_AGENT,seller_type_BUILDER,seller_type_OWNER,layout_type_BHK,layout_type_RK,property_type_Apartment,property_type_Independent_Floor,property_type_Independent_House,property_type_Penthouse,property_type_Studio_Apartment,property_type_Villa,furnish_type_Furnished,furnish_type_Semi_Furnished,furnish_type_Unfurnished,city_Ahmedabad,city_Bangalore,city_Chennai,city_Delhi,city_Hyderabad,city_Kolkata,city_Mumbai,city_Pune]]

        with open('rent_user_inputs.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            new_Area = Area*1000
            writer.writerow([Bedroom,new_Area,Bathroom,seller_type_AGENT,seller_type_BUILDER,seller_type_OWNER,layout_type_BHK,layout_type_RK,property_type_Apartment,property_type_Independent_Floor,property_type_Independent_House,property_type_Penthouse,property_type_Studio_Apartment,property_type_Villa,furnish_type_Furnished,furnish_type_Semi_Furnished,furnish_type_Unfurnished,city_Ahmedabad,city_Bangalore,city_Chennai,city_Delhi,city_Hyderabad,city_Kolkata,city_Mumbai,city_Pune])

        prediction = rent_model.predict(rent_data)
        prediction = prediction*10000
        output=round(prediction[0],2)
        if output<0:
            return render_template('model_rent_prediction.html',prediction_text="Sorry You Can't Rent The House")
        else:
            return render_template('model_rent_prediction.html',prediction_text="You Can Rent The House At {}".format(output))

    else:
        return render_template('model_rent.html')


if __name__ == "__main__":
    app.run(debug=True, port=5001)
