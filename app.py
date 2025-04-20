from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/sensor', methods=['POST'])
def receive_data():
    data = request.get_json()
    print("Received:", data)
    return jsonify({"status": "ok"})

@app.route('/status', methods=['GET'])
def send_status():
    return jsonify({"tilt": 14.3}) 

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

