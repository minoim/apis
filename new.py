#!/usr/bin/env python3

import requests
import os
from datetime import datetime, timedelta
import difflib
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 로그 파일 경로 설정
log_file = "/home/runner/work/apis/apis/news_clipping_log.txt"

# 스크립트 시작 로그 기록
with open(log_file, "a") as file:
    file.write(f"Script started at {datetime.now()}\n")

def is_similar(text1, text2, threshold=0.85):
    """ 두 텍스트 간의 유사도를 계산하고, 지정된 임계값 이상인 경우 True를 반환합니다. """
    similarity = difflib.SequenceMatcher(None, text1, text2).ratio()
    return similarity > threshold

# 네이버 API 접속을 위한 키
client_id = "OALU1nyFeIqqpOgBuhAD"       # 제공받은 클라이언트 ID
client_secret = "a2XmB4RoL_" # 제공받은 클라이언트 시크릿

# 검색할 키워드 및 카테고리 설정
keywords = {
    "주요증시/거시경제": ["연준","금리","코스피","코스닥","나스닥","특징주","물가","인플레","cpi","환원","자사주","채권","IPO"],
}

# 결과 저장을 위한 딕셔너리 및 카테고리별 본문 유사도 확인을 위한 딕셔너리 초기화
results = {category: [] for category in keywords}
seen_articles = {category: [] for category in keywords}

# 날짜 설정
current_time = datetime.now()
start_time = current_time.replace(hour=23, minute=0, second=0, microsecond=0) - timedelta(days=1)  # 전날 23시

# API URL 및 헤더 설정
url = "https://openapi.naver.com/v1/search/news.json"
headers = {
    "X-Naver-Client-Id": client_id,
    "X-Naver-Client-Secret": client_secret
}

# 세션 설정
session = requests.Session()
retry = Retry(
    total=5,  # 재시도 횟수
    read=5,
    connect=5,
    backoff_factor=0.3,  # 재시도 간격
    status_forcelist=(500, 502, 504)
)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

# 결과 저장을 위한 딕셔너리
results = {category: [] for category in keywords}

# 각 키워드에 대한 검색 및 결과 분류
for category, keys in keywords.items():
    print(f"Processing category: {category}")
    for key in keys:
        print(f"  Searching for keyword: {key}")
        params = {
            "query": key,
            "start": 1,
            "display": 100,
            "sort": "date"
        }
        try:
            response = session.get(url, headers=headers, params=params, timeout=10)
            print(f"  Response status code: {response.status_code}")
            if response.status_code == 200:
                news_data = response.json()
                for item in news_data['items']:
                    title = item['title']
                    description = item['description'][:300]
                    combined_text = title + description
                    if not any(is_similar(combined_text, seen_article, threshold=0.7) for seen_article in seen_articles[category]):
                        seen_articles[category].append(combined_text)
                        pub_date = datetime.strptime(item['pubDate'], '%a, %d %b %Y %H:%M:%S +0900')
                        if start_time <= pub_date <= current_time and key in item['title']:
                            results[category].append({
                                "제목": title,
                                "본문 미리보기": description,
                                "링크": item['link'],
                                "발행 시간": pub_date.strftime("%Y-%m-%d %H:%M:%S")
                            })
                            print(f"    Article added: {title}")
            else:
                print(f"Error: Response status code is {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            with open(log_file, "a") as file:
                file.write(f"Request error at {datetime.now()}: {e}\n")

# 각 기사를 시간 순으로 정렬
for category, items in results.items():
    results[category] = sorted(items, key=lambda x: datetime.strptime(x['발행 시간'], "%Y-%m-%d %H:%M:%S"))

# HTML 파일 생성
html_content = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>뉴스 검색 결과</title>
    <meta name="description" content="돈이 되는 오늘 주요 뉴스 요약">
    <meta name="keywords" content="오늘뉴스, 경제, 인공지능, 삼성, 반도체, 전염병, 인공지능, 로봇, 경제뉴스">
    <meta name="author" content="Apis Hive">
    <style>
        .category { font-size: 24px; font-weight: bold; margin-top: 20px; }
        .news { margin-bottom: 15px; }
        .title { font-size: 18px; }
        .preview { font-size: 14px; }
        .info { font-size: 12px; color: grey; }
        hr { border: 0; height: 1px; background-color: #333; margin-top: 5px; }
    </style>
</head>
<body>
"""
for category, items in results.items():
    html_content += f"<h1 class='category'>{category}</h1>\n"  # h1 태그 사용
    for item in items:
        html_content += "<article class='news'>\n"
        html_content += f"  <h2 class='title'><a href='{item['링크']}'>{item['제목']}</a></h2>\n"  # h2 태그 사용
        html_content += f"  <p class='preview'>{item['본문 미리보기']}...</p>\n"
        html_content += f"  <p class='info'>{item['발행 시간']}</p>\n"
        html_content += "</article>\n"
html_content += """
</body>
</html>
"""
# 현재 날짜와 시간을 포맷에 맞게 문자열로 변환
current_datetime_str = datetime.now().strftime("%Y%m%d_%H%M%S")
# HTML 파일 저장 경로 설정 (날짜와 시간 포함)
directory = "/home/runner/work/apis/apis/news_clipping"
if not os.path.exists(directory):
    os.makedirs(directory)
file_path = f"{directory}/news_results_{current_datetime_str}.html"
# HTML 파일 저장
with open(file_path, "w", encoding="utf-8") as file:
    file.write(html_content)

# 스크립트 완료 로그 기록
with open(log_file, "a") as file:
    file.write(f"Script completed at {datetime.now()}\n")
