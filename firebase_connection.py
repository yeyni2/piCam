import os

import firebase_admin
from firebase_admin import credentials, firestore, messaging

file = str(os.path.dirname(__file__))
fire_base_credentials = os.path.join(file, 'picam-262bc-firebase-adminsdk-u5owm-02fbae3cf2.json')


def initialize_firebase():
    cred = credentials.Certificate(fire_base_credentials)
    firebase_admin.initialize_app(cred)


def get_firestore_ref(collection: str = None, document: str = None):
    if collection is None:
        firestore.client()
    if document is None:
        return firestore.client().collection(collection)
    return firestore.client().collection(collection).document(document)


def send_message(token, message_title: str = "", message_body: str = ""):
    message = messaging.Message(
        notification=messaging.Notification(
            title=message_title,
            body=message_body,
        ),
        token=token,
    )

    try:
        response = messaging.send(message)
        print('Successfully sent message:', response)
    except Exception as e:
        print('Error sending message:', e)


# initialize_firebase()
token = "cRK_UPv_WQ3Xb0TfvUSPxS:APA91bFKb73XEQNOk3-1RCfMcJpYep3n58l-H2oxyoCErrp5a4qvqMmCTTH1WL0_O0k0B3UarOpuv37pVYnkTXS-_Ta3sVnkQ7wLqdevjE-tk80hnEyysVnD4BIgQ-bHgBT8xKpi8gaJ"
send_message(token, "test_title", "body_title")
