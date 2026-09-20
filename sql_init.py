import sqlite3
import os

BASE_DIR=os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR=os.path.join(BASE_DIR,'Instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)
DB_PATH=os.path.join(INSTANCE_DIR,'chat_app.db')


def deb_init():
    con=sqlite3.connect(DB_PATH)
    cur=con.cursor()

    cur.execute("""
    PRAGMA foreign_keys=ON
    """)

    #TABLE FOR USERS
    try:
        cur.execute("""
        CREATE TABLE users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        deleted_at DATETIME DEFAULT NULL

        )

        """)

    #TABLE FOR CONVERSIONS
    except sqlite3.OperationalError as e:
        print("SQLite error:", e)

    try:
        cur.execute("""

        CREATE TABLE conversation(
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        type TEXT NOT NULL CHECK(type IN ('private','group')),
        name TEXT DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )

        """)

    #TABLE FOR CONVERSATION MEMBERS
    except sqlite3.OperationalError as e:
        print("SQLite error:", e)

    try:
        cur.execute("""
            CREATE TABLE conversation_members (
            
            conversation_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'member' CHECK(role IN ('admin','member','banned')),
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY(conversation_id,user_id),
            FOREIGN KEY(conversation_id)
                REFERENCES conversation(id)
                ON DELETE RESTRICT,
            FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE RESTRICT
            )

            """)
        
    except sqlite3.OperationalError as e:
        print("SQLite error:", e)
    try:
        cur.execute("""

        CREATE TABLE messages(
        
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        sender_id INTEGER NOT NULL,

        content TEXT NOT NULL,

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(conversation_id)
            REFERENCES conversation(id)
            ON DELETE RESTRICT,

        FOREIGN KEY(sender_id)
            REFERENCES users(id)
            ON  DELETE RESTRICT

        )

        """)
    except sqlite3.OperationalError as e:
        print("SQLite error:", e)

    try:
        cur.execute("""CREATE TABLE message_receipts (
    message_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    read_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (message_id, user_id),
    FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE RESTRICT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE RESTRICT
);


""")
    except sqlite3.OperationalError as e:
        print("SQLite error:", e)

    try:
        cur.execute("""
            CREATE INDEX idx_receipts_user ON message_receipts(user_id);
        """)
    except sqlite3.OperationalError as e:
        print("SQLite error:", e)

    try:
        cur.execute("""CREATE TABLE pending_registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    otp_code TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL );
        
    """)
            
    except sqlite3.OperationalError as e:
        print("SQLite error:", e) 

    try:
        cur.execute("""
                CREATE INDEX idx_pending_email ON pending_registrations(email);
            """)
    except sqlite3.OperationalError as e:
        print("SQLite error:", e)

    try:
        cur.execute("""
        CREATE INDEX idx_messages_conversation_time
        ON messages(conversation_id, created_at)
    """)
    except sqlite3.OperationalError as e:
        print("SQLite error:", e)

    try:
        cur.execute("""
            CREATE INDEX idx_conversation_members_user
            ON conversation_members(user_id)
        """)
    except sqlite3.OperationalError as e:
        print("SQLite error:", e)
    try:

        cur.execute("""
            CREATE INDEX idx_conversation_members_conversation
            ON conversation_members(conversation_id)
        """)

    except sqlite3.OperationalError as e:
        print("SQLite error:", e)
    con.commit()
    con.close()

if __name__ == '__main__':
    deb_init()

