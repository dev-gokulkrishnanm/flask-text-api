from flask import Flask,request,jsonify
from flask_bcrypt import Bcrypt
from datetime import datetime,timedelta,timezone
import database
import random
from session_handler import token_gen, verify_token
from smtp_helper import send_Otp 
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os
import secrets

load_dotenv()

app = Flask(__name__)
bcrypt=Bcrypt(app)
limiter=Limiter(get_remote_address,app=app)
FERNET_KEY=os.getenv('FERNET_KEY')
cipher=Fernet(FERNET_KEY)

REQUIRED_FIELDS = {"username":1, "email":2, "password":3}
UPDATE_REQUIRED_FIELDS=["field", "ch_value"]

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "Error": "Too many verification attempts",
        "message": f"Rate limit exceeded: {e.description}"
    }), 429


@app.route('/join',methods=['POST'])
def create_user():
    data = request.get_json(silent=True)
    missing_or_empty = []

    if not data:
        return jsonify({"error": "Invalid or missing JSON payload"}),400
    
    for f in REQUIRED_FIELDS.keys():
        val = data.get(f)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing_or_empty.append(f)

    if missing_or_empty:
        return (jsonify({"error": "Validation failed", "missing_or_empty_fields": missing_or_empty,}),400,)
    otp=random.randint(100000,999999)
    expire_at=datetime.now(timezone.utc) + timedelta(minutes=10)

    raw_password=data['password']
    hashed_password=bcrypt.generate_password_hash(raw_password).decode('utf-8')

    result=database.add_users_to_pending_registrations(data['email'],data['username'],hashed_password,otp,expire_at)
    res=send_Otp(data['email'],otp)
    if not result:
        return jsonify({"error": "Pending registration DB error"}),400
    #user=database.fetch_user_by_name(data['username'])
    #if user == None:
        #return jsonify({"Error":f"User {data['username']} not found"})
    #else:
        #token=token_gen(user[0],user[1])
        #return jsonify({"message" : f"{result['success']} Successfully","Token": token}),201
    elif res:
        return jsonify({"message":f"An OTP is sent to the email {data['email']} check your inbox"})
    
@limiter.limit('5 per minute')
@app.route('/verify',methods=['POST'])
def verify_user():
    data=request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload"}),400
    otp=data.get('otp')
    email=data.get('email')
    if not email or not otp:
        return jsonify({"Error": "Both 'email' and 'otp' are required"}), 400
    res=database.get_pending_user(email,otp)
    if not res:
        return jsonify({"Error": "Invalid or expired OTP"}), 400
    promote_users=database.promote_pending_users_to_users_table(dict(res)) #returns a dict {"success": f"Account verified and created for {result['user'][1]}","user": result}
    if not promote_users:
        return jsonify({"Error": "Failed to create user account"}), 500
    #user=database.fetch_user_by_email(email)
    print(promote_users)
    token=token_gen(promote_users['id'],promote_users['username'])
    return jsonify({"status": "success","message": "Email verified successfully. Account created!","user_id": promote_users,"Token": token}), 201

@app.route('/login',methods=['POST'])
@limiter.limit("5 per minute; 20 per hour")
def login():

    data=request.json
    
    if not data:
        return jsonify({"Error":"Empty Request Body"})
    username=data['username'].strip()
    password=data['password']
    user=database.fetch_user_by_name(username)
    if user == None or user == False:
            return jsonify({"Error":f"User {username} not found"})
    else:
        user_login=database.db_login(username,password)
        print(user_login)
        token=token_gen(user_login['id'],user_login['username'])
        return jsonify({"message" : f"{username} Login Success","Token": token}),201


@app.route('/update',methods=['POST'])
@limiter.limit("5 per minute; 20 per hour")
@verify_token
def update_user():
    user_id = request.current_user['user_id']
    data = request.get_json(silent=True)
    field=data['field'].strip()
    ch_value=data['ch_value'].strip()
    missing_or_empty = []
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload"}),400
    for f in UPDATE_REQUIRED_FIELDS:
        val = data.get(f)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing_or_empty.append(f)
    if missing_or_empty:
        return (jsonify({"error": "Validation failed", "missing_or_empty_fields": missing_or_empty,}),400,)
    elif field not in REQUIRED_FIELDS:
        return jsonify({"error": f"Invalid field '{field}'. Allowed: {list(REQUIRED_FIELDS.keys())}"}),400

    updated_user,old_user=database.update_user(user_id,field,ch_value)

    if updated_user is None:
        return jsonify({"error": "User not found or update failed"}), 404

    if updated_user == old_user:
            return jsonify({"message": "Same value, No Change applied"}), 200
    
    
    return jsonify({"Message":f"{field} changed to {ch_value}","User":updated_user[REQUIRED_FIELDS[field]]})
    

@app.route('/chats', methods=['POST'])
@verify_token
def create_chats():
    data=request.get_json(silent=True)
    current_user_id = request.current_user['user_id']
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload"}),400

    username=data.get('username')
            
    if not username or not str(username).strip():
        return jsonify({"Error":"Invalid Or Missing Username Field"})
    target_username=database.fetch_user_by_name(username)

    if not target_username:
        return jsonify({"error": "User not found"}), 404
    target_user_id=target_username[0]

    if current_user_id == target_user_id:
        return jsonify({"error": "Cannot create a private chat with yourself"}), 400
    
    existing_chat_id = database.get_existing_private_chat(current_user_id, target_user_id)
    
    if existing_chat_id:
        return jsonify({
            "message": "Conversation already exists",
            "conversation_id": existing_chat_id
        }), 200
    
    conversation_id = database.create_private_chat(current_user_id, target_user_id)

    if not conversation_id:
        return jsonify({"error": "Failed to create conversation"}), 500
            



    return jsonify({"message": "Conversation created successfully","conversation_id": conversation_id}), 201



@app.route('/chats', methods=['GET'])
@verify_token
def list_chats():
    current_user=request.current_user['user_id']
    chats_list=database.get_current_user_chats(current_user)
    return jsonify(chats_list)


@app.route('/groups',methods=['POST'])
@verify_token
def create_groups():
    data=request.get_json(silent=True)
    name=data.get('name')
    user_id = request.current_user['user_id']
    if not data:
        return jsonify({"Error":"Invalid or Missing JSON Payload"}),400
    
    elif not name:
        return jsonify({"Error":"Invalid Field"}),400
    elif name:
        grp_res,conversation_id=database.create_group(name, user_id)
        if not grp_res:
            return jsonify({"Error":"Some Thing Went Wrong Try Again Later"})
        elif grp_res:
            return jsonify({"Message":"group created","group_id":conversation_id}),200
        else:
            return jsonify({"Error":"Internal Server Error"}),403



@app.route('/groups/<int:conversation_id>',methods=['DELETE'])
@verify_token
@database.is_group_admin
def delete_group(conversation_id):

    delete,res=database.delete_group(conversation_id)
    if delete:
        return jsonify({"Message":f"groud ID {res} deleted "})
        


@app.route('/groups/<int:conversation_id>/members',methods=['POST'])
@verify_token
@database.is_group_admin
def add_users_group(conversation_id):
    current_user_id = request.current_user['user_id']
    data=request.get_json(silent=True)
    if not data:
            return jsonify({"Error":"Invalid or Missing JSON Payload"}),400
    
    members_list=data.get('members')
    
    if not isinstance(members_list,list) or not members_list:
        return jsonify({"Error":"Invalid or Missing Members"}),400
    elif members_list and isinstance(members_list,list):
        res=database.add_users_group(conversation_id,members_list)
        if not res:
            return jsonify({"Error": "Something Went Wrong User Not Created"}),400
        elif res:
            return jsonify({"Message":f"Users added to group ID {conversation_id}"}),200
        else:
            return jsonify({"Error":"Internal Server Error"}),403



@app.route('/groups/<int:conversation_id>/kickout',methods=['POST'])
@verify_token
@database.is_group_admin
def kickout_users_group(conversation_id):
    data=request.get_json(silent=True)
    if not data:
        return jsonify({"Error":"Invalid or Missing JSON Payload"}),400
    kickout_id=data.get('kickout_id')
    res,row=database.kickout_user(conversation_id,kickout_id)
    if res:
        return jsonify({"Message": f"User {row} is Kickedout"}),200
    else:
        return jsonify({"Error":"Internal Server Error"}),403

    
        
@app.route('/groups/<int:conversation_id>/members',methods=['GET'])
@verify_token 
def get_group_member_list(conversation_id):

    user_id = request.current_user['user_id']
    mem_list=database.get_group_list_by_id(conversation_id,user_id)
    
    if not mem_list:
        return jsonify({"Error":"Group Not Found"}),401
    elif mem_list:
        return jsonify({"Message": mem_list}),200
    else:
        return jsonify({"Error":"Internal Server Error"}),403
    

@app.route('/message/<int:conversation_id>/<string:username>',methods=['POST'])
@verify_token
@database.is_ban
def send_message(conversation_id,username):
    data=request.get_json(silent=True)
    if not data:
        return jsonify({"Error":"Invalid or Missing JSON Payload"}),400
    current_user=request.current_user['user_id']
    message=data.get('message')
    enc_message=cipher.encrypt(message.encode('utf-8')).decode('utf-8')
    success=database.send_message(conversation_id,current_user,enc_message)
    if not message or not str(data['message']).strip():
        return jsonify({"error": "'message' field is required and cannot be empty"}), 400
    
    elif success:
        return jsonify({"Message":f"Message send to {username}"}),200
    
    else:
        return jsonify({"Error":"Failed To Save Message to DB"}),500

    
@app.route('/message/<int:conversation_id>/<string:username>',methods=['GET'])
@verify_token
@database.is_conversation_member
def get_message(conversation_id,username):

    current_user=request.current_user['user_id']

    msg_res=database.get_messages(conversation_id)
    msg_ids=[]
   # print(f"message res: {msg_res}")

    if msg_res is not None:

        msg_ids = [s['message_id'] for s in msg_res if s['sender_id'] != current_user] #exclude current_user 

        msg_read=database.mark_message_as_read(msg_ids,current_user)
        #print(f"message read {msg_read}")
        for s in msg_res:
            s['content'] =cipher.decrypt(s['content'].encode('utf-8')).decode('utf-8')
        if not msg_read:
            return jsonify({"Error":"receipt failed !"}),500
        elif msg_read:
            return jsonify({"Message": "Read","conversation_id": conversation_id,"messages": msg_res}),200
    
    else:
        return jsonify({"Error": f"Failed to retrieve messages from {username}"}), 500

@app.route('/forgot-pwd',methods=['POST'])
@limiter.limit('5 per minute')
def forgot_password():
    data=request.get_json(silent=True)
    if not data:
        return jsonify({"Error":"Invalid or Missing JSON Payload"}),400
    elif not data['email']:
        return jsonify({"error": "'email' field is required and cannot be empty"}), 400
    
    email=data['email']
    result=database.fetch_user_by_email(email)
    expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    if not email:
        return jsonify({"error": "'email' field is required and cannot be empty"}), 400
    
    elif not result:
        return jsonify({"error":"no user associated with this email"}),400

    otp=random.randint(100000,999999)
    res_fp=database.add_frogot_password(email,otp,expires_at)
    if not res_fp:
        return jsonify({"error": "Failed to process password reset. Please try again."}), 500
    res_em=send_Otp(email,otp)

    if not res_em:
        return jsonify({"error": "Failed to send OTP email. Please try again later."}), 500
    return jsonify({"message":f"An OTP is sent to the email {data['email']} check your inbox"}),201
    
@app.route('/verify-reset',methods={'POST'})
@limiter.limit('5 per minute')
def verify_reset():
    data=request.get_json(silent=True)

    if not data:
        return jsonify({"Error":"Invalid or Missing JSON Payload"}),400
    if not data['email'] or not data['otp'] or not data['nw_password']:
        return jsonify({"error":"missing fields"}),400
    
    email=data['email']
    pwd=data['nw_password']
    otp=data['otp']
    result_reset=database.get_forgot_pwd(email,otp)
    #username_res=database.fetch_user_by_email(email)
    if not result_reset:
        return jsonify({"error": "Invalid or expired OTP"}), 400

    success=database.verify_reset(email,pwd)
    #if username_res:
        #username=username_res[1]
    if not success:
        return jsonify({"error": "Failed to update password. Please try again."}), 500
        
    elif success:
        return jsonify({"status":"success","message":"Password updated successfully"}),201
    else:
        return jsonify({"error":"something went wrong please try again after some time"}),500

@app.route('/groups/<int:conversation_id>/ban',methods=['POST'])
@verify_token
@limiter.limit('5 per minute')
@database.is_group_admin
def ban_group_member(conversation_id):
    current_user=request.current_user['user_id']
    data=request.get_json(silent=True)
    
    if not data:
        return jsonify({"Error":"Invalid or Missing JSON Payload"}),400

    target_user_id = data.get('target_user_id')
    if not target_user_id:
        return jsonify({"error": "'target_user_id' is required"}), 400
    if current_user == target_user_id:
        return jsonify({"error": "You cannot ban yourself"}), 400
    
    ban_res=database.ban_group_user(conversation_id,target_user_id)
    #print(ban_res)

    if ban_res["reason"] == "not_member":
        return jsonify({"error": "Target user is not a member of this conversation"}), 440
    elif ban_res["reason"] == "already_banned":
        return jsonify({"message": "User is already banned from this conversation"}), 200
    elif ban_res["reason"] == "banned_successfully":
        return jsonify({"message": "User banned successfully"}), 200
    else:
        return jsonify({"error": "Failed to process ban request"}), 500
    
@app.route('/groups/<int:conversation_id>/unban',methods=['POST'])
@verify_token
@limiter.limit('5 per minute')
@database.is_group_admin
def unban_group_member(conversation_id):
    current_user=request.current_user['user_id']
    data=request.get_json(silent=True)
        
    if not data:
        return jsonify({"Error":"Invalid or Missing JSON Payload"}),400
    
    target_user_id = data.get('target_user_id')
    if not target_user_id:
        return jsonify({"error": "'target_user_id' is required"}), 400
    if current_user == target_user_id:
        return jsonify({"error": "You cannot ban yourself"}), 400
        
    unban_res=database.unban_group_user(conversation_id,target_user_id)
    #print(ban_res)
    
    if unban_res["reason"] == "not_member":
        return jsonify({"error": "Target user is not a member of this conversation"}), 440
    elif unban_res["reason"] == "already_member":
        return jsonify({"message": "User is already a member from this conversation"}), 200
    elif unban_res["reason"] == "unbanned_successfully":
        return jsonify({"message": "User unbanned successfully"}), 200
    else:
        return jsonify({"error": "Failed to process ban request"}), 500


@app.route('/groups/<int:conversation_id>/leave',methods=['POST'])
@verify_token
@database.is_conversation_member
def leave_group(conversation_id):
    current_user=request.current_user['user_id']
    leave_res=database.leave_group(conversation_id,current_user)
    #print(leave_res)
    if leave_res["reason"] == "admin":
        return jsonify({"error": "group admin cannot leave"}), 440
    elif leave_res["reason"] == "leaved":
         return jsonify({"message": "group leaved successfully"}), 200
    else:
        return jsonify({"error": "Failed to process ban request"}), 500


@app.route('/invite/<string:inv_key>', methods=['POST'])
@verify_token
def invite_user(inv_key):
    current_user=request.current_user['user_id']
    res_inv=database.invite_user(current_user,inv_key)
    print(res_inv)
    if not res_inv:
        return jsonify({"error": "invlid request"}),400
    elif res_inv['reason'] == "link_expire":
        return jsonify({"message":"link expired or invalid link"}),400
    elif res_inv['reason'] == "user_added":     
        return jsonify({"success": "user added"}),200
    else:
        return jsonify({"error": "failed to process your request"}),500


@app.route('/create-invite/<int:conversation_id>',methods=['POST'])   
@verify_token
@database.is_group_admin
def create_invite(conversation_id):
    link_id=secrets.token_urlsafe(16)
    current_user=request.current_user['user_id']
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=60)
    res_crinv=database.cretae_invite(link_id,conversation_id,current_user,expires_at)
    print(res_crinv)
    if not res_crinv:
        return jsonify({"error":"invalid request"}),400
    elif res_crinv["reason"] == "not_group":
            return jsonify({"error": "Cannot create invite links for direct/private chats"}),403
    elif res_crinv["reason"] == "created_invite":
        return jsonify({"success": "invite link created successfully ", "link_id": res_crinv["row"]['link_id']}),200
    else:
        return jsonify({"error": "failed to process your request"}),500

if __name__ == "__main__":
    app.run(debug=True)
        
