import os

import firebase_admin
from firebase_admin import credentials, firestore, messaging, storage

file = str(os.path.dirname(__file__))
fire_base_credentials = os.path.join(file, 'picam-262bc-firebase-adminsdk-u5owm-02fbae3cf2.json')


def initialize_firebase():
    cred = credentials.Certificate(fire_base_credentials)
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'picam-262bc.appspot.com'  # Replace with your Firebase Storage bucket
    })


def get_firestore_ref(collection: str = None, document: str = None):
    if collection is None:
        firestore.client()
    if document is None:
        return firestore.client().collection(collection)
    return firestore.client().collection(collection).document(document)


def get_storage_blob(name: str):
    return storage.bucket().blob(name)


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

