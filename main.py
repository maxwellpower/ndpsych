import os
import time
import requests

# =============== SETTINGS / ENV VARIABLES ===============
CHECK_URL = os.environ.get("CHECK_URL")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", 300))  # default 5 min
SEND_404_NOTIFICATION = os.environ.get("SEND_404_NOTIFICATION", "false").lower() in ("true", "1", "yes")

# Mailgun (for email)
MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.environ.get("MAILGUN_DOMAIN")
EMAIL_TO       = os.environ.get("EMAIL_TO")

# VoIP.ms (for SMS)
VOIPMS_API_USERNAME = os.environ.get("VOIPMS_API_USERNAME")
VOIPMS_API_PASSWORD = os.environ.get("VOIPMS_API_PASSWORD")
VOIPMS_DID_NUMBER   = os.environ.get("VOIPMS_DID_NUMBER")
SMS_DESTINATION_NUMBER = os.environ.get("SMS_DESTINATION_NUMBER")

# =============== NOTIFICATION FUNCTIONS ===============
def send_email_notification(subject, message):
    """Send an email via Mailgun if API credentials are set."""
    if not MAILGUN_API_KEY or not MAILGUN_DOMAIN:
        print("Mailgun environment variables not set. Cannot send email.")
        return

    try:
        response = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API_KEY),
            data={
                "from": f"NDPsych Status Bot <ndpsych_bot_noreply@{MAILGUN_DOMAIN}>",
                "to": [EMAIL_TO],
                "subject": subject,
                "text": message
            },
            timeout=10
        )
        if response.status_code == 200:
            print(f"Email sent successfully: {subject}")
        else:
            print(f"Failed to send email. Status code: {response.status_code}, response: {response.text}")
    except Exception as e:
        print(f"Exception while sending email: {e}")

def send_sms_voipms(message):
    """Send an SMS via VoIP.ms if API credentials are set."""
    if not all([VOIPMS_API_USERNAME, VOIPMS_API_PASSWORD, VOIPMS_DID_NUMBER, SMS_DESTINATION_NUMBER]):
        print("Missing VoIP.ms environment variables. Cannot send SMS.")
        return

    url = "https://voip.ms/api/v1/rest.php"
    params = {
        "api_username": VOIPMS_API_USERNAME,
        "api_password": VOIPMS_API_PASSWORD,
        "method": "sendSMS",
        "did": VOIPMS_DID_NUMBER,
        "dst": SMS_DESTINATION_NUMBER,
        "message": message
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success":
            print(f"SMS sent successfully: {message}")
        else:
            print(f"Failed to send SMS via VoIP.ms. Response: {data}")
    except Exception as e:
        print(f"Exception while sending SMS via VoIP.ms: {e}")

def send_both_notifications(subject, message):
    """Helper to send both email and SMS with the same info."""
    send_email_notification(subject, message)
    send_sms_voipms(message)

# =============== MAIN CHECK LOOP ===============
def main():
    print("Starting ND Psych checker...")
    print(f"Will check {CHECK_URL} every {CHECK_INTERVAL} seconds.")
    print(f"SEND_404_NOTIFICATION = {SEND_404_NOTIFICATION}")
    
    was_404 = None  # We'll store True/False once we know the state

    while True:
        try:
            # HEAD is faster if we only need the status code
            resp = requests.head(CHECK_URL, timeout=10)
            status_code = resp.status_code
        except Exception as e:
            print(f"Error fetching {CHECK_URL}: {e}")
            time.sleep(CHECK_INTERVAL)
            continue

        is_404 = (status_code == 404)
        is_200 = (status_code == 200)

        # Logging
        print(f"Status code: {status_code} ({'404' if is_404 else '200' if is_200 else 'other'})")

        # If we don't have a recorded state yet (first iteration), just set it.
        if was_404 is None:
            was_404 = is_404
            # Optionally send a 404 notification on first run if you want
            # but that might be spammy. Let's skip it by default.
        else:
            # Check for state changes
            if was_404 and is_200:
                # Page changed from 404 to 200 => Possibly open now
                msg = f"The ND Psych get-started page is now returning {status_code}. Sign-ups might be open!"
                print(msg)
                send_both_notifications("ND Psych Sign-ups Open?", msg)
                was_404 = False

            elif not was_404 and is_404:
                # Page changed from 200 to 404 => Possibly closed again
                msg = f"The ND Psych get-started page went back to 404. Sign-ups might have closed."
                print(msg)
                send_both_notifications("ND Psych Sign-ups Closed?", msg)
                was_404 = True

            # If it remains 404 and we want a test notification each time
            if is_404 and SEND_404_NOTIFICATION:
                msg = "Still 404 - ND Psych sign-ups not open yet."
                print(f"Sending 404 notification (due to SEND_404_NOTIFICATION = True).")
                send_both_notifications("ND Psych Still Closed", msg)

        # Sleep until next check
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
