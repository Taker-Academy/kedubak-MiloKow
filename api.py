import pymongo
from fastapi import FastAPI
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId
import datetime
import jwt
from bson.json_util import dumps

uri = "mongodb+srv://milokowalska:yPgtT7Owrtw51OJB@kedubak.abeyfuk.mongodb.net/?retryWrites=true&w=majority&appName=KeDuBak"


app = Flask(__name__)
CORS(app, origins="http://localhost:3000")
client = MongoClient(uri, server_api=ServerApi('1'))
db = client["Taker"]
user_db = db["User"]
post_db = db["Post"]
app.config['SECRET_KEY'] = 'milokow'

@app.route('/', methods=['GET'])
def get_items():
    items = list(user_db.find({}, {'_id': 0}))
    return jsonify(items)

@app.route('/:<item_id>', methods=['GET'])
def get_item(item_id):
    item = user_db.find_one({'id': item_id}, {'_id': 0})
    if item:
        return jsonify(item)
    else:
        return jsonify({'message': 'Item not found'}), 404

@app.route('/auth/register', methods=['POST'])
def add_item():
    data = request.json
    if not data:
        return jsonify({'ok': False, 'message': 'Mauvaise requête, paramètres manquants ou invalides.'}), 400
    data['createdAt'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data['lastUpVote'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing_user = user_db.find_one({'email': data.get('email')})
    if existing_user:
        return jsonify({'ok': False, 'message': 'Cet utilisateur existe déjà'}), 400
    new_user = {
        'createdAt': data.get('createdAt'),
        'email': data.get('email'),
        'lastUpVote': data.get('lastUpVote'),
        'firstName': data.get('firstName'),
        'lastName': data.get('lastName'),
        'password': data.get('password')
    }
    insert_user = user_db.insert_one(new_user)
    user_id = str(insert_user.inserted_id)
    token_payload = {
        'id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    token = jwt.encode(token_payload, app.config['SECRET_KEY'], algorithm='HS256')
    response_data = {
        'ok': True,
        'data': {
            'token': 'Bearer ' + token,
            'user': {
                'createdAt': new_user['createdAt'],
                'email': new_user['email'],
                'lastUpVote': new_user['lastUpVote'],
                'firstName': new_user['firstName'],
                'lastName': new_user['lastName']
            }
        }
    }
    return jsonify(response_data), 201




@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    if not data:
        return jsonify({'ok': False, 'message': 'Mauvaise requête, paramètres manquants ou invalides.'}), 400
    resultats = user_db.find(data)
    if resultats:
        user = {
            'id': resultats[0]["_id"],
            'email': resultats[0]['email'],
            'firstName': resultats[0]['firstName'],
            'lastName': resultats[0]['lastName']
        }
        user_id = str(user['id'])
        token_payload = {
            'id': user_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }
        token = jwt.encode(token_payload, app.config['SECRET_KEY'], algorithm='HS256')
        response_data = {
            'ok': True,
            'data': {
                'token': 'Bearer ' + token,
                'user': {
                    'email': user['email'],
                    'firstName': user['firstName'],
                    'lastName': user['lastName']
                }
            }
        }
        return jsonify(response_data), 200
    else:
        return jsonify({'error': 'L\'utilisateur n\'existe pas'}), 401

def decode_token(token):
    try:
        parts = token.split()
        token = parts[2]
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.InvalidTokenError:
        return None

@app.route('/user/me', methods=['GET'])
def find_user():
    if 'Authorization' not in request.headers:
        return jsonify({'error': 'Authorization manquant'}), 401
    token = request.headers['Authorization']
    if not token:
        return jsonify({'ok': False, 'message': 'Token JWT manquant'}), 401
    user_info = decode_token(token)
    if not user_info:
        return jsonify({'ok': False, 'message': 'Token JWT invalide ou expiré'}), 401
    object_id = ObjectId(user_info['id'])
    user_document = user_db.find_one({'_id': object_id})
    if user_document:
        response_data = {
            'ok': True,
            'data': {
                'user': {
                    'email': user_document['email'],
                    'firstName': user_document['firstName'],
                    'lastName': user_document['lastName']
                }
            }
        }
        return jsonify(response_data), 200
    else :
        return jsonify({'ok': False, 'message': 'Utilisateur n\'existe pas'}), 401

@app.route('/user/edit', methods=['PUT'])
def edit_profile():
    data = request.json
    if not data:
        return jsonify({'ok': False, 'message': 'Mauvaise requête, paramètres manquants ou invalides.'}), 400
    if 'Authorization' not in request.headers:
        return jsonify({'error': 'Authorization manquant'}), 401
    token = request.headers['Authorization']
    if not token:
        return jsonify({'ok': False, 'message': 'Token JWT manquant'}), 401
    user_info = decode_token(token)
    if not user_info:
        return jsonify({'ok': False, 'message': 'Token JWT invalide ou expiré'}), 401
    object_id = ObjectId(user_info['id'])
    user_document = user_db.find_one({'_id': object_id})
    if user_document:
        update_data = {}
        update_data['firstName'] = data['firstName']
        update_data['lastName'] = data['lastName']
        update_data['email'] = data['email']
        update_data['password'] = data['password']
        result = user_db.update_one({'_id': object_id}, {'$set': update_data})
        response_data = {
            'ok': True,
            'data': {
                'user': {
                    'email': update_data['email'],
                    'firstName': update_data['firstName'],
                    'lastName': update_data['lastName']
                }
            }
        }
        return jsonify(response_data), 200
    else :
        return jsonify({'ok': False, 'message': 'Utilisateur n\'existe pas'}), 401

@app.route('/user/remove', methods=['DELETE'])
def delete_profile():
    if 'Authorization' not in request.headers:
        return jsonify({'error': 'Authorization manquant'}), 401
    token = request.headers['Authorization']
    if not token:
        return jsonify({'ok': False, 'message': 'Token JWT manquant'}), 401
    user_info = decode_token(token)
    if not user_info:
        return jsonify({'ok': False, 'message': 'Token JWT invalide ou expiré'}), 401
    object_id = ObjectId(user_info['id'])
    user_document = user_db.find_one({'_id': object_id})
    if user_document:
        response_data = {
            'ok': True,
            'data': {
                'user': {
                    'email': user_document['email'],
                    'firstName': user_document['firstName'],
                    'lastName': user_document['lastName'],
                    'removed': True
                }
            }
        }
        result = user_db.delete_one({'_id': object_id})
        return jsonify(response_data), 200

##############################################################################POST#############################################################################

@app.route('/post', methods=['GET'])
def get_posts():
    items = post_db.find({}, {'_id': 0})
    list_items = list(items)
    response_data = {
        'ok': True,
        'data': list_items
    }
    return jsonify(response_data), 201

@app.route('/post', methods=['POST'])
def add_post():
    data = request.json
    if not data:
        return jsonify({'ok': False, 'message': 'Mauvaise requête, paramètres manquants ou invalides.'}), 400
    if 'Authorization' not in request.headers:
        return jsonify({'error': 'Authorization manquant'}), 401
    token = request.headers['Authorization']
    if not token:
        return jsonify({'ok': False, 'message': 'Token JWT manquant'}), 401
    user_info = decode_token(token)
    if not user_info:
        return jsonify({'ok': False, 'message': 'Token JWT invalide ou expiré'}), 401
    object_id = ObjectId(user_info['id'])
    data['createdAt'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data['lastUpVote'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_document = user_db.find_one({'_id': object_id})
    new_post = {
        'createdAt': data.get('createdAt'),
        'userId': str(object_id),
        'firstName': user_document['firstName'],
        'title': data.get('title'),
        'content': data.get('content'),
        'comments': [],
        'upVotes': []
    }
    insert_post = post_db.insert_one(new_post)
    new_id = insert_post.inserted_id
    str_new_id = str(new_id)
    response_data = {
        'ok': True,
        'data': {
            '_id': str_new_id,
            'createdAt': new_post['createdAt'],
            'userId': new_post['userId'],
            'firstName': new_post['firstName'],
            'title': new_post['title'],
            'content': new_post['content'],
            'comments': [],
            'upVotes': []
        }
    }
    return jsonify(response_data), 200

@app.route('/post/me', methods=['GET'])
def get_post_user():
    if 'Authorization' not in request.headers:
        return jsonify({'error': 'Authorization manquant'}), 401
    token = request.headers['Authorization']
    if not token:
        return jsonify({'ok': False, 'message': 'Token JWT manquant'}), 401
    user_info = decode_token(token)
    if not user_info:
        return jsonify({'ok': False, 'message': 'Token JWT invalide ou expiré'}), 401
    user_id = user_info['id']
    user_post = post_db.find({'userId': user_id})
    if user_post :
        list_post = list(user_post)
        response_data = {
            'ok': True,
            'data': list_post
        }
        return dumps(response_data), 200
    else:
        return jsonify({'ok': False, 'message': 'Post introuvable'}), 404

@app.route('/post/<id>', methods=['GET'])
def get_post_id(id):
    data = id
    if 'Authorization' not in request.headers:
        return jsonify({'error': 'Authorization manquant'}), 401
    token = request.headers['Authorization']
    if not token:
        return jsonify({'ok': False, 'message': 'Token JWT manquant'}), 401
    user_info = decode_token(token)
    if not user_info:
        return jsonify({'ok': False, 'message': 'Token JWT invalide ou expiré'}), 401
    user_id = user_info['id']
    post_id = ObjectId(data)
    user_post = post_db.find_one({'_id': post_id})
    if user_post:
        response_data = {
            'ok': True,
            'data': user_post
        }
        return dumps(response_data), 200
    else:
        return jsonify({'ok': False, 'message': 'Post introuvable'}), 404

@app.route('/post/<id>', methods=['DELETE'])
def del_post_id(id):
    data = id
    if 'Authorization' not in request.headers:
        return jsonify({'error': 'Authorization manquant'}), 401
    token = request.headers['Authorization']
    if not token:
        return jsonify({'ok': False, 'message': 'Token JWT manquant'}), 401
    user_info = decode_token(token)
    if not user_info:
        return jsonify({'ok': False, 'message': 'Token JWT invalide ou expiré'}), 401
    user_id = user_info['id']
    post_id = ObjectId(data)
    user_post = post_db.find_one({'_id': post_id})
    if user_post:
        result = post_db.delete_one({'_id': post_id})
        response_data = {
            'ok': True,
            'data': user_post
        }
        return dumps(response_data), 200

@app.route('/post/vote/<id>', methods=['POST'])
def up_vote(id):
    data = id
    if 'Authorization' not in request.headers:
        return jsonify({'error': 'Authorization manquant'}), 401
    token = request.headers['Authorization']
    if not token:
        return jsonify({'ok': False, 'message': 'Token JWT manquant'}), 401
    user_info = decode_token(token)
    if not user_info:
        return jsonify({'ok': False, 'message': 'Token JWT invalide ou expiré'}), 401
    user_id = user_info['id']
    post_id = ObjectId(data)
    user_post = post_db.find_one({'_id': post_id})
    if user_post:
        if user_id not in user_post['upVotes']:
            user_post['upVotes'].append(user_id)
            post_db.update_one({'_id': ObjectId(user_id)}, {'$set': {'upVotes': user_post['upVotes']}})
            return jsonify({'ok': True, 'message': 'post upvoted'}), 200
        else :
            return jsonify({'ok': False, 'message': 'Conflict: Vous avez déjà voté pour ce post'}), 409

if __name__ == '__main__':
    app.run(port=8080, debug=True)
