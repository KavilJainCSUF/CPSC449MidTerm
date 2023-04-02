from flask import Flask, render_template
import pymysql

app = Flask(__name__)

conn = pymysql.connect(
    host='localhost',
    user='root',
    password='Kavil@514',
    db='mid_term',
    cursorclass=pymysql.cursors.DictCursor
)

@app.route('/')
def index():
    """Home Page"""
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host ="localhost", port = int("5000"))
