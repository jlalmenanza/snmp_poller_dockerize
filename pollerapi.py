from backend_api.app import app
import os

app.run(host='0.0.0.0',port=os.environ.get("API_PORT"))
# app.run(host='0.0.0.0',port=4001)



