from routs import app
from sql_init import deb_init
import os

base_dir=os.path.dirname(__file__)
instance_dir=os.path.join(base_dir,'Instance')
db_path=os.path.join(instance_dir,'chat_app.db')

if __name__ == '__main__':
    if not os.path.exists(instance_dir):
        os.path.makedirs(instance_dir)
    if not os.path.exists(db_path):
        print("Database not found. Initializing database schema...")
        deb_init()
    else:
        print('database found. starting server...')
    app.run(debug=True)