# ChatApp API

A Flask-based chat backend with direct messages, group chats, invite links, read receipts, and OTP-based email verification. Data is stored in SQLite and messages are encrypted at rest with Fernet.

## Features

- **Accounts** – Register with username/email/password, verify by email OTP, and reset forgotten passwords via OTP.
- **Authentication** – JWT bearer tokens (2-hour expiry) guard every protected route.
- **Direct messages** – Create 1-to-1 conversations and exchange encrypted messages.
- **Group chats** – Create groups, add/remove members, ban/unban, leave, and manage admins.
- **Invite links** – Generate shareable links (60-minute expiry) to join a group.
- **Read receipts** – Per-message read tracking that powers single/double tick UI states.
- **Rate limiting** – Login, verification, and password flows are limited per client IP.

## Tech Stack

- Python / Flask
- SQLite (`sqlite3`)
- `flask_bcrypt` for password hashing
- `PyJWT` for tokens
- `cryptography` (Fernet) for message encryption
- `flask_limiter` for rate limiting
- SMTP (SSL) + `python-dotenv`

## Project Structure

```
app/
├── main.py              # Entry point: ensures DB exists, starts the server
├── routs.py             # All Flask routes and app setup
├── database.py          # SQLite data access + auth/authorization decorators
├── session_handler.py   # JWT token generation and verification
├── smtp_helper.py       # OTP email sending (HTML template)
├── sql_init.py          # Database schema creation
├── requirements.txt     # Python dependencies
├── Instance/
│   └── chat_app.db      # SQLite database (created on first run)
└── .env                 # Environment configuration (not committed)
```

## Setup

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   > The app also imports `PyJWT`, `cryptography`, `python-dotenv`, and `flask_limiter` (with its storage backend). Install them if they are not already present.

2. **Create a `.env` file** in the project root:

   ```env
   SECRET_KEY=your_jwt_secret
   FERNET_KEY=your_fernet_key
   SMTP_MAIL_ID=you@example.com 
   SMTP_MAIL_PASSWORD=your_app_password
   SMTP_SERVER=smtp.example.com (Default Gmail)
   ```

   Generate a Fernet key with:

   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

3. **Run the server**

   ```bash
   python main.py
   ```

   On first run, `Instance/chat_app.db` is created and the schema is initialized. The server listens on `http://127.0.0.1:5000`.

## Authentication

Protected routes require a JWT in the `Authorization` header:

```
Authorization: Bearer ${TOKEN}
```

Obtain a token from `/verify` (after registration) or `/login`. Tokens expire after 120 minutes.

## API Reference

All examples assume the server is running at `http://127.0.0.1:5000`.

### Accounts

**Create an account**

```bash
curl -X POST http://127.0.0.1:5000/join -H "Content-Type: application/json" -d '{"username":"haxejustin","email":"haxejustin@gmail.com", "password":"passme12"}'
```

**Verify an account**

```bash
curl -X POST http://127.0.0.1:5000/verify -H "Content-Type: application/json" -d '{"email":"haxejustin@gmail.com", "otp":"331642"}'
```

**Login**

```bash
curl -X POST http://127.0.0.1:5000/login   -H "Content-Type: application/json"   -d '{"username":"gouthami","password":"dragonlady"}'
```

**Update a user record (logged in)**

```bash
curl -X POST http://127.0.0.1:5000/update   -H "Content-Type: application/json" -H "Authorization: Bearer ${TOKEN}"  -d '{"field":"username","ch_value":"testuser12"}'
```

### Forgot Password

**Request a reset OTP**

```bash
curl -X POST http://127.0.0.1:5000/forgot-pwd -H "Content-Type: application/json" -d '{"email":"haxejustin@gmail.com"}'
```

**Verify reset request and set a new password**

```bash
curl -X POST http://127.0.0.1:5000/verify-reset -H "Content-Type: application/json" -d '{"email":"frank@email.com", "otp":"123456","nw_password":"frakpass"}'
```

### Direct Chats

**Create a chat with a username**

```bash
curl -X POST http://127.0.0.1:5000/chats -H "Content-Type: Application/json" -H "Authorization: Bearer ${TOKEN}" -d '{"username":"gokul"}'
```

**Get the list of conversations**

```bash
curl -X GET http://127.0.0.1:5000/chats -H "Content-Type: Application/json" -H "Authorization: Bearer ${TOKEN}"
```

### Messages

**Send a message** (content is encrypted before storage)

```bash
curl -X POST http://127.0.0.1:5000/message/15/gokul -H "Content-Type: application/json" -H "Authorization: Bearer ${TOKEN}" -d '{"message":"encrypted message"}'
```

**Get messages** (marks incoming messages as read and returns decrypted content)

```bash
curl -X GET http://127.0.0.1:5000/message/11/testgroup -H "Content-Type: application/json" -H "Authorization: Bearer ${TOKEN}"
```

### Groups

**Create a group**

```bash
curl -X POST http://127.0.0.1:5000/groups   -H "Content-Type: application/json" -H "Authorization: Bearer ${TOKEN}"  -d '{"name":"testgroup"}'
```

**Add users to a group**

```bash
curl -X POST http://127.0.0.1:5000/groups/11/members   -H "Content-Type: application/json" -H "Authorization: Bearer ${TOKEN}"  -d '{"members":[9, 7, 8 ]}'
```

**Get group member list**

```bash
curl -X GET http://127.0.0.1:5000/groups/11/members   -H "Content-Type: application/json" -H "Authorization: Bearer ${TOKEN}"
```

**Kick out a user**

```bash
curl -X POST http://127.0.0.1:5000/groups/12/kickout -H "Content-Type: application/json" -H "Authorization: Bearer ${TOKEN}" -d '{"kickout_id":9}'
```

**Ban a user from a group**

```bash
curl -X POST http://127.0.0.1:5000/groups/11/ban -H "Content-Type: application/json" -H "Authorization: Bearer ${TOKEN}" -d '{"target_user_id": 7}'
```

**Unban a user from a group**

```bash
curl -X POST http://127.0.0.1:5000/groups/11/unban -H "Content-Type: application/json" -H "Authorization: Bearer ${TOKEN}" -d '{"target_user_id": 7}'
```

**Leave a group**

```bash
curl -X POST http://127.0.0.1:5000/groups/11/leave -H "Content-Type: application/json" -H "Authorization: Bearer ${TOKEN}"
```

**Delete a group** (admin only)

```bash
curl -X DELETE http://127.0.0.1:5000/groups/12   -H "Content-Type: application/json" -H "Authorization: Bearer ${TOKEN}"
```

### Invite Links

**Create a group invite link** (admin only)

```bash
curl -X POST http://127.0.0.1:5000/create-invite/11 -H "Content-Type: application/json" -H "Authorization: Bearer ${TOKEN}"
```

**Join via an invite link**

```bash
curl -X POST http://127.0.0.1:5000/invite/5LG9erTKgFGEy7jDe5m9Rw -H "Content-Type: application/json" -H "Authorization: Bearer ${TOKEN}"
```

## Read Receipts (Frontend Guide)

The backend records a row in `message_receipts` for every message a user reads. The frontend maps the computed `read_count` to UI ticks:

| Condition | Meaning | UI Representation |
| --- | --- | --- |
| `read_count == 0` | Sent, but no recipients have opened it | Single Gray Tick (✓) |
| `read_count > 0` AND `read_count < total_recipients` | At least one person saw it (group chat) | Double Gray Ticks (✓✓) |
| `read_count == total_recipients` | Everyone in the group (or partner in DM) read it | Double Blue Ticks (✓✓) |

## Database Schema

Tables created by `sql_init.py`:

- **users** – `id`, `username`, `email`, `password`, `created_at`, `deleted_at`
- **conversation** – `id`, `type` (`private`/`group`), `name`, `created_at`
- **conversation_members** – `conversation_id`, `user_id`, `role` (`admin`/`member`/`banned`), `joined_at`
- **messages** – `id`, `conversation_id`, `sender_id`, `content`, `created_at`
- **message_receipts** – `message_id`, `user_id`, `read_at`
- **pending_registrations** – `email`, `username`, `password_hash`, `otp_code`, `created_at`, `expires_at`
- **pending_resets** – password reset OTPs
- **invite_links** – `link_id`, `conversation_id`, `created_by`, `expires_at`


> Passwords shown above are illustrative only. In practice, passwords are stored as bcrypt hashes via `flask_bcrypt`.

## Security Notes

- Passwords are hashed with bcrypt before storage.
- Message content is encrypted with Fernet before being written to the database and decrypted on read.
- JWT tokens are signed with `HS256` and expire after 120 minutes.
- Rate limits: `5 per minute` on verification/reset/ban/unban routes and `5 per minute; 20 per hour` on login/update.