"""This module serves as the CLI interface for the project. It runs the
web app. By default the flask instance is run with debug=False. This
could be changed when exactly one argument is provided and it is exactly
'debug' (case-sensitive match).
"""
import sys
from .routes import setup_flask

if __name__ == '__main__':
    setup_flask().run(debug=len(sys.argv) == 2 and sys.argv[1] == 'debug')
