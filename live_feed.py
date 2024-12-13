import os
import logging
import base64
import time
import uuid

from firebase_connection import get_firestore_ref, initialize_firebase, get_storage_blob
from cams_known_faces import add_new_image, remove_image, update_name
from flask import Flask, request, send_from_directory, jsonify
from flask_socketio import SocketIO, disconnect
from firebase_admin import auth, firestore
from typing import List, Tuple, Dict, Any
from facial_req import activate_camera
from datetime import datetime, timezone
from flask_cors import CORS
from functools import wraps
import threading
import cv2

app = Flask(__name__, static_folder="vueapp")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

log = logging.getLogger('werkzeug')
log.disabled = True

frame_info = {"frame": "", "user_connections": set()}
frame_info_lock = threading.Lock()


def verify_firebase_user_id_token(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_id_token = (
                (request.get_json(silent=True) or {}).get('userIdToken') or
                request.form.get('userIdToken') or
                request.headers.get('Authorization') or
                request.args.get("userIdToken")
        )

        if not user_id_token:
            return "Firebase UserIdToken is missing", 401

        if user_id_token.startswith('Bearer '):
            user_id_token = user_id_token.split(' ')[1]

        try:
            decoded_token = auth.verify_id_token(user_id_token)
            request.user = decoded_token
        except auth.InvalidIdTokenError:
            return "Invalid ID token", 401
        except Exception as e:
            return "something went wrong", 500

        return func(*args, **kwargs)

    return wrapper


def upload_images(images: list, user_id: str) -> list[dict[str, str | Any]]:
    """
    Uploading images to firebase storage [(image_path, url)]
    :param images: array of images
    :param user_id: firebase user id
    :return: list of images paths in the storage and a list of new singed urls (valid for an hour)
    """
    uploaded_images = []

    for image in images:
        if image.filename == '':
            continue

        unique_filename = f"{uuid.uuid4()}.jpg"
        blob_path = f"users/{user_id}/{unique_filename}"
        blob = get_storage_blob(blob_path)
        blob.upload_from_file(image.stream, content_type=image.content_type)

        uploaded_images.append({"imagePath": blob_path, "url": generate_signed_url([blob_path])[0]})

    return uploaded_images


def generate_signed_url(image_paths: list) -> list:
    """
    :param image_paths: Array of all the image paths the user have
    :return: singed url to access the images
    """
    if image_paths is None:
        return []

    signed_urls = []
    for image_path in image_paths:
        blob = get_storage_blob(image_path)
        expiration_time = datetime.timedelta(hours=1)

        signed_url = blob.generate_signed_url(
            version='v4',
            expiration=expiration_time,
            method='GET'
        )
        signed_urls.append(signed_url)

    return signed_urls


def get_cams_admin(cam: str) -> str:
    pass


def is_new_id_valid(it_to_check: str, collection: str) -> bool:
    if get_firestore_ref(collection=collection, document=it_to_check).get().exists:
        return False
    return True


def gen_random_id(collection: str) -> str:
    while True:
        request_id = str(uuid.uuid4())
        if is_new_id_valid(request_id, collection):
            return request_id


def build_join_cam_request(uid: str, cams_name: str, options: dict):
    """
    :param uid: user id
    :param cams_name: cams name/id
    :param options: dict or request relevant options
    :return: A dict of data about the request
    """
    # TODO: move this to utils script
    request_id = gen_random_id(collection="requests")

    return request_id, {
        "sender_id": uid,
        "cam": cams_name,
        "options": options,
        "status": "pending",
        "timestamp": datetime.now(timezone.utc)
    }


def update_reqeust_related_users(request_id: str, request_data):
    cams_admin = get_cams_admin(request_data.get("cam"))
    sender_ref = get_firestore_ref(collection="users", document=request_data.get("sender_id"))
    admins_ref = get_firestore_ref(collection="users", document=cams_admin)

    # The uid that made the request will have a list of outgoing request and the admin will also have pending request
    # list so he can to make requests to other cams.


def create_request(uid: str, cams_name: str, options: dict):
    """
    Creates a request and saves it to the relevant locations in db
    :param uid: user id
    :param cams_name: cams name/id
    :param options: dict of relevant options for the request
    """
    # TODO: move this to utils script

    request_id, request_data = build_join_cam_request(uid=uid, cams_name=cams_name, options=options)

    req_ref = get_firestore_ref(collection="requests", document=request_id)
    req_ref.set(request_data)

    update_reqeust_related_users(request_id=request_id, request_data=request_data)


def gen_frames():
    while True:
        with frame_info_lock:
            if not frame_info["user_connections"]:
                break

        frame = frame_info["frame"]
        if frame is not None:
            _, buffer = cv2.imencode('.jpg', frame)
            frame = base64.b64encode(buffer).decode('utf-8')
            socketio.emit('new_frame', {'frame': frame})
            socketio.sleep(1 / frame_info["frame_rate"])


@socketio.on('connect')
def on_connect():
    user_id_token = request.args.get("userIdToken")

    try:
        auth.verify_id_token(user_id_token)
    except auth.InvalidIdTokenError:
        disconnect()
        return 'Invalid ID token', 401
    except Exception as e:
        disconnect()
        return "something went wrong", 500


@socketio.on('video_feed')
def handle_request_stream():
    with frame_info_lock:
        frame_info["user_connections"].add(request.sid)
    socketio.start_background_task(gen_frames)


@socketio.on('disconnect')
def handle_disconnect():
    with frame_info_lock:
        frame_info["user_connections"].discard(request.sid)


@app.route('/api/set_token', methods=['POST'])
@verify_firebase_user_id_token
def set_user_token():
    data = request.get_json()
    token = data.get('messageToken')

    user_ref = get_firestore_ref(collection='users', document=request.user["uid"])
    if not user_ref.get().exists:
        return "unauthorised access", 500

    user_ref.update({"messageToken": token})
    return "", 200


@app.route("/api/get_account_info")
@verify_firebase_user_id_token
def get_account_info():
    user_id = request.user.get("uid")
    user_ref = get_firestore_ref(collection="users", document=user_id)
    images_list = []

    user_doc = user_ref.get()

    if not user_doc.exists:
        return "unauthorised access", 500

    user_data = user_doc.to_dict()
    singed_urls = generate_signed_url(user_data.get("images"))

    if len(singed_urls) != len(user_data.get("images")):
        return "A problem with the images was found", 401

    for index in range(len(singed_urls)):
        images_list.append({"imagePath": user_data.get("images")[index], "url": singed_urls[index]})

    account_details = {
        'email': user_data.get('email'),
        'name': user_data.get('name'),
        'images': images_list
    }

    return jsonify(account_details), 200


@app.route('/api/edit_account_details', methods=['POST'])
@verify_firebase_user_id_token
def edit_account_details():
    name = request.form.get("name")
    images = request.files.getlist('images')
    user_id = request.user.get('uid')

    user_ref = get_firestore_ref(collection='users', document=user_id)
    if not user_ref.get().exists:
        return "unauthorised access", 500

    existing_name = user_ref.get().get("name")
    new_images = upload_images(images, user_id)
    image_paths = [image_path["imagePath"] for image_path in new_images]
    set_data = {}

    if len(image_paths) > 0:
        set_data["images"] = firestore.ArrayUnion(image_paths)

    if existing_name != name and name != "":
        set_data["name"] = name

    if len(set_data.keys()) == 0:
        return "", 200

    user_ref.set(set_data, merge=True)

    for cam in user_ref.get().get("cams"):
        add_new_image(user_id, image_paths)
        if existing_name != name:
            update_name(user_id)

    return jsonify({"uploadedImages": new_images})


@app.route("/api/delete_image", methods=["DELETE"])
@verify_firebase_user_id_token
def delete_image_from_account():
    image_path = request.get_json().get('imagePath')
    user_id = request.user.get('uid')

    if not image_path:
        return "Missing image path to delete"

    try:
        user_ref = get_firestore_ref(collection='users', document=user_id)
        if not user_ref.get().exists:
            return "unauthorised access", 500

        user_ref.update({
            "images": firestore.ArrayRemove([image_path])
        })

        get_storage_blob(image_path).delete()

        for cam in user_ref.get().get("cams"):
            # TODO: This will need to send a request to the cam to handles its own delete
            remove_image(user_id, [image_path])

    except Exception as e:
        print(e)
        return str(e), 500

    return "", 200


@app.route("/api/add_new_user", methods=['POST'])
@verify_firebase_user_id_token
def add_new_user():
    user_id = request.user['uid']
    user_email = request.user.get("email")

    user_ref = get_firestore_ref(collection='users', document=user_id)
    if user_ref.get().exists:
        return "User with this email already exists", 500

    user_ref.set({"email": user_email}, merge=True)

    return "", 200


@app.route("/api/join_cam_request", methods=['POST'])
@verify_firebase_user_id_token
def join_cam_request():
    # Firstly get the cams name, and the requests options in a dict like:
    # {"request_live_feed": True, "get_notifications": True, "allow_to_add_images": False}
    requests_data = request.get_json()
    request_options = requests_data["options"]
    cams_name = requests_data.get("name")
    user_id = request.user["uid"]

    user_ref = get_firestore_ref(collection='users', document=user_id)
    cams_ref = get_firestore_ref(collection="cams", document=cams_name)

    if not user_ref.get().exists:
        return "unauthorised access", 500

    if not cams_ref.get().exists:
        return "cam not found", 500

    # After all the data is saved and the user data is checked and validated
    # create a request in a requests collections with the user that made the request the cam and the requests options
    # Add a request creation time and status.

    # Create a requests list for and add this request (generate and id and make sure it doesnt exist)
    # The uid that made the request will have a list of outgoing request and the admin will also have pending request
    # list so he can to make requests to other cams.

    create_request(uid=user_id, cams_name=cams_name, options=request_options)

    # After all that the request will exist and the front will just show them and logic will be applied in following
    # functions


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_vue_app(path):
    """
    :param path: url path to get the frontend
    :return: files to run the website
    """
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


def start_face_recognition():
    thread = None

    while True:
        if thread is None or not thread.is_alive():
            print("restarting face rec")
            thread = threading.Thread(target=activate_camera, args=(frame_info,), daemon=True)
            thread.start()
        time.sleep(5)


def main():
    initialize_firebase()
    time.sleep(1)
    threading.Thread(target=start_face_recognition, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=3000, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
