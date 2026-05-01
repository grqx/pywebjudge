from flask import Flask
from .routes import setup_flask_routes

def entry():
    fapp = Flask('pywebjudge')
    setup_flask_routes(fapp)
    fapp.run(debug=True)

