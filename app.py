import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database

uri = os.getenv("DATABASE_URL")
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://")
db = SQL(uri)

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    def index():
    """Show portfolio of stocks"""
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    print('user', user)
    try:
        data = db.execute("SELECT symbol, name, sum(shares) as total_shares, sum(total) as total FROM purchases WHERE user_id = ? group by symbol HAVING total_shares>0", user[0]["id"])
        total_purchases = db.execute("SELECT sum(total) as total FROM purchases WHERE user_id = ?", user[0]["id"])
        stock_prices = []

        for stock in data:
            stocks = {}
            price = lookup(stock['symbol'])
            stocks['symbol'] = stock['symbol']
            stocks['price'] = price['price']
            stock_prices.append(stocks)
        if data:
            price = lookup(data[0]["symbol"])
            stock_price = price["price"]
            return render_template("index.html", user=user[0], data= zip(data,stock_prices), total=total_purchases[0]['total'])
    except:
        return render_template("starter.html", user=user[0])

    # get the total for all owned shares based on share count and current share price
    print('Data', data)

    stock_prices = []

    for stock in data:
        stocks = {}
        price = lookup(stock['symbol'])
        stocks['symbol'] = stock['symbol']
        stocks['price'] = price['price']
        stock_prices.append(stocks)
    if data:
        price = lookup(data[0]["symbol"])
        stock_price = price["price"]
        return render_template("index.html", user=user[0], data= zip(data,stock_prices), total=total_purchases[0]['total'])
    else:
        return render_template("starter.html", user=user[0])


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Get stock quote."""
    if request.method == "GET":
        return render_template('buy.html')

    if request.method == "POST":
        #check if we have the symbol
        if not request.form.get("symbol"):
            return apology("Sorry you must enter a symbol", 400)

        elif not request.form.get("shares"):
            return apology("please enter a positive share count", 400)

        else:
            symbol = request.form.get("symbol")
            shares = request.form.get("shares")

            print('shares', shares)


            try:
                int(shares)
                if int(shares)<0:
                    return apology("Sorry you must enter a postive number of shares", 400)
                shares = int(shares)
                symbol = symbol.upper()
                response = lookup(symbol)
                if not response:
                    return apology("Sorry symbol does not exist", 400)
                else:
                    name = response["name"]
                    price = response["price"]

                    # Query database for id
                    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
                    print("user", user)
                    funds = int(user[0]['cash'])
                    total = int(shares * price)
                    if total > funds:
                        return apology("sorry not enough funds available", 400)
                    else:
                        db.execute("INSERT INTO purchases (user_id, date, symbol, name, shares, share_price, total) VALUES(?, ?, ?, ?, ?, ?, ?)", user[0]["id"], date.today(), symbol, name, shares, price, total)
                        db.execute("UPDATE users SET cash = ? WHERE id = ?", funds-total, user[0]["id"])
                        return redirect('/')
            except ValueError:
                return apology("Please enter a whole integer for number of shares", 400)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""  """Show portfolio of stocks"""
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    data = db.execute("SELECT symbol, shares, share_price, date FROM purchases WHERE user_id = ? order by date", user[0]["id"])

    return render_template("history.html", data=data)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template('quote.html')

    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Sorry you must enter a symbol", 400)
        else:
            symbol = request.form.get("symbol")
            symbol = symbol.upper()
            response = lookup(symbol)
            if not response:
                return apology("Sorry that is not an accurate symbol", 400)
            else:
                return render_template("quoted.html", symbol=response["symbol"], name=response["name"], price=usd(response["price"]))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        user = db.execute("SELECT * FROM users WHERE username = ?", username)
        print('user', user)

        if not username:
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 400)

        # Ensure confirmation was submitted
        elif not confirmation:
            return apology("please confirm your password", 400)

        # Make sure passwords match
        elif password != confirmation:
            return apology("your passwords don't match", 400)

         # Ensure username was submitted
        if not user:
            # Hash password
            hashpassword = generate_password_hash(password)

            # Register User
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hashpassword)

            return redirect('/')
        else:
            return apology("sorry that username is taken", 400)
    else:
        return render_template('register.html')

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    data = db.execute("SELECT symbol, name, sum(shares) as total_shares, sum(total) as total FROM purchases WHERE user_id = ? group by symbol HAVING total_shares>0", user[0]["id"])

    print('user', user)
    print('data', data)

    if request.method == "POST":
        #check if we have the symbol
        if not request.form.get("symbol"):
            return apology("Sorry you must enter a symbol", 400)

        elif not request.form.get("shares"):
            return apology("please enter a positive share count", 400)

        else:
            symbol = request.form.get("symbol")
            shares = int(request.form.get("shares"))
            for stock in data:
                if stock['symbol'] == symbol:
                    currentshares = stock['total_shares']
            if shares < 0:
                return apology("please enter a positive share count", 400)
            elif shares > currentshares:
                return apology("Sorry, try again, you don't have that many shares in your account", 400)
            else:
                symbol = symbol.upper()
                response = lookup(symbol)
                if not response:
                    return apology("Sorry symbol does not exist", 400)
                else:
                    name = response["name"]
                    price = response["price"]
                    funds = int(user[0]['cash'])
                    proceeds = int(shares * price)
                    db.execute("INSERT INTO purchases (user_id, date, symbol, name, shares, share_price, total) VALUES(?, ?, ?, ?, ?, ?, ?)", user[0]["id"], date.today(), symbol, name, -shares, price, proceeds)
                    db.execute("UPDATE users SET cash = (cash+?) WHERE id = ?", proceeds, user[0]["id"])
                    return redirect('/')
    else:
        return render_template('sell.html', data = data)
