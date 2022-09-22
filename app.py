from flask import Flask, render_template, jsonify, request, redirect
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient

import pandas as pd
from http import client

import hashlib
import jwt
from datetime import datetime, timedelta

from tkinter import messagebox

app = Flask(__name__)

client = MongoClient('localhost', 27017)  
db = client.dbweek0

# 기상청 데이터 파싱 시작-------------------------------------------
headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
html = requests.get('https://www.weather.go.kr/w/obs-climate/land/city-obs.do')

soup = BeautifulSoup(html.text, 'html.parser')

weathers = soup("table", "table-col")[0]

table_rows = weathers.find_all("tr")

table_headers=table_rows[:2] # 두번째 행 까지 헤더로 사용
table_data = table_rows[2:] # 나머지 행은 데이터

table_data_elements=[x.find_all("td") for x in table_data]

data = []
for elem in table_data_elements:
    if len(elem) > 0:
        data.append([x.text for x in elem])
df = pd.DataFrame(data) # 스크래핑 한 데이터를 데이터프레임화

temp = df.iloc[20][5]
wind_temp = df.iloc[20][7]
humidity = df.iloc[20][9]
wind_direction = df.iloc[20][10]
# 기상청 데이터 파싱 종료-----------------------------------

# 비밀키
SECRET_KEY = 'APPLE'

#메인홈
@app.route('/')
def home():
   return render_template('index.html', 
    title = '4조 기온 별 옷차림',
    temp1 = temp, 
    temp2 = wind_temp,
    temp3 = humidity,
    temp4 = wind_direction)

#회원가입
@app.route('/join')
def join():
    return render_template('signup.html')

#회원가입 api
@app.route('/api/signup', methods=['POST'])
def signUp():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']
    email_receive = request.form['email_give']
    
    if id_receive == "" or pw_receive == "" or email_receive == "":
        return jsonify({'result': 'fail', 'msg': '아이디와 비밀번호를 입력해주세요.'})

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    db.users.insert_one({'id':id_receive, 'pw':pw_hash, 'email':email_receive})
    return jsonify({'result': 'success', 'msg':'회원가입 완료!'})


# 로그인 api
@app.route('/api/login', methods=['POST'])
def login():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']  # 유저가 아이디 pw 입력
    
    print(id_receive)
    if id_receive == "" or pw_receive == "" :
        return jsonify({'result': 'fail', 'msg': '아이디와 비밀번호를 입력해주세요.'}) 


    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()  # 유저가 입력한 pw를 해쉬화

    result = db.users.find_one({'id': id_receive, 'pw': pw_hash}) 

    if result is not None:  # 일치한다면
        payload = {
            'id': id_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60*15)  # 로그인 15분 유지
        } 
        #유저 아이디와 유효기간을 담고 있는 payload 생성
       
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        # jwt기반 토큰 생성
        return jsonify({'result': 'success', 'token': token, 'msg': '로그인 성공!'}) 
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})



# main 으로 오면 쿠키에 토큰이 있는지 확인.
# mytoken(키 값)에 담겨 있는 것을 가져온다. 
@app.route('/main')
def check():
    # 쿠키에 저장된 token 받아오기
    receive_token = request.cookies.get('mytoken')

    try:
        #받은 토큰을 사용하여 디코드
        payload = jwt.decode(receive_token, SECRET_KEY, algorithms=['HS256'])
        id_receive = payload['id']
        result = db.users.find_one({'id': id_receive}) 

        if result is not None:  # 일치한다면
            return render_template('main.html',
                temp1 = temp,
                temp2 = wind_temp,
                temp3 = humidity,
                temp4 = wind_direction)
        else: 
            return redirect('/')
   	
    # token이 만료 되었을때
    except jwt.exceptions.ExpiredSignatureError:
        print('알림창', '로그인이 만료되었습니다. 다시 로그인 해주세요')
        return redirect('/')
    # token이 없을때
    except jwt.exceptions.DecodeError:
        print('알림창', '로그인 정보가 없습니다. 로그인 해주세요')
        return redirect('/')






# 연습

@app.route('/post', methods=['POST'])
def post():
    # 쿠키에 저장된 token 받아오기
    receive_token = request.cookies.get('mytoken')

    try:
        #받은 토큰을 사용하여 디코드
        payload = jwt.decode(receive_token, SECRET_KEY, algorithms=['HS256'])
        id_receive = payload['id']
        result = db.users.find_one({'id': id_receive}) 

        if result is not None:  # 일치한다면
            text_receive = request.form['text_give']
            file_insert = {'text': text_receive, 'user_id': id_receive, 'like': 0}
            db.cards.insert_one(file_insert)
            return jsonify({'result': 'success'})
        else: 
            return redirect('/')
   	
    # token이 만료 되었을때
    except jwt.exceptions.ExpiredSignatureError:
        print('알림창', '로그인이 만료되었습니다. 다시 로그인 해주세요')
        return redirect('/')
    # token이 없을때
    except jwt.exceptions.DecodeError:
        print('알림창', '로그인 정보가 없습니다. 로그인 해주세요')
        return redirect('/')


@app.route('/post', methods=['GET'])
def read_post():
    result = list(db.cards.find({}, {'_id': 0}))
    return jsonify({'result':'success', 'postings': result})


      
@app.route('/api/like', methods=['POST'])
def like_heart():
   return

    




    

# 기본포트 5000
if __name__ == '__main__':
   app.run('0.0.0.0',port=5000,debug=True)
