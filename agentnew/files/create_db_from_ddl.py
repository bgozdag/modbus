import os
import sqlite3

os.system("rm agent.db")
conn = sqlite3.connect("agent.db")
with open("agent.ddl", 'rt') as f:
    schema = f.read()
conn.executescript(schema)
conn.commit()

os.system("rm webconfig.db")
conn = sqlite3.connect("webconfig.db")
with open("webconfig.ddl", 'rt') as f:
    schema = f.read()
conn.executescript(schema)
conn.commit()
