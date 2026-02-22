import sqlite3
from pathlib import Path

# Find the DB - correct location
db_path = Path('legacy/cache/inventory.db')

if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check for P0010036 using correct column name
    print('Searching for P0010036...')
    cursor.execute('SELECT "SKU (Old)", "Total Cost Net" FROM inventory WHERE "SKU (Old)" = ?', ('P0010036',))
    row = cursor.fetchone()
    if row:
        print(f'Found: SKU={row[0]}, Cost={row[1]}')
    else:
        print('NOT FOUND')
    
    # Check what P00 SKUs exist
    print('\nP00xxxxx SKUs in database (first 10):')
    cursor.execute('SELECT "SKU (Old)", "Total Cost Net" FROM inventory WHERE "SKU (Old)" LIKE ? LIMIT 10', ('P00%',))
    for row in cursor.fetchall():
        print(f'  {row[0]}: €{row[1]}')
    
    conn.close()
else:
    print(f'DB not found at {db_path}')
