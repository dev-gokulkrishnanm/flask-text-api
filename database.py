import sqlite3 as sql
from functools import wraps
from flask import request,jsonify
from flask_bcrypt import Bcrypt
import os
# Force an absolute path relative to the script directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR=os.path.join(BASE_DIR,'Instance')
DB_PATH = os.path.join(INSTANCE_DIR, 'chat_app.db')

bcrypt=Bcrypt()

def create_users(email,username,password):
    con=sql.connect(DB_PATH)
    cur=con.cursor()
    try:
        cur.execute("""

        INSERT INTO users(username,email,password) VALUES(?, ?, ?) returning id,username,email

        """,(username,email,password))

        res = cur.fetchone()
        con.commit()
        if res:
            return {"success": f"User {res[1]} is Created","id": res[0],"username":res[1],"email":res[2]}
        return None
        
    except sql.IntegrityError as e:
        err_msg = str(e).lower()
        if "users.email" in err_msg or "email" in err_msg:
            if "users.username" in err_msg or "username" in err_msg:
                return {"error": f"Username '{username}' is already taken."}
            return {"error": f"Email '{email}' is already registered."}
        
        elif "users.username" in err_msg or "username" in err_msg:
            if "users.email" in err_msg or "email" in err_msg:
                return {"error": f"Email '{email}' is already registered."}
            return {"error": f"Username '{username}' is already taken."}
        else:
            return {"error": "A user with that email or username already exists."}
    finally:
        con.close()

def fetch_user_by_name(username):
    try:
        con=sql.connect(DB_PATH)
        cur=con.cursor()
        cur.execute("""

        SELECT * FROM users WHERE username = ?

        """,(username,))
        user=cur.fetchone()
        return user
    
    except sql.Error as err:
        print(f'Database Error: {err}')
    finally:
        con.close()
def fetch_user_by_id(user_id):
    try:
        con=sql.connect(DB_PATH)
        cur=con.cursor()
        cur.execute("""

        SELECT * FROM users WHERE id = ?

        """,(user_id,))
        user=cur.fetchone()
        return user
    
    except sql.Error as err:
        print(f'Database Error: {err}')
    finally:
        con.close()
def fetch_user_by_email(email):
    try:
        con=sql.connect(DB_PATH)
        cur=con.cursor()
        cur.execute("""

        SELECT * FROM users WHERE email = ?

        """,(email,))
        user=cur.fetchone()
        return user
    
    except sql.Error as err:
        print(f'Database Error: {err}')
    finally:
        con.close()

def db_login(username,password):
    try:
        con=sql.connect(DB_PATH)
        con.row_factory=sql.Row
        cur=con.cursor()
        user=cur.execute(
            """SELECT * FROM users WHERE username = ?"""
        ,(username,))
        user=cur.fetchone()
        if user is None:
            return None
        user_dic=dict(user)
        if bcrypt.check_password_hash(user_dic['password'],password):
            return user_dic
        else:
            return None
    except ValueError as e:
        print(f"[Security Warning] Malformed or invalid hash in DB: {e}")
        return False
    except sql.Error as err:
        print(err)
    finally:
        con.close()

def update_user(user_id,value,new_value):
    query=f"UPDATE users SET {value} = ? WHERE id = ?"
    try:
        con=sql.connect(DB_PATH)
        cur=con.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        old_user=cur.fetchone()
        cur.execute(query,(new_value,user_id))
        con.commit()
        
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        updated_user = cur.fetchone()
        return updated_user,old_user
    except sql.Error as err:
        print(f'Database Error: {err}')
    finally:
        con.close()

def create_conversation_members(user_id,conversation_id,role):
    try:
        con=sql.connect(DB_PATH)
        cur=con.cursor()
        cur.execute("""
        
        INSERT INTO conversation_members(conversation_id,user_id, role) VALUES(?, ?,?)
        
        """,(conversation_id, user_id, role))
        con.commit()
    except sql.Error as err:
        print(f'Database Error: {err}')
    finally:
        con.close()

def create_private_chat(current_user_id,target_user_id):
    try:
        con=sql.connect(DB_PATH)
        cur=con.cursor()

        # 1. Create private conversation
        cur.execute("INSERT INTO conversation (type) VALUES ('private')")
        conversation_id = cur.lastrowid
        
        # 2. Add current user (sender)
        cur.execute(
            "INSERT INTO conversation_members (conversation_id, user_id) VALUES (?, ?)",
            (conversation_id, current_user_id)
        )
        
        # 3. Add target user
        cur.execute(
            "INSERT INTO conversation_members (conversation_id, user_id) VALUES (?, ?)",
            (conversation_id, target_user_id)
        )
        con.commit()
        return conversation_id
    except sql.Error as err:
        print(f'Database Error: {err}')
    finally:
        con.close()

def get_existing_private_chat(user_id_1, user_id_2):
    try:
        con = sql.connect(DB_PATH)
        cur = con.cursor()
        
        # Find a 'private' conversation that includes BOTH user_id_1 and user_id_2
        query = """
            SELECT cm1.conversation_id 
            FROM conversation_members cm1
            JOIN conversation_members cm2 ON cm1.conversation_id = cm2.conversation_id
            JOIN conversation c ON cm1.conversation_id = c.id
            WHERE c.type = 'private'
              AND cm1.user_id = ? 
              AND cm2.user_id = ?
        """
        cur.execute(query, (user_id_1, user_id_2))
        row = cur.fetchone()
        return row[0] if row else None
    
    except sql.Error as err:
        print(f'Database Error: {err}')
        return None
    finally:
        con.close()

def get_current_user_chats(user_id):
    try:
        con=sql.connect(DB_PATH)
        con.row_factory = sql.Row
        cur=con.cursor()
        cur.execute("""

        SELECT cm.conversation_id, cm.user_id AS partner_id,u.username 
        FROM conversation_members cm 
        JOIN conversation c ON cm.conversation_id = c.id 
        JOIN users u ON cm.user_id = u.id 
        WHERE c.type='private' 
        AND cm.user_id != ? 
        AND cm.conversation_id IN (SELECT conversation_id FROM conversation_members WHERE user_id = ?)

        """,(user_id,user_id,))
        result=[dict(s) for s in cur.fetchall()]
        

        return result
    
    except sql.Error as err:
        print(f'Database Error: {err}')
        return None
    finally:
        con.close()
def create_group(name, user_id):

    con=None
    con=sql.connect(DB_PATH)
    cur=con.cursor()
    try:
        
        cur.execute("""

        INSERT INTO conversation(type,name) VALUES('group', ?)
        
        """,(name,))
        conversation_id = cur.lastrowid

        cur.execute(""" 
        
        INSERT INTO conversation_members(conversation_id,user_id,role) VALUES(?, ?, ?)
        
        """,(conversation_id,user_id,'admin',))
        con.commit()
        return True,conversation_id

    except sql.Error as err:
        if con:
            con.rollback()
        print(f"Transaction failed and rolled back: {err}")
        return False,None

    finally:
        if con:
            con.close()

def delete_group(conversation_id):
    con=None
    con=sql.connect(DB_PATH)
    cur=con.cursor()
    con.row_factory=sql.Row
    try:
        
        cur.execute(""" 
        SELECT id, name FROM conversation
        WHERE id = ? and type = ?
        """,(conversation_id,'group',))

        row=cur.fetchone()

        cur.execute(""" 
        DELETE FROM conversation_members 
        WHERE conversation_id = ?""",(conversation_id,))

        cur.execute("""

        DELETE FROM conversation WHERE type = ? and id = ?

        """,('group',conversation_id,))
        con.commit()
        return True,row
    except sql.Error as err:
        if con:
            con.rollback()
        print(f"Transaction failed and rolled back: {err}")
        return False,None
    finally:
        if con:
            con.close()


def add_users_group(conversation_id,users_list):
    query = """
                INSERT OR IGNORE INTO conversation_members (conversation_id, user_id, role)
                VALUES (?, ?, ?)
            """
    
    members_data=[(conversation_id,user_id,'member') for user_id in users_list]
    con=None
    con=sql.connect(DB_PATH)
    cur=con.cursor()

    try:
        cur.executemany(query,members_data)
        con.commit()
        return True
    except sql.Error as err:
        if con:
            con.rollback()
        print(f"Failed to add members: {err}")
        return False
    finally:
        if con:
            con.close()

def is_group_admin(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        conversation_id=kwargs.get('conversation_id')
        current_user=getattr(request,'current_user',None)
        user_id=current_user.get('user_id') if current_user else None
        if not current_user or not user_id:
            return jsonify({"Error":"Missing Authentication or Conversation ID"}),401
        con=None
        con=sql.connect(DB_PATH)
        cur=con.cursor()

        try:
            
            cur.execute("""
            
            SELECT 1 
            FROM conversation_members 
            WHERE conversation_id = ? AND user_id = ? AND role = 'admin'

            """,(conversation_id, user_id,))
            is_admin =cur.fetchone()

            if not is_admin:
                return jsonify({"Error": "Unauthorized: You must be a group admin to perform this action"}), 403
        
        except sql.Error as err:
                print(f"Admin check failed: {err}")
                return jsonify({"Error": "Internal server error"}), 500
        finally:
            if con:
                con.close()
        return func(*args, **kwargs)
    return wrapper

def is_conversation_member(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        conversation_id=kwargs.get('conversation_id')
        current_user_id=request.current_user.get('user_id')
        if not conversation_id and not current_user_id:
            return jsonify({"Error": "Missing conversation or user context"}), 400

        con=None
        try:
            con=sql.connect(DB_PATH)
            cur=con.cursor()
            cur.execute("""

            SELECT 1 FROM conversation_members 
            WHERE conversation_id = ? 
            AND user_id = ?

            """,(conversation_id,current_user_id,))

            is_member = cur.fetchone() is not None
        except sql.Error as err:
            print(f"Auth check failed: {err}")
            return jsonify({"Error": "Database authorization check failed"}), 500
        finally:
            if con:
                con.close()

        if not is_member:
            return jsonify({"Error": "Forbidden: You are not a member of this chat"}), 403

        return func(*args,**kwargs)
    return wrapper
        
def get_group_list_by_id(conversation_id,user_id):
    con=None
    con=sql.connect(DB_PATH)
    cur=con.cursor()
    cur.row_factory=sql.Row
    try:
        cur.execute("""

        SELECT cm.conversation_id,cm.user_id,cm.role,u.username 
        FROM conversation_members cm
        JOIN users u ON cm.user_id = u.id
        WHERE conversation_id = ? 
        AND EXISTS(SELECT 1 FROM conversation_members WHERE conversation_id = ? and user_id = ? )

        """,(conversation_id,conversation_id,user_id,))
        mem_list=[dict(s) for s in cur.fetchall()]
        
        return mem_list
    except sql.Error as err:
        print(f"Error: {err}")
        return jsonify({"Error": "Internal server error"}), 500
    finally:
        if con:
            con.close()

def kickout_user(conversation_id,user_id):
    con=None
    con=sql.connect(DB_PATH)
    cur=con.cursor()
    try:
        cur.execute("""
        SELECT cm.user_id, u.username FROM conversation_members cm JOIN users u ON cm.user_id = u.id
        WHERE user_id = ? AND conversation_id = ?
        """,(user_id,conversation_id,))
        row=cur.fetchone()
        if row[0] == user_id:
            cur.execute("""DELETE FROM conversation_members 
                            WHERE user_id = ? 
                            AND conversation_id = ?""",(user_id,conversation_id,))
        con.commit()
        return cur.rowcount > 0,row
    except sql.Error as err:
        if con:
            con.rollback()
        print(f"Failed to remove user: {err}")
        return False,None
    
    finally:
        if con:
            con.close()
def send_message(conversation_id,user_id,message):
    con=None
    con=sql.connect(DB_PATH)
    cur=con.cursor()
    try:
        cur.execute("""

        INSERT INTO messages(conversation_id,sender_id,content) 
        VALUES(?, ?, ?)

        """,(conversation_id,user_id,message))
        con.commit()
        return cur.rowcount > 0
    
    except sql.Error as err:
        if con:
            con.rollback()
        print(f"Failed to remove user: {err}")
        return False
    finally:
        if con:
            con.close()
def get_messages(con_id):

    con=sql.connect(DB_PATH)
    con.row_factory=sql.Row
    cur=con.cursor()
    try:
        cur.execute("""
        
        SELECT m.id as message_id, m.sender_id, u.username, m.content
        FROM messages m 
        JOIN users u on m.sender_id=u.id 
        WHERE m.conversation_id = ? 
        ORDER BY m.created_at ASC

        """,(con_id,))
        row = cur.fetchall()
        return [dict(s) for s in row]
    except sql.Error as err:
        print(f"Failed to remove user: {err}")
        return []
    finally:
        con.close()

def mark_message_as_read(message_ids,user_id):

    if not message_ids:  #for new group or there is no message
        return True
    con=None
    con=sql.connect(DB_PATH)
    cur=con.cursor()
    try:
        msg_ids=[(message_id,user_id,) for message_id in message_ids ]
        cur.executemany("""

        INSERT OR IGNORE INTO message_receipts(message_id,user_id) 
        VALUES(?, ?)

        """,msg_ids)
        con.commit()
        return cur.rowcount >= 0
    
    except sql.Error as err:
        if con:
            con.rollback()
        print(f"Failed insert data: {err}")
        return False
    finally:
        if con:
            con.close()

def is_ban(func):
    @wraps(func)
    def wrapper(*args,**kwargs):

        user_id=request.current_user.get('user_id')
        conversation_id=kwargs.get('conversation_id')
        if not conversation_id and not user_id:
            return jsonify({"Error": "Missing conversation or user context"}), 400

        con=sql.connect(DB_PATH)
        cur=con.cursor()
        try:
            cur.execute("""
            
            SELECT * FROM conversation_members 
            WHERE role = 'banned'
            AND user_id = ? 
            AND conversation_id = ?

            """,(user_id,conversation_id))

            ban_user=cur.fetchone() is not None
        except sql.Error as err:
            print(f"Auth check failed: {err}")
            return jsonify({"Error": "Database authorization check failed"}), 500 
        finally:
            con.close()
        if ban_user:
            return jsonify({"Error": "Forbidden: You are banned from this chat"}), 403
        return func(*args,**kwargs)
    return wrapper


def add_users_to_pending_registrations(email,username,password_hash,otp_code,expires_at):
    con = None
    con=sql.connect(DB_PATH)
    cur=con.cursor()
    try:   
        cur.execute("""INSERT INTO pending_registrations(email,username,password_hash,otp_code,expires_at) 
        VALUES(?,?,?,?,?)
        ON CONFLICT(email) DO UPDATE SET
        username = excluded.username,
        password_hash = excluded.password_hash,
        otp_code = excluded.otp_code,
        expires_at = excluded.expires_at,
        created_at = CURRENT_TIMESTAMP""",(email,username,password_hash,otp_code,expires_at,))
        con.commit()
        return True
    except sql.Error as err:
        if con:
            con.rollback()
        print(f"Pending registration DB error: {err}")
        return False
    finally:
        if con:
            con.close()


def get_pending_user(email,otp):

    #return format
    #{'id': 1, 'email': 'test@email.com', 'username': 'testveruser', 'password_hash': 'passme12', 'otp_code': '564236', 'created_at': '2026-09-15 08:13:01', 'expires_at': '2026-09-15 09:50:43'}


    con=sql.connect(DB_PATH)
    con.row_factory=sql.Row
    cur=con.cursor()
    try:
        cur.execute("""
        SELECT * FROM pending_registrations
        WHERE email = ? 
        AND otp_code = ?
        AND expires_at > CURRENT_TIMESTAMP
        """,(email,otp,))
        verified_user=cur.fetchone()  

        return verified_user
    
    except sql.Error as err:
        print(f"Auth check failed: {err}")
        return jsonify({"Error": "Database authorization check failed"}), 500 
    finally:
        con.close()


def promote_pending_users_to_users_table(pending_data):
    email=pending_data['email']
    username=pending_data['username']
    password=pending_data['password_hash']
    result=create_users(email,username,password)
    if "error" in result:
        return result
    con=None
    try:
        con=sql.connect(DB_PATH)
        cur=con.cursor()
        cur.execute("""
        DELETE FROM pending_registrations 
        WHERE email = ? 
        """,(email,))

        con.commit()

        return {"success": f"Account verified and created for {result['username']}","id": result['id'],"username": result['username'],"email": result['email']}
    
    except sql.Error as err:
        if con:
            con.rollback()
        print(f"Failed to delete pending record: {err}")
        return {"success": f"User {username} created, but failed to clean pending verification"}
    finally:
        if con:
            con.close()

#------------------------------for testing-------------------------------------
def hash_password_on_db(password):
    passw=bcrypt.generate_password_hash(password)
    return passw
def update_pass_on_db(ids,password):
    con=None
    try:
        con=sql.connect(DB_PATH)
        cur=con.cursor()
        cur.execute("""
        UPDATE users set password = ? where id = ?
        """,(password,ids))
        con.commit()
    except sql.Error as err:
        print(err)
    finally:
        if con:
            con.close()
#------------------------------for testing-------------------------------------

def add_frogot_password(email,otp_code,expires_at):
    con=None
    try:
        con=sql.connect(DB_PATH)
        cur=con.cursor()
        cur.execute("""

        INSERT INTO pending_resets (email, otp_code, expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                otp_code = excluded.otp_code,
                expires_at = excluded.expires_at
        """,(email,str(otp_code),expires_at,))
        con.commit()
        return True
    except sql.Error as err:
        print(f"Database error in add_frogot_password: {err}")
        if con:
            con.rollback()
        return None
    finally:
        if con:
            con.close()

def get_forgot_pwd(email,otp_code):

    try:
        con=sql.connect(DB_PATH)
        con.row_factory=sql.Row
        cur=con.cursor()
        cur.execute("""
        SELECT * FROM pending_resets 
        WHERE email = ? 
        AND otp_code = ? 
        AND expires_at > CURRENT_TIMESTAMP
        """,(email,otp_code,))
        res=cur.fetchone()
        return res
    except sql.Error as err:
        print(err)
        return None
    finally:
        con.close()

def verify_reset(email,nw_pwd):
    con=None
    hashed_pwd=bcrypt.generate_password_hash(nw_pwd).decode('utf-8')
    try:
        con=sql.connect(DB_PATH)
        cur=con.cursor()
        cur.execute("""
        
        UPDATE users 
        SET password = ? 
        WHERE email = ?

        """,(hashed_pwd,email,))

        cur.execute("""
        DELETE FROM pending_resets 
        WHERE email = ? 
        """,(email,))
        
        con.commit()
        return True
    
    except sql.Error as err:
        if con:
            con.rollback()
        print(err)
        return None
    
    finally:
        if con:
            con.close()

def ban_group_user(conversation_id,user_id):
    con=None
    try:
        con=sql.connect(DB_PATH)
        con.row_factory=sql.Row
        cur=con.cursor()

        cur.execute("""
        
        SELECT * FROM conversation_members 
        WHERE conversation_id = ? 
        AND user_id = ?

        """,(conversation_id,user_id,))
        member=cur.fetchone()
        if not member:
            return {"success": False, "reason": "not_member"}
        if member['role'] == 'banned':
            return {"success": True, "reason": "already_banned"}
        

        cur.execute("""
        
        UPDATE conversation_members 
        SET role = 'banned' 
        WHERE conversation_id = ? 
        AND user_id = ?

        """,(conversation_id,user_id,))
        con.commit()
        return {"success": True, "reason": "banned_successfully"}
    
    except sql.Error as err:
        print(err)
        if con:
            con.rollback()
        return {"success": False, "reason": "db_error"}
    finally:
        if con:
            con.close()

def unban_group_user(conversation_id,user_id):
    con=None
    try:
        con=sql.connect(DB_PATH)
        con.row_factory=sql.Row
        cur=con.cursor()

        cur.execute("""
        
        SELECT * FROM conversation_members 
        WHERE conversation_id = ? 
        AND user_id = ?

        """,(conversation_id,user_id,))
        member=cur.fetchone()
        if not member:
            return {"success": False, "reason": "not_member"}
        if member['role'] == 'member':
            return {"success": True, "reason": "already_member"}
        

        cur.execute("""
        
        UPDATE conversation_members 
        SET role = 'member' 
        WHERE conversation_id = ? 
        AND user_id = ?

        """,(conversation_id,user_id,))
        con.commit()
        return {"success": True, "reason": "unbanned_successfully"}
  
    except sql.Error as err:
        print(err)
        if con:
            con.rollback()
        return {"success": False, "reason": "db_error"}
    finally:
        if con:
            con.close()

def leave_group(conversation_id,user_id):
    con=None
    try:
        con=sql.connect(DB_PATH)
        con.row_factory=sql.Row
        cur=con.cursor()
        cur.execute("""
        
        SELECT * FROM conversation_members 
        WHERE conversation_id = ? 
        AND user_id = ?

        """,(conversation_id,user_id,))
        role=cur.fetchone()
        if role['role'] == 'admin':
            return {"success": False,"reason":"admin"}
        cur.execute("""
        
        DELETE FROM conversation_members 
        WHERE conversation_id = ? 
        AND user_id = ? 

        """,(conversation_id,user_id,))

        con.commit()
        return {"success": True, "reason": "leaved"}
    
    except sql.Error as err:
        if con:
            con.rollback()
        print(err)
        return {"success": False, "reason": "db_error"}
    finally:
        if con:
            con.close()

def invite_user(user_id,inv_key):
    con=None
    try:
         con=sql.connect(DB_PATH)
         con.row_factory=sql.Row
         cur=con.cursor()
         cur.execute("""

         SELECT * FROM invite_links 
         WHERE link_id = ? 
         AND expires_at > CURRENT_TIMESTAMP
         
         """,(inv_key,))
         is_inv=cur.fetchone()
         #print(dict(is_inv))
         if not is_inv:
            cur.execute("""DELETE FROM invite_links WHERE expires_at < CURRENT_TIMESTAMP""")
            con.commit()
            return {"success": False,"reason":"link_expire"}
         
         
         
         cur.execute("""
         
         INSERT INTO conversation_members(conversation_id,user_id,role) 
         VALUES(?, ?, ?) 
         ON CONFLICT(conversation_id,user_id) DO UPDATE SET 
         role = excluded.role
         
         """,(is_inv['conversation_id'],user_id,'member',))
         con.commit()
         return {"success": True, "reason": "user_added"}
    except sql.Error as err:
        print(err)
        if con:
            con.rollback()
        return {"success": False,"reason": "db_error"}   
    finally:
        if con:
            con.close()

def cretae_invite(link_id,conversation_id,created_by,expires_at):
    con=None
    try:
        con=sql.connect(DB_PATH)
        con.row_factory=sql.Row
        cur=con.cursor()

        is_group=cur.execute("""
        
        SELECT * FROM conversation 
        WHERE id = ? 
        AND type ='group'

        """,(conversation_id,))
        if not is_group:
            return {"success":False,"reason":"not_group"}
        
        cur.execute("""
        
        INSERT INTO invite_links(link_id,conversation_id,created_by,expires_at) 
        VALUES(?, ?, ?, ?)
        RETURNING *
        """,(link_id,conversation_id,created_by,expires_at,))
        row_id=cur.fetchone()
        con.commit()
        
        return {"success": True, "reason": "created_invite","row":row_id}
    except sql.Error as err:
        print(err)
        if con:
            con.rollback()
    finally:
        if con:
            con.close()


if __name__ == '__main__':

    #ids=[5,7,8,13,14]
    #for i in ids:
    #    usr=fetch_user_by_id(i)
    #    hash_pass=hash_password_on_db(usr[3])
    #    update_pass_on_db(i,hash_pass)
    #    print(f'{usr[3]} saved')
    usr=invite_user(25,'5LG9erTKgFGEy7jDe5m9Rw')
    if usr == None:
        print({"error":"user not found"})
    else:
        print(usr)
