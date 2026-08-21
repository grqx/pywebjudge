import sys
from .routes import setup_flask

if __name__ == '__main__':
    setup_flask().run(debug=len(sys.argv) == 2 and sys.argv[1] == 'debug')
