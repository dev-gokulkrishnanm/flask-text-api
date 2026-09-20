import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

load_dotenv()

EXPIRY_MINUTES= '10'
#OTP_CODE='123456'
APP_NAME='TextApp'
YEAR=2026
def send_Otp(email,otp):
  OTP_CODE=otp
  sender_email = os.getenv('SMTP_MAIL_ID')
  receiver_email = email
  password = os.getenv('SMTP_MAIL_PASSWORD')  # NOT your regular password!
  smtp_server=os.getenv('SMTP_SERVER')

  # Create message
  message = MIMEMultipart("alternative")
  message["Subject"] = "ChatApp OTP for Login"
  message["From"] = sender_email
  message["To"] = receiver_email

  html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your OTP Code</title>
</head>
<body style="margin:0; padding:0; background-color:#ffffff; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color:#000000;">

  <!-- Preheader (hidden preview text) -->
  <div style="display:none; max-height:0; overflow:hidden; mso-hide:all;">
    Your verification code is {OTP_CODE}.
  </div>

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff; padding:40px 20px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:480px; text-align:left;">
          
          <!-- App Name Header -->
          <tr>
            <td style="padding-bottom:24px;">
              <h2 style="margin:0; font-size:20px; font-weight:700; color:#000000;">
                {APP_NAME}
              </h2>
            </td>
          </tr>

          <!-- Message Body -->
          <tr>
            <td style="padding-bottom:16px;">
              <p style="margin:0 0 12px 0; font-size:16px; line-height:1.5; color:#000000;">
                Hello,
              </p>
              <p style="margin:0; font-size:16px; line-height:1.5; color:#000000;">
                Your verification code is below. It will expire in {EXPIRY_MINUTES} minutes.
              </p>
            </td>
          </tr>

          <!-- OTP Display Block -->
          <tr>
            <td align="center" style="padding:28px 0;">
              <span style="font-size:42px; font-weight:800; font-family:'Courier New', Courier, monospace; letter-spacing:10px; color:#000000;">
                {OTP_CODE}
              </span>
            </td>
          </tr>

          <!-- Security Note -->
          <tr>
            <td style="padding-bottom:32px;">
              <p style="margin:0; font-size:14px; line-height:1.5; color:#000000;">
                If you did not request this code, please ignore this email. Do not share this code with anyone.
              </p>
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="border-top:1px solid #000000; padding-top:20px;">
              <p style="margin:0; font-size:12px; color:#000000;">
                © {YEAR} {APP_NAME}. All rights reserved.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""

  #message.attach(MIMEText(text, "plain"))
  message.attach(MIMEText(html, "html"))

  # Send the email
  try:
      with smtplib.SMTP_SSL(smtp_server, 465) as server:

          server.login(sender_email, password)
          server.sendmail(sender_email, receiver_email, message.as_string())
      print("Email sent successfully!")
      return True
  except Exception as e:
      print(f"Error: {e}")
      return False

if __name__=='__main__':
    res=send_Otp('gokulkrishnanmnair@gmail.com',123456)
    
    if not res:
        print('error')
    else:
        print('email sent from if name == main')