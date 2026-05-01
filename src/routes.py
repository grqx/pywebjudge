import typing
if typing.TYPE_CHECKING:
    from flask import Flask

def setup_flask_routes(fapp: Flask):
    fapp.route('/')(lambda: 'flask app!')

