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
from datetime import datetime, timezone, timedelta
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


def verify_user_token(user_id_token):
    try:
        decoded_token = auth.verify_id_token(user_id_token)
        uid = decoded_token.get("uid")
    except auth.InvalidIdTokenError:
        return {"message": 'Invalid ID token', "status": 401}
    except Exception as e:
        return {"message": str(e), "status": 500}

    return {"message": "", "status": 200, "uid": uid, "user_data": decoded_token}


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

        token_verification_data = verify_user_token(user_id_token=user_id_token)

        if token_verification_data.get("status") != 200:
            return token_verification_data.get("message"), token_verification_data.get("status")

        request.user = token_verification_data.get("uid")
        request.user_data = token_verification_data.get("user_data")

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
        expiration_time = timedelta(hours=1)

        signed_url = blob.generate_signed_url(
            version='v4',
            expiration=expiration_time,
            method='GET'
        )
        signed_urls.append(signed_url)

    return signed_urls


def get_cams_admin(cam: str) -> str:
    cams_ref = get_firestore_ref(collection="cameras", document=cam)

    if not cams_ref.get().exists:
        return ""

    return get_firestore_ref(collection="cameras", document=cam).get().get("adminUser")


def is_new_id_valid(it_to_check: str, collection: str) -> bool:
    if get_firestore_ref(collection=collection, document=it_to_check).get().exists:
        return False
    return True


def gen_random_id(collection: str) -> str:
    while True:
        request_id = str(uuid.uuid4())
        if is_new_id_valid(request_id, collection):
            return request_id


def build_join_cam_request(uid: str, cams_name: str, options: dict, comment: str):
    """
    :param comment: text from the sender to the admin
    :param uid: user id
    :param cams_name: cams name/id
    :param options: dict or request relevant options
    :return: A dict of data about the request
    """
    # TODO: move this to utils script
    user_data = get_firestore_ref(collection="users", document=uid).get().to_dict()

    request_id = gen_random_id(collection="requests")

    return request_id, {
        "sender_id": uid,
        "sender_name": user_data.get("name", "no name"),
        "sender_email": user_data.get("email", ""),
        "sender_comment": comment,
        "camera": cams_name,
        "options": options,
        "status": "pending",
        "timestamp": datetime.now(timezone.utc)
    }


def update_request_related_users(request_id: str, request_data):
    cams_admin = get_cams_admin(request_data.get("camera"))
    if cams_admin is None:
        raise Exception("Cam is not valid")

    sender_ref = get_firestore_ref(collection="users", document=request_data.get("sender_id"))
    admins_ref = get_firestore_ref(collection="users", document=cams_admin)

    sender_ref.update({
        "myRequests": firestore.ArrayUnion([request_id])
    })

    admins_ref.update({
        "adminPendingRequests": firestore.ArrayUnion([request_id])
    })


def create_request(uid: str, cams_name: str, options: dict, comment: str):
    """
    Creates a request and saves it to the relevant locations in db
    :param comment: text from the sender to the admin
    :param uid: user id
    :param cams_name: cams name/id
    :param options: dict of relevant options for the request
    """
    # TODO: move this to utils script

    request_id, request_data = build_join_cam_request(uid=uid, cams_name=cams_name, options=options, comment=comment)

    req_ref = get_firestore_ref(collection="requests", document=request_id)
    req_ref.set(request_data)

    update_request_related_users(request_id=request_id, request_data=request_data)


def handle_request_answer(requests_id, admin_id, sender_id, camera, answer_details, options):
    requests_ref = get_firestore_ref(collection="requests", document=requests_id)
    admin_ref = get_firestore_ref(collection="users", document=admin_id)

    update_req_data = {"status": answer_details.get("verdict"), "admin_comment": answer_details.get("admin_comment"),
                       "concluded": True}
    requests_ref.update(update_req_data)

    admin_ref.update({
        "adminPendingRequests": firestore.ArrayRemove([requests_id])
    })

    if answer_details.get("verdict") == "approved":
        sender_ref = get_firestore_ref(collection="users", document=sender_id)
        cam_ref = get_firestore_ref(collection="cameras", document=camera)

        update_cam_details = {}

        if options["useAccountImages"]:
            add_new_image(sender_id, sender_ref.get().to_dict().get("images", []))

        if options["requestLiveFeed"]:
            if sender_id not in cam_ref.get().to_dict().get("usersToNotify", []):
                update_cam_details["usersToNotify"] = firestore.ArrayUnion([sender_id])

        if options["requestLiveFeed"]:
            if sender_id not in cam_ref.get().to_dict().get("videoAccess", []):
                update_cam_details["videoAccess"] = firestore.ArrayUnion([sender_id])

        cam_ref.update(update_cam_details)
        sender_ref.update({"cameras": firestore.ArrayUnion([camera])})


def handle_request_delete(request_id: str, is_admin: bool, is_concluded: bool):
    request_ref = get_firestore_ref(collection="requests", document=request_id)
    request_data = request_ref.get().to_dict()
    user_ref = get_firestore_ref(collection='users', document=request_data.get("sender_id"))
    admin_ref = get_firestore_ref(collection='users', document=get_cams_admin(request_data.get("camera")))

    if not is_concluded or is_admin:
        admin_ref.update({
            "adminPendingRequests": firestore.ArrayRemove([request_id])
        })

    if is_admin:
        return

    user_ref.update({
        "myRequests": firestore.ArrayRemove([request_id])
    })

    if not request_ref.get().to_dict().get("concluded", None):
        request_ref.delete()


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

    token_verification_data = verify_user_token(user_id_token)
    if token_verification_data.get("status") != 200:
        return token_verification_data.get("message"), token_verification_data.get("status")


@socketio.on('video_feed')
def handle_request_stream(data):
    validation_data = verify_live_feed_access(camera=data.get("cameras"), user_id_token=data.get("userIdToken"))

    if validation_data.get("status") != 200:
        disconnect()
        return validation_data.get("message", ""), validation_data.get("status")

    with frame_info_lock:
        frame_info["user_connections"].add(request.sid)
    socketio.start_background_task(gen_frames)


def verify_live_feed_access(user_id_token, camera):
    token_verification_data = verify_user_token(user_id_token)
    if token_verification_data.get("status") != 200:
        return token_verification_data

    cams_ref = get_firestore_ref(collection="cameras", document=camera)

    if not cams_ref.get().exists:
        return {"message": "camera doesn't exist", "status": 500}

    if token_verification_data.get("uid") not in cams_ref.get().to_dict().get("videoAccess"):
        return {"message": "unauthorised access", "status": 403}

    return {"message": "", "status": 200}


@socketio.on('disconnect')
def handle_disconnect():
    with frame_info_lock:
        frame_info["user_connections"].discard(request.sid)


@app.route('/api/set_token', methods=['POST'])
@verify_firebase_user_id_token
def set_user_token():
    data = request.get_json()
    token = data.get('messageToken')

    user_ref = get_firestore_ref(collection='users', document=request.user)
    if not user_ref.get().exists:
        return "unauthorised access", 403

    user_ref.update({"messageToken": token})
    return "", 200


@app.route("/api/get_account_info")
@verify_firebase_user_id_token
def get_account_info():
    user_id = request.user
    user_ref = get_firestore_ref(collection="users", document=user_id)
    images_list = []
    admin_cams = []

    user_doc = user_ref.get()

    if not user_doc.exists:
        return "unauthorised access", 403

    user_data = user_doc.to_dict()
    singed_urls = generate_signed_url(user_data.get("images"))

    if len(singed_urls) != len(user_data.get("images", [])):
        return "A problem with the images was found", 401

    for index in range(len(singed_urls)):
        images_list.append({"imagePath": user_data.get("images")[index], "url": singed_urls[index]})

    if "adminCams" in user_data:
        for cam in user_data.get("adminCams"):
            if get_cams_admin(cam) == user_id:
                admin_cams.append(cam)

    account_details = {
        'email': user_data.get('email'),
        'name': user_data.get('name', ''),
        'images': images_list,
        "cameras": user_data.get("cameras", []),
        "admin_cams": admin_cams
    }

    return jsonify(account_details), 200


@app.route('/api/edit_account_details', methods=['POST'])
@verify_firebase_user_id_token
def edit_account_details():
    name = request.form.get("name")
    images = request.files.getlist('images')
    user_id = request.user

    user_ref = get_firestore_ref(collection='users', document=user_id)
    if not user_ref.get().exists:
        return "unauthorised access", 403

    existing_name = user_ref.get().to_dict().get("name", "")

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

    for cam in user_ref.get().get("cameras"):
        add_new_image(user_id, image_paths)  # TODO: this will be specific to the cam
        if existing_name != name:
            update_name(user_id)

    return jsonify({"uploadedImages": new_images})


@app.route("/api/delete_image", methods=["DELETE"])
@verify_firebase_user_id_token
def delete_image_from_account():
    image_path = request.get_json().get('imagePath')
    user_id = request.user

    if not image_path:
        return "Missing image path to delete"

    try:
        user_ref = get_firestore_ref(collection='users', document=user_id)
        if not user_ref.get().exists:
            return "unauthorised access", 403

        user_ref.update({
            "images": firestore.ArrayRemove([image_path])
        })

        get_storage_blob(image_path).delete()

        for cam in user_ref.get().get("cameras"):
            # TODO: This will need to send a request to the cam to handles its own delete
            remove_image(user_id, [image_path])

    except Exception as e:
        print(e)
        return str(e), 500

    return "", 200


@app.route("/api/add_new_user", methods=['POST'])
@verify_firebase_user_id_token
def add_new_user():
    user_id = request.user
    user_email = request.user_data.get("email")

    user_ref = get_firestore_ref(collection='users', document=user_id)
    if user_ref.get().exists:
        return "User with this email already exists", 500

    user_ref.set({"email": user_email, "name": "", "cameras": [], "images": []}, merge=True)

    return "", 200


@app.route("/api/admin_request_answer", methods=["POST"])
@verify_firebase_user_id_token
def admin_request_answer():
    requests_data = request.get_json()
    admin_id = request.user
    cams_name = requests_data.get("camera")
    sender_id = requests_data.get("sender_id")
    requests_id = requests_data.get("request_id")
    options = requests_data.get("options")
    answer = requests_data.get("answer")

    user_ref = get_firestore_ref(collection='users', document=admin_id)
    cams_ref = get_firestore_ref(collection="cameras", document=cams_name)
    requests_ref = get_firestore_ref(collection="requests", document=requests_id)

    if not user_ref.get().exists:
        return "unauthorised access", 403

    if not cams_ref.get().exists:
        return "cam not found", 500

    if not requests_ref.get().exists:
        return "requests not found", 500

    if get_cams_admin(cams_name) != admin_id:
        return "unauthorised access", 403

    handle_request_answer(requests_id=requests_id, admin_id=admin_id, sender_id=sender_id, camera=cams_name,
                          answer_details=answer, options=options)

    return "", 200


@app.route("/api/join_cam_request", methods=['POST'])
@verify_firebase_user_id_token
def join_cam_request():
    requests_data = request.get_json()
    request_options = requests_data.get("options")
    cams_name = requests_data.get("camera")
    comment = requests_data.get("sender_comment")
    user_id = request.user

    user_ref = get_firestore_ref(collection='users', document=user_id)
    cams_ref = get_firestore_ref(collection="cameras", document=cams_name)

    if not user_ref.get().exists:
        return "unauthorised access", 403

    if not cams_ref.get().exists:
        return "cam not found", 500

    if not user_ref.get().to_dict().get("name", None):
        return "user must have a name", 500

    if user_id == get_cams_admin(cams_name):
        return "403", "Can't create a request to your own camera"

    create_request(uid=user_id, cams_name=cams_name, options=request_options, comment=comment)

    return "", 200


def get_requests(field_name: str, user_data: dict):
    request_ids = user_data.get(field_name, [])
    requests = []

    for req_id in request_ids:
        request_data = get_firestore_ref(collection="requests", document=req_id).get().get('')
        request_data["request_id"] = req_id
        requests.append(request_data)

    return requests


@app.route("/api/get_my_requests", methods=['GET'])
@verify_firebase_user_id_token
def get_my_requests():
    user_id = request.user

    user_ref = get_firestore_ref(collection='users', document=user_id)
    if not user_ref.get().exists:
        return "unauthorised access", 403

    user_data = user_ref.get().to_dict()

    return get_requests(user_data=user_data, field_name="myRequests"), 200


@app.route("/api/get_cam_requests", methods=['GET'])
@verify_firebase_user_id_token
def get_cam_requests():
    admin_id = request.user
    user_ref = get_firestore_ref(collection='users', document=admin_id)

    if not user_ref.get().exists:
        return "unauthorised access", 403

    user_data = user_ref.get().to_dict()

    return get_requests(user_data=user_data, field_name="adminPendingRequests"), 200


@app.route("/api/delete_request", methods=['DELETE'])
@verify_firebase_user_id_token
def delete_request():
    user_id = request.user
    request_id = request.get_json().get("request_id")

    user_ref = get_firestore_ref(collection='users', document=user_id)
    request_ref = get_firestore_ref(collection="requests", document=request_id)
    is_admin = False
    is_concluded = False

    if not user_ref.get().exists:
        return "unauthorised access", 403

    if not request_ref.get().exists:
        return "request not found"

    if user_id == get_cams_admin(request_ref.get().to_dict().get("camera", "")):
        is_admin = True

    if request_ref.get().to_dict().get("sender_id", "") != user_id and not is_admin:
        return "unauthorised access", 403

    if request_ref.get().to_dict().get("concluded", None):
        is_concluded = True

    if not is_concluded and is_admin:
        return "can't delete open request", 500

    handle_request_delete(request_id=request_id, is_admin=is_admin, is_concluded=is_concluded)

    return "", 200


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
    thread = threading.Thread(target=activate_camera, args=(frame_info,), daemon=True)
    thread.start()

    while True:
        try:
            if thread is None or not thread.is_alive():
                print("restarting face rec")
                thread = threading.Thread(target=activate_camera, args=(frame_info,), daemon=True)
                thread.start()
        except Exception as e:
            print("the thread faild... ", e)
        finally:
            time.sleep(5)

def main():
    initialize_firebase()
    time.sleep(1)
    threading.Thread(target=start_face_recognition, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=3000, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
