import os, requests, time, json
from flask import Flask, session, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


app = Flask(__name__)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

#Functions
def match(username, password):
    #seach database for username and password
    command = "SELECT * FROM userinfo WHERE username LIKE '%%%(username)s%%'" %{"username":username, "password":password}
    userinfo =  db.execute(command).fetchall()
    #if it retreived a valid username and password from database
    if userinfo[0][0]!=[] and userinfo[0][1]!=[]:
        #if they match
        if username==userinfo[0][0] and password==userinfo[0][1]:
            return True
    else:
        return False

# Link to html files-------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")
    
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method=="POST":
        #clear session name every time someone goes to sign up for an account
        session["name"]=[]
            #the html form accepts a name, can be stored in place specific to the user
        if session.get("name") is None:
            session["name"]=[]
            session["password"]=[]
        if request.method=="POST": #take register request from user, access the form
            name=request.form.get("name")
            password=request.form.get("password")
            session["name"]=name
            session["password"]=password
            #if name and password exist, ie. they didn't submit a blank form 
            if name!="" or password!="":
                # insert username and password to database
                db.execute("INSERT INTO userinfo(username, password) VALUES (:username, :password)", {"username":name, "password":password})
                db.commit()
                return render_template("login.html", name=name, password=password, message='1')
            else:
                #return to index to register for an account
                return render_template("index.html", message = 1)
    else:
        return render_template("login.html", message='3')

@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method=="POST": #take login request from user, access the form
        name=request.form.get("name")
        password=request.form.get("password")
        #username and password match database, login successful
        if match(name, password):
            session["name"]=name
            session["password"]=password
            return render_template("search.html", name=name, password=password)
        #username and password dont match database, login unsuccessful
        else:
            return render_template("login.html", name=name, password=password, message=2)
    
    if request.method=="GET": #refresh from book page to search again
        name=session.get("name")
        password=session.get("password")
        return render_template("search.html", name=name, password=password)


#book page for display of book info and reviews, after search query
@app.route("/book", methods=["GET", "POST"])
def book():
    #accepts title, author, isbn number
    # #take request from user, access the form
    searchtype=request.args.get("searchtype")
    searchtext=request.args.get("searchtext")

    #query database for books with matching credentials
    if searchtext=='year':
        command = "SELECT * FROM books WHERE %(searchtype)s = '%%%(searchtext)s%%'" %{'searchtype':searchtype, 'searchtext':searchtext}
    else:
        command = "SELECT * FROM books WHERE %(searchtype)s LIKE '%%%(searchtext)s%%'" %{'searchtype':searchtype, 'searchtext':searchtext}
    booksfound =  db.execute(command).fetchall()

    return render_template("book.html", searchtype=searchtype, searchtext=searchtext, numfound=len(booksfound), booksfound=booksfound)

@app.route("/review", methods=["GET", "POST"])
def review():
    if request.method=="GET":
        #cover up empty review
        rev = [0,0]
        #load initial page
        isbn=request.args.get("isbn")
        session['isbn']=isbn
        command = "SELECT * FROM books WHERE isbn LIKE '%%%(isbn)s%%'" %{'isbn':isbn}
        bookdata = db.execute(command).fetchall()
        #retreive reviews for display
        command = "SELECT * FROM reviews WHERE isbn LIKE '%%%(isbn)s%%'" %{'isbn':isbn}
        rev =  db.execute(command).fetchall()
        # make requests to Goodreads API
        url = "https://www.goodreads.com/book/review_counts.json"
        res = requests.get(url, params={"key": "1534yrlGntKmEvl4P5DlZg", "isbns": isbn})

        if res.ok:
            res = res.json()
            avgrate = res["books"][0]["average_rating"]
            numrevs = res["books"][0]["ratings_count"]
            session['avgrate']=avgrate
            session['numrevs']=numrevs
            return render_template("review.html", bookdata=bookdata, isbn=isbn, avgrate = avgrate, numrevs=numrevs, rev=rev, revcount=len(rev))
        else: 
            session['avgrate']=0
            session['numrevs']=0
            #if there are no reviews on goodreads:
            return render_template("review.html", bookdata=bookdata, isbn=isbn, avgrate = 0, numrevs = 0, rev=rev, revcount=len(rev))

    #reload page after review is submitted
    if request.method=="POST":
        #cover up empty review
        rev = [0,0]
        isbn=session.get('isbn')
        command = "SELECT * FROM books WHERE isbn LIKE '%%%(isbn)s%%'" %{'isbn':isbn}
        bookdata = db.execute(command).fetchall()

        #access previous goodreads review data
        avgrate=session['avgrate']
        numrevs=session['numrevs']

        #get review info from user submitted form
        review = request.form.get("review")
        rating = request.form.get("rate")

        # insert review to database
        db.execute("INSERT INTO reviews(username, isbn, review, rating) VALUES (:username, :isbn, :review, :rating)", {"username":session["name"], "isbn":isbn, "review":review, "rating":rating})
        db.commit()

        #now retreive reviews for display
        command = "SELECT * FROM reviews WHERE isbn LIKE '%%%(isbn)s%%'" %{'isbn':isbn}
        rev =  db.execute(command).fetchall()

        return render_template("review.html", bookdata=bookdata, isbn=isbn, avgrate = avgrate, numrevs=numrevs, rev=rev, revcount=len(rev))

        




# #main
# def main():

# if __name__ == "__main__":
#     main()