To run:

```sh
git clone https://github.com/grqx/pywebjudge
cd pywebjudge

cat create.sql insert.sql | sqlite3 --bail --batch app.db
# If sqlite3 is absent, use python3 -m sqlite3 app.db

python3 -mvenv .venv
. .venv/bin/activate
pip install -r requirements.txt

python3 -m src

deactivate
```

