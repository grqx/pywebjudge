from flask import Flask
from .routes import setup_flask

def entry():
    fapp = Flask('pywebjudge')
    setup_flask(fapp)
    fapp.run(debug=True)

