import os
import logging
import base64
import uuid
import datetime

from firebase_connection import get_firestore_ref, initialize_firebase, get_storage_blob
from flask import Flask, request, send_from_directory, jsonify
from flask_socketio import SocketIO, disconnect
from firebase_admin import auth, firestore
from facial_req import activate_camera
from typing import List, Tuple, Dict, Any
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


@app.route('/api/edit_account_details', methods=['POST'])
@verify_firebase_user_id_token
def edit_account_details():
    # TODO: should he be able to change his name? if so it should update in all the cams hes in.x
    name = request.form.get("name")
    images = request.files.getlist('images')
    user_id = request.user.get('uid')

    user_ref = get_firestore_ref(collection='users', document=user_id)
    if not user_ref.get().exists:
        return "unauthorised access", 500

    new_images = upload_images(images, user_id)

    user_ref.set({
        'images': firestore.ArrayUnion([image_path[0] for image_path in new_images]),
        "name": name
    }, merge=True)

    return jsonify({"uploadedImages": new_images})


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
    except Exception as e:
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


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_vue_app(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


def main():
    initialize_firebase()
    t = threading.Thread(target=activate_camera, args=(frame_info,))
    t.daemon = True
    t.start()
    socketio.run(app, host='0.0.0.0', port=3000, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
