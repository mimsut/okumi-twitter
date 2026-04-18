#!/usr/bin/env python3
"""
오꿈이 트위터 콘텐츠 자동 생성기
매 30분마다 한국 트위터/인터넷 트렌드를 반영한 오꿈이 스타일 트윗 10개를 Discord로 전송
"""

import os
import json
import random
import requests
import anthropic
import datetime
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = (
    "https://discord.com/api/webhooks/1494971650847014913/"
    "QEfp8_ssBU4MJfQa-SWTV-ko9AtdPk3Psjpmn5Jz_FXhIz7cdb2Nopg5O5phoHQ1A6RQ"
)

# ─── 시간대별 트렌드 키워드 풀 ───────────────────────────────────────────────
TREND_POOL = {
    "아침": ["기상", "출근", "아침밥", "커피", "지각", "알람", "모닝루틴", "버스", "지하철", "졸음"],
    "점심": ["점심메뉴", "배달", "편의점", "구내식당", "회식", "다이어트", "치킨", "라면", "밥값", "카페"],
    "오후": ["업무", "졸음", "집중", "카페인", "야근예감", "퇴근",  "퇴근길", "스트레스", "미팅", "디저트"],
    "저녁": ["퇴근", "저녁", "야식", "넷플릭스", "피곤", "맥주", "치킨", "배달", "힐링", "집순이"],
    "밤": ["새벽감성", "불면증", "생각많음", "유튜브", "밤샘", "내일걱정", "폰중독", "감성", "외로움", "먹방"],
    "공통": [
        "월요일", "화요일", "수요일", "목요일", "금요일", "주말", "연휴",
        "취준", "알바", "대학생", "직장인", "주부", "사회초년생",
        "멘탈", "번아웃", "힐링", "자존감", "감정", "행복",
        "MBTI", "인싸", "아싸", "덕질", "최애", "팬심",
        "날씨", "비", "더위", "추위", "미세먼지",
        "운동", "다이어트", "헬스", "러닝",
        "연애", "썸", "이별", "짝사랑", "솔로",
        "돈없음", "적금", "저축", "재테크", "용돈",
    ],
}

OKUMI_PERSONA = """
너는 멘탈케어 앱 '오리의 꿈(Duck's Dream)'의 마스코트 오꿈이야.
귀엽고 통통한 오리 캐릭터인데, 트위터에서는 불닭볶음면·올리브영·투썸플레이스 공식 계정처럼
웃기고 공감되는 글을 쓰는 계정이야.

■ 오꿈이 트위터 문체:
- 짧고 임팩트 있음 (140자 이내)
- 일상 공감 포인트를 오리/꿈/멘탈 드립으로 연결
- 심리학·멘탈케어 내용을 진지하지 않게 유머로 풀기
- 트렌드 키워드 자연스럽게 녹이기
- 🦆 꽥 같은 오리 마무리 종종 사용
- ㅋㅋㅋ ;;; ㅇㅈ? ㄹㅇ 같은 트위터 언어 사용
- 가끔 진지한 척하다 반전 드립
- 브랜드인데 친구 같은 느낌

■ 절대 하지 말 것:
- "오리의 꿈 앱 다운로드" 같은 직접 광고
- 지나치게 진지하거나 교훈적
- 너무 길게 쓰기
- 억지 해시태그 남발

■ 좋은 예시 스타일:
"직장인 번아웃 3단계: 1. 오늘만 참자 2. 이번 주만 3. 이번 달만... 오꿈이는 4단계부터 봄 꽥"
"치킨 먹으면서 다이어트 걱정하는 거 진짜 멘탈 스포츠인데 ㅋㅋ 오꿈이도 매일 하는 경기임"
"월요일 아침 알람 끄고 5분만... 이 거짓말 몇 번째야 ㅇㅈ?"
"""


def get_time_slot() -> str:
    """현재 시간대 반환"""
    hour = datetime.datetime.now().hour
    if 6 <= hour < 10:
        return "아침"
    elif 10 <= hour < 14:
        return "점심"
    elif 14 <= hour < 18:
        return "오후"
    elif 18 <= hour < 22:
        return "저녁"
    else:
        return "밤"


def get_smart_trends() -> list[str]:
    """시간대 + 무작위 조합으로 트렌드 키워드 선택"""
    slot = get_time_slot()
    slot_keywords = TREND_POOL.get(slot, [])
    common_keywords = TREND_POOL["공통"]

    # 시간대 키워드 3~4개 + 공통 키워드 6~7개
    selected = random.sample(slot_keywords, min(4, len(slot_keywords)))
    selected += random.sample(common_keywords, min(6, len(common_keywords)))
    random.shuffle(selected)

    print(f"[트렌드] 시간대: {slot} | 키워드: {selected[:10]}")
    return selected[:10]


def try_scrape_trends() -> list[str]:
    """실시간 트렌드 스크래핑 시도 (실패 시 스마트 풀로 fallback)"""
    # 네이버 실시간 검색어 스크래핑 시도
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        # 네이버 데이터랩 JSON API
        res = requests.get(
            "https://signal.bz/news",
            headers=headers,
            timeout=8,
        )
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, "html.parser")
            items = soup.select(".trend_name")
            trends = [item.get_text(strip=True) for item in items if item.get_text(strip=True)]
            if trends:
                print(f"[트렌드] 실시간 스크래핑 성공: {trends[:10]}")
                return trends[:10]
    except Exception as e:
        print(f"[트렌드 스크래핑 실패] {e}")

    return get_smart_trends()


def generate_tweets(trends: list[str]) -> list[str]:
    """Claude API로 오꿈이 스타일 트윗 10개 생성"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.\n"
            "터미널에서 실행: export ANTHROPIC_API_KEY=sk-ant-..."
        )

    client = anthropic.Anthropic(api_key=api_key)

    now = datetime.datetime.now()
    time_slot = get_time_slot()
    trend_str = ", ".join(trends)

    prompt = f"""{OKUMI_PERSONA}

지금 시각: {now.strftime("%Y년 %m월 %d일 %H:%M")} ({time_slot}대)
오늘의 트렌드/관심 키워드: {trend_str}

위 트렌드 키워드 중 일부를 자연스럽게 녹여서 오꿈이 스타일 트윗 10개를 써줘.
모든 키워드를 다 쓸 필요 없고, 자연스럽게 어울리는 것만 골라서 써.
시간대({time_slot}대)에 어울리는 내용이면 더 좋아.

규칙:
- 각 트윗은 개행으로만 구분
- 번호, 불릿, 접두어 없이 트윗 텍스트만 반환
- 10개 정확히
- 설명·메타 텍스트 없이 트윗만"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    tweets = [line.strip() for line in raw.split("\n") if line.strip()]
    return tweets[:10]


def send_to_discord(tweets: list[str], trends: list[str]):
    """Discord 웹훅으로 트윗 초안 전송"""
    now = datetime.datetime.now().strftime("%Y.%m.%d %H:%M")
    trend_preview = " · ".join(trends[:6])

    lines = [
        f"🦆 **오꿈이 트윗 초안** `{now}`",
        f"📈 키워드: `{trend_preview}`",
        "─────────────────────────────────",
        "",
    ]
    for i, tweet in enumerate(tweets, 1):
        lines.append(f"**{i}.** {tweet}")

    lines += ["", "─────────────────────────────────", "_마음에 드는 글을 골라 트위터에 올려주세요 ✏️_"]

    full_message = "\n".join(lines)

    # Discord 2000자 제한 처리
    chunks = []
    current = ""
    for line in full_message.split("\n"):
        candidate = current + line + "\n"
        if len(candidate) > 1900:
            chunks.append(current.rstrip())
            current = line + "\n"
        else:
            current = candidate
    if current.strip():
        chunks.append(current.rstrip())

    success = True
    for chunk in chunks:
        res = requests.post(DISCORD_WEBHOOK_URL, json={"content": chunk}, timeout=10)
        if res.status_code not in (200, 204):
            print(f"[Discord 실패] {res.status_code}: {res.text}")
            success = False
        else:
            print(f"[Discord 전송 OK] {len(chunk)}자")

    return success


def main():
    print(f"\n{'='*50}")
    print(f"오꿈이 트윗 생성 시작: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    trends = try_scrape_trends()

    print("[생성] Claude로 오꿈이 스타일 트윗 생성 중...")
    tweets = generate_tweets(trends)
    print(f"[생성 완료] {len(tweets)}개 트윗")
    for i, t in enumerate(tweets, 1):
        print(f"  {i}. {t}")

    print("\n[전송] Discord 웹훅으로 전송 중...")
    send_to_discord(tweets, trends)
    print(f"\n완료! 다음 실행: 30분 후\n")


if __name__ == "__main__":
    main()
