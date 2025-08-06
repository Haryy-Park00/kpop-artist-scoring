import re

def process_event_data(event_string):
    # 기본값 설정
    organizers, supervisors = None, None
    
    # '문의' 기준으로 분리
    try:
        event_string = event_string.split('문 의')[0].strip()
    except:
        try:
            event_string = event_string.split('문의')[0].strip()
        except:
            pass
    print(event_string)
    
    # 정규식 패턴 설정
    pattern = r'\s*주\s?최\s?/\s?주\s?관\s*[:]\s*(?P<both>.*?)$|\s*주\s?최\s*[:]\s*(?P<organizers>.*?)\s*주\s?관\s*[:]\s*(?P<supervisors>.*?)$'
    match = re.search(pattern, event_string)
    
    if match:
        if match.group('both'):
            organizers = supervisors = match.group('both').strip()
        else:
            organizers = match.group('organizers').strip() if match.group('organizers') else None
            supervisors = match.group('supervisors').strip() if match.group('supervisors') else None
    
    return organizers, supervisors