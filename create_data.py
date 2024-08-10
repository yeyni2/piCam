import pickle

from firebase_admin.auth import EmailAlreadyExistsError

from firebase_connection import get_firestore_ref, initialize_firebase
from firebase_admin import auth

initialize_firebase()


def create_user(email: str, password: str):
    try:
        user = auth.create_user(email=email, password=password)
        get_firestore_ref(collection="users", document=user.uid).set({"email": email})
    except EmailAlreadyExistsError as e:
        print(e)


def create_cam(cam_name: str = "piCam", admin_email: str = None, **kwargs):
    cam_ref = get_firestore_ref(collection="cameras", document=cam_name)
    admin_uid = auth.get_user_by_email(admin_email).uid
    print(admin_uid)
    cam_ref.set({"adminUser": admin_uid, "usersToNotify": [admin_uid]})
    update_cam(**kwargs)


def update_cam(cam_name: str = "piCam", users_to_notify: list = None, **kwargs):
    data = {}
    cam_ref = get_firestore_ref(collection="cameras", document=cam_name)

    if users_to_notify is not None:
        notify_uid = []

        for user_email in set(users_to_notify):
            notify_uid.append(auth.get_user_by_email(user_email))

        admin_uid = cam_ref.get().get("adminUser")
        if admin_uid not in notify_uid:
            notify_uid.append(admin_uid)

        data["userToNotify"] = notify_uid

    if data:
        cam_ref.update(data)


if __name__ == '__main__':
    email = "liranyeyni1620@gmail.com"
    password = ""
    # create_user(email=email, password=password )
    create_cam(admin_email=email)
