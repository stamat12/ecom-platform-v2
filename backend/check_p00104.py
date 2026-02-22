import sqlite3
from pathlib import Path

db_path = Path('legacy/cache/inventory.db')

if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    
    # Check for range P0010482-P0010490
    print('Checking P0010482 to P0010490...')
    cursor = conn.cursor()
    cursor.execute('SELECT "SKU (Old)", "Total Cost Net" FROM inventory WHERE "SKU (Old)" IN (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                  ('P0010482', 'P0010483', 'P0010484', 'P0010485', 'P0010486', 'P0010487', 'P0010488', 'P0010489', 'P0010490'))
    results = cursor.fetchall()
    if results:
        for row in results:
            print(f'  {row[0]}: €{row[1]}')
    else:
        print('  NONE FOUND')
    
    # Check if P00104xx range exists at all
    print('\nChecking P00104xx range...')
    cursor.execute('SELECT COUNT(*) FROM inventory WHERE "SKU (Old)" LIKE "P00104%"')
    count = cursor.fetchone()[0]
    print(f'  Found {count} SKUs matching P00104%')
    
    conn.close()
else:
    print(f'DB not found at {db_path}')
