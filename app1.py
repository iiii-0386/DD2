#機能読み込み
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
import firebase_admin
from firebase_admin import credentials, firestore
import os

#Openaiキー参照
load_dotenv() #.envファイル読み込み
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

'''
#Firebaseキー参照
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred) #Firebase初期化
db = firestore.client() #Firestoreを操作するためのクライアント作成
'''

#Flask
app = Flask(__name__)
CORS(app, origins=["*"]) #どのポートやドメインからでもアクセス可能にする

#サーバー動作確認
@app.route("/")
def hello():
    return "Hello Flask!" #Hello Flaskと返す

@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.get_json() #フロントから送られたJSONを取得
    task = data.get("task") #予定名
    score = data.get("score") #達成度
    reason = data.get("reason") #理由

    if not task or not reason or not score: #必要項目がそろっていなければエラーを返す
        return jsonify({"error": "task, reason, scoreは必須です"}), 400

#AIに送るプロンプト作成
    prompt = f"""
    以下の予定について改善点を教えてください。
    予定: {task}
    達成度: {score}
    理由: {reason}
    具体的な改善案で返してください。
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o", #使用するモデル
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8 #回答のランダム性
        )
        advice = response.choices[0].message.content #AIによる文章を取り出す
        return jsonify({"advice": advice}) #フロントにJSON形式で返す
    except Exception as e:
        return jsonify({"error": str(e)}), 500 #エラーが発生した場合、エラーメッセージを返す

if __name__ == "__main__":
    app.run(debug=True)