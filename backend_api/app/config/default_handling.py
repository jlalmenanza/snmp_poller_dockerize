from backend_api.app import app
from backend_api.app import jwt
from backend_api.app import blacklist
import requests
from flask_restful import reqparse
 
@app.before_request
def do_before_request():
    bearer_token = reqparse.RequestParser()
    bearer_token.add_argument('Authorization',location='headers')
    args = bearer_token.parse_args()
    if args['Authorization']:
        myUrl = os.environ.get("VALIDATE_API_URL")
        head = {'Authorization': args['Authorization']}
        response = requests.post(myUrl, headers=head)
        print(response.status_code)
        if (response.status_code == 200):
            pass
        else:
            return {"response": response.status_code, "message":"Unauthorized token"}, 401
                
@app.errorhandler(404)
def page_not_found(e):
    return {'message': 'Not found', 'type': '404'}, 404

@app.errorhandler(500)
def page_not_found(e):
    return {'message': 'Internal Server Error', 'type': '500'}, 500

@jwt.token_in_blacklist_loader
def check_if_token_in_blacklist(decrypted_token):
    jti = decrypted_token['jti']
    return jti in blacklist


