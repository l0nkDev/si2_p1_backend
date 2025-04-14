from flask import Flask, request, jsonify

app = Flask(__name__)

genai = loader()

@app.route('/auth/email', methods=['POST'])
def chat():
    print(request.json)
    if not request or not 'prompt' in request.json:
        Flask.abort(400)
    #res = genai.ask(request.json["prompt"])
    cont = {"content": genai.ask(request.json["prompt"])}
    ans = {"message": cont}
    return jsonify(ans), 201

if __name__ == '__main__':
    app.run(debug=True)