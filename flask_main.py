"""
Flask web app connects to Mongo database.
Keep a simple list of dated memoranda.

Representation conventions for dates: 
   - We use Arrow objects when we want to manipulate dates, but for all
     storage in database, in session or g objects, or anything else that
     needs a text representation, we use ISO date strings.  These sort in the
     order as arrow date objects, and they are easy to convert to and from
     arrow date objects.  (For display on screen, we use the 'humanize' filter
     below.) A time zone offset will 
   - User input/output is in local (to the server) time.  
"""

import flask
from flask import render_template
from flask import request
from flask import url_for

import json
import logging

# Date handling 
import arrow # Replacement for datetime, based on moment.js
import datetime # But we may still need time
from dateutil import tz  # For interpreting local times

# Mongo database
from pymongo import MongoClient
from bson import ObjectId


###
# Globals
###
import CONFIG

app = flask.Flask(__name__)

print("Entering Setup")
try: 
    dbclient = MongoClient(CONFIG.MONGO_URL)
    db = dbclient.memos
    collection = db.dated

except:
    print("Failure opening database.  Is Mongo running? Correct password?")
    sys.exit(1)

import uuid
app.secret_key = str(uuid.uuid4())

###
# Pages
###

@app.route("/")
@app.route("/index")
def index():
  app.logger.debug("Main page entry")
  app.logger.debug("Getting memos now")
  flask.session['memos'] = get_memos()
  app.logger.debug("Displaying all memos")
  for memo in flask.session['memos']:
      app.logger.debug("Memo: " + str(memo))
  return flask.render_template('index.html')

@app.route("/create")
def create():
    app.logger.debug("Create")
    return flask.render_template('create.html')


@app.errorhandler(404)
def page_not_found(error):
    app.logger.debug("Page not found")
    return flask.render_template('page_not_found.html',
                                 badurl=request.base_url,
                                 linkback=url_for("index")), 404

#################
#
# Functions used within the templates
#
#################

# NOT TESTED with this application; may need revision 
#@app.template_filter( 'fmtdate' )
# def format_arrow_date( date ):
#     try: 
#         normal = arrow.get( date )
#         return normal.to('local').format("ddd MM/DD/YYYY")
#     except:
#         return "(bad date)"

@app.template_filter( 'humanize' )
def humanize_arrow_date( date ):
    """
    Date is internal UTC ISO format string.
    Output should be "today", "yesterday", "in 5 days", etc.
    Arrow will try to humanize down to the minute, so we
    need to catch 'today' as a special case. 
    """
    try:
        then = arrow.get(date).to('local')
        now = arrow.utcnow().to('local')
        if then.date() == now.date():
            human = "Today"
        else: 
            human = then.humanize(now)
            if human == "in a day":
                human = "Tomorrow"
    except: 
        human = date
    return human

@app.route("/_create")
def create_memo():
    """
    Creates and insert a new memo into the database.
    """
    date = request.args.get('date', 0, type=str)
    memo = request.args.get('memo', 0, type=str)
    
    insert_memo(date,memo)
    
    return flask.redirect("/index")

@app.route("/_delete")
def delete_memo():
    """
    Deletes entry by ID
    """
    print("Getting memo id...")
    memoID = request.args.get('memoID', 0, type=str)
    print("The memo id is " + memoID)
    print("Deleting memo...")

    memo = collection.find_one({"_id": ObjectId(memoID)})
    collection.remove(memo)
    print("Deleted! Redirecting to index.")
    
    return flask.redirect("/index")

#############
#
# Functions available to the page code above
#
##############
def get_memos():
    """
    Returns all memos in the database, in a form that
    can be inserted directly in the 'session' object.
    """
    print("get_memos() started")
    records = [ ]
    for record in collection.find( { "type": "dated_memo" } ):
        record['date'] = arrow.get(record['date']).isoformat()
        del record['_id']
        records.append(record)

    records.sort(key=lambda r: r["date"])
    return records

def insert_memo(date, memo):
    """
    """
    print("Inserting memo")
    print("********** The date is " + str(date))
    dt = arrow.get(date, 'MM/DD/YYYY').replace(tzinfo='local')
    iso_dt = dt.isoformat()
    print("Compiling record from data")
    record = {
                "type": "dated_memo",
                "date": iso_dt,
                "text": memo
                }
    collection.insert(record)
    print("Memo has been inserted into the database")

    return

if __name__ == "__main__":
    # App is created above so that it will
    # exist whether this is 'main' or not
    # (e.g., if we are running in a CGI script)
    app.debug=CONFIG.DEBUG
    app.logger.setLevel(logging.DEBUG)
    # We run on localhost only if debugging,
    # otherwise accessible to world
    if CONFIG.DEBUG:
        # Reachable only from the same computer
        app.run(port=CONFIG.PORT)
    else:
        # Reachable from anywhere 
        app.run(port=CONFIG.PORT,host="0.0.0.0")

    
