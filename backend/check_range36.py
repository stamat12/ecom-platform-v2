import sqlite3
from pathlib import Path

db_path = Path('legacy/cache/inventory.db')
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print('Checking P0010036 to P0010040...')
cursor.execute('SELECT "SKU (Old)", "Total Cost Net" FROM inventory WHERE "SKU (Old)" IN (?, ?, ?, ?, ?)', 
              ('P0010036', 'P0010037', 'P0010038', 'P0010039', 'P0010040'))
for row in cursor.fetchall():
    print(f'  {row[0]}: EUR {row[1]}')

conn.close()
