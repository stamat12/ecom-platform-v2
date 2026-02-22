import sqlite3
from pathlib import Path

# Find the DB
legacy_dir = Path('legacy')
db_path = legacy_dir / 'products' / 'inventory.db'

if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get column names
    cursor.execute('PRAGMA table_info(inventory)')
    columns = cursor.fetchall()
    print('Columns in inventory table:')
    for col in columns:
        print(f'  {col[1]} ({col[2]})')
    
    # Check for P0010036
    print('\nSearching for P0010036...')
    cursor.execute('SELECT SKU, Total_Cost_Net FROM inventory WHERE SKU = ?', ('P0010036',))
    row = cursor.fetchone()
    if row:
        print(f'Found: {row}')
    else:
        print('NOT FOUND')
    
    # Check what P00 SKUs exist
    print('\nP00 SKUs in database:')
    cursor.execute('SELECT SKU, Total_Cost_Net FROM inventory WHERE SKU LIKE ? LIMIT 10', ('P00%',))
    for row in cursor.fetchall():
        print(f'  {row}')
    
    conn.close()
else:
    print(f'DB not found at {db_path}')
