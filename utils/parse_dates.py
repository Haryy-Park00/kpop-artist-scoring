from datetime import datetime
import re

# 날짜 추출 및 변환 함수
def parse_dates(date_string):
    # 날짜 범위 처리
    if "~" in date_string:
        start_date = date_string.split("~")[0]
    else:
        start_date = date_string
    start_date = re.sub(r" \(.*?\)", "", start_date.strip())  # 요일 제거
    return datetime.strptime(start_date, "%Y.%m.%d.")  # 문자열 -> datetime 변환