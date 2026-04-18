#!/usr/bin/env python3
"""
오꿈이 트위터 콘텐츠 자동 생성기
API 없이 템플릿 + 트렌드 키워드 조합으로 오꿈이 스타일 트윗 생성
매 30분마다 Discord 웹훅으로 10개 전송
"""

import random
import requests
import datetime
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = (
    "https://discord.com/api/webhooks/1494971650847014913/"
    "QEfp8_ssBU4MJfQa-SWTV-ko9AtdPk3Psjpmn5Jz_FXhIz7cdb2Nopg5O5phoHQ1A6RQ"
)

# ─── 트렌드 키워드 풀 (시간대별) ───────────────────────────────────────────
TREND_POOL = {
    "아침": ["아침밥", "출근길", "지각", "알람", "커피 한 잔", "버스", "지하철", "모닝루틴", "졸음"],
    "점심": ["점심메뉴", "배달", "편의점 도시락", "구내식당", "다이어트", "치킨", "라면", "밥값 인상"],
    "오후": ["오후 3시", "업무 집중", "카페인 한계", "야근 예감", "퇴근까지 N시간", "스트레스"],
    "저녁": ["퇴근길", "야식", "넷플릭스", "오늘 수고했어", "치맥", "배달앱", "침대"],
    "밤":   ["새벽 감성", "불면증", "생각 많음", "내일 걱정", "유튜브 알고리즘", "폰 중독", "먹방"],
    "공통": [
        "월요일", "금요일", "주말", "연휴 전날", "취준", "알바", "대학생", "직장인",
        "멘탈 관리", "번아웃", "자존감", "행복", "MBTI", "덕질", "최애",
        "날씨", "비 오는 날", "운동", "다이어트 실패", "연애", "솔로", "통장 잔고",
        "카페", "공부", "시험", "발표", "회의", "마감", "점심값",
    ],
}

# ─── 오꿈이 트윗 템플릿 ────────────────────────────────────────────────────
# {K} = 트렌드 키워드, {K2} = 두 번째 키워드
# {EMO} = 감정 표현, {QUACK} = 오리 마무리

QUACKS = ["꽥", "꽥꽥", "🦆", "꽥..", "꽥?", "🦆💨", "꽥 (이건 공감 아님)", "꽥입니다"]

EMOTIONS = [
    "멘탈이 나갔어", "진짜 공감됨", "이거 실화?", "왜 이렇게 공감돼",
    "오늘도 수고했어", "괜찮아 다 그래", "이게 삶이지", "숨 한 번 쉬자",
    "존버하는 중", "버티는 중", "힐링이 필요해", "감정 과부하",
]

TEMPLATES = [
    # 공감형
    "{K} 앞에서 멘탈 터지는 사람 🦆",
    "{K} 걱정하느라 잠 못 잔 사람 손 🦆",
    "{K} 때문에 오늘 하루 다 썼다 꽥",
    "{K} 보면서 '나만 힘든 게 아니구나' 하는 오꿈이 🦆",
    "{K} 앞에선 다들 오리처럼 겉은 태연한데 발은 미친듯이 움직이는 중 ㅋㅋ",
    "{K} 스트레스는 꿈에서 풀기로 함 꽥",
    "{K} 버티는 거 그것 자체가 이미 대단한 거야 ㅇㅈ?",
    "{K} 힘든 사람 오꿈이가 꽥 하고 있을게 🦆",

    # 유머/반전형
    "{K} 걱정 3초 → 포기 → 내일의 나에게 패스 → 오늘 하루 완료 꽥",
    "{K} 때문에 멘탈 나간 사람: 저요\n{K} 극복한 사람: 아직 없음\n오꿈이: 둘 다 꽥",
    "심리학적으로 {K} 앞에서 멍때리는 건 뇌가 스스로를 보호하는 거래. (방금 지어냄) 꽥",
    "{K} 걱정하다가 딴 생각하다가 다시 {K} 걱정하다가 잠드는 루틴 ㅋㅋ",
    "오늘의 목표: {K} 그냥 잊기. 달성률: 0% 꽥",
    "{K} 해결법 3가지: 1. 잠자기 2. 밥 먹기 3. 또 잠자기 🦆",
    "{K}? 꿈에서 해결해 꽥 (실제로 이 방법 효과 없음)",
    "나는 {K}을 두 번 이겼다\n첫 번째: 꿈속에서\n두 번째: 아직 안 이김 꽥",

    # 브랜드/오리 캐릭터형
    "오꿈이가 {K} 잘 버티라고 꽥 하러 왔어 🦆",
    "오리는 물 위에서 항상 여유로워 보이잖아. {K} 앞의 우리가 딱 그 꼴임 ㅋㅋ 꽥",
    "오꿈이 오늘의 위로: {K} 힘들어도 넌 잘하고 있어. (진심임) 🦆",
    "{K} 때문에 힘들면 오꿈이한테 꽥 하면 돼. 들을게 🦆",
    "오리의 꿈이 뭔지 알아? {K} 없는 하루. 근데 꿈이라 아직 못 이뤄씀 꽥",

    # 시간대 공감형
    "오늘 {K} 어떻게 버텼어? 잘했다 진짜 꽥 🦆",
    "{K} 끝나고 집 가는 길이 제일 좋은 순간 아님? 꽥",
    "{K} 앞에서 버티는 거 보면 인간이 진짜 대단한 동물임. 오리는 그냥 꽥만 함",
    "오늘 {K} 때문에 힘들었지? 자기 전에 잘 자라고 꽥 해줌 🦆",
    "{K} 내일 생각하기로 하고 일단 지금 이 순간만 꽥 🦆",

    # MZ/트위터 감성형
    "{K} ㄹㅇ 공감되면 좋아요 한 번만 꽥",
    "{K} 앞에서 ㅇㅈㄹ 하는 사람 vs 그냥 꽥 하는 사람 나는 후자",
    "{K} 겪고 있는 사람 여기 있어? 오꿈이도 있어 꽥",
    "{K} 힘들다고 티 내도 되는데 다들 왜 괜찮은 척 하는지 ;;; 꽥",
    "솔직히 {K} 앞에서 '나 괜찮아'는 99% 거짓말임 ㅋㅋ 꽥",

    # 두 키워드 조합형
    "{K} 하면서 {K2} 걱정하는 멀티태스킹 고수들 🦆",
    "{K} 때문에 힘들다가 {K2} 보고 현실 직면하는 순서 ㅋㅋ 꽥",
    "{K}도 버텼는데 {K2}도 버텨. 오꿈이 믿어 꽥 🦆",
    "오늘의 난이도: {K} ★★★☆☆ / {K2} ★★★★★ 꽥",

    # 철학 드립형
    "꿈에서는 {K} 없어. 그래서 꿈이 꿈인 거지 꽥",
    "{K} 앞에서 멍때리는 시간도 필요해. 뇌가 쉬는 거거든. (오꿈이 심리학) 🦆",
    "오리는 {K} 신경 안 써. 왜냐면 꽥만 하면 되거든. 인간이 더 복잡함 꽥",
    "{K} 걱정하다 보면 어느새 해결돼 있는 경우가... 없지는 않음. 있을 수도 있음. 꽥",
    "멘탈이 중요한 이유: {K} 앞에서 무너지면 아무것도 못 하거든. 오꿈이가 챙겨줄게 🦆",

    # 요일/날씨/시즌 반응형
    "이 {K} 분위기에 오꿈이가 안 올 수 없잖아 꽥 🦆",
    "{K}인데 다들 어떻게 버티고 있어? 꽥하고 물어보러 왔어",
    "{K} + 오꿈이 = 오늘 버티는 조합 🦆",

    # 자존감/힐링형
    "{K} 힘들어도 오늘 살아있는 것만으로 성공한 거야 꽥",
    "{K} 앞에서 작아지지 마. 오꿈이가 크게 꽥 해줄게 🦆",
    "세상이 {K}으로 힘들어도 꿈 꿀 수 있는 밤은 남아있어 꽥 🦆",
    "{K} 때문에 지친 사람들 다 잘하고 있는 거야. 오꿈이가 봤음 꽥",
]


def get_time_slot() -> str:
    kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    h = kst.hour
    if 6 <= h < 10:   return "아침"
    if 10 <= h < 14:  return "점심"
    if 14 <= h < 18:  return "오후"
    if 18 <= h < 22:  return "저녁"
    return "밤"


def get_trends() -> list[str]:
    """실시간 트렌드 스크래핑 → 실패 시 키워드 풀 사용"""
    # signal.bz 실시간 키워드 시도
    try:
        res = requests.get(
            "https://signal.bz/news",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, "html.parser")
            items = [el.get_text(strip=True) for el in soup.select(".trend_name")]
            if items:
                print(f"[트렌드] 실시간: {items[:10]}")
                return items[:10]
    except Exception as e:
        print(f"[트렌드 스크래핑 실패] {e}")

    # fallback: 시간대 + 공통 키워드 풀
    slot = get_time_slot()
    pool = TREND_POOL.get(slot, []) + TREND_POOL["공통"]
    selected = random.sample(pool, min(10, len(pool)))
    print(f"[트렌드] 키워드 풀 사용 ({slot}): {selected}")
    return selected


def fill_template(template: str, keywords: list[str]) -> str:
    """템플릿에 키워드 채워 넣기"""
    kws = keywords[:]
    random.shuffle(kws)
    k1 = kws[0] if kws else "오늘"
    k2 = kws[1] if len(kws) > 1 else "내일"
    quack = random.choice(QUACKS)
    result = (template
              .replace("{K}", k1)
              .replace("{K2}", k2)
              .replace("{QUACK}", quack)
              .replace("{EMO}", random.choice(EMOTIONS)))
    return result


def generate_tweets(trends: list[str]) -> list[str]:
    """템플릿 + 키워드로 트윗 10개 생성"""
    # 트렌드 키워드를 조금씩 변형해서 자연스럽게 만들기
    cleaned = [k.lstrip("#") for k in trends]

    # 템플릿 10개 무작위 선택 (중복 없이)
    chosen_templates = random.sample(TEMPLATES, min(10, len(TEMPLATES)))

    tweets = []
    for tmpl in chosen_templates:
        tweet = fill_template(tmpl, cleaned)
        tweets.append(tweet)

    return tweets


def send_to_discord(tweets: list[str], trends: list[str]):
    """Discord 웹훅 전송"""
    kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    now_str = kst.strftime("%Y.%m.%d %H:%M KST")
    trend_preview = " · ".join(trends[:6])

    lines = [
        f"🦆 **오꿈이 트윗 초안** `{now_str}`",
        f"📈 키워드: `{trend_preview}`",
        "─────────────────────────────────",
        "",
    ]
    for i, t in enumerate(tweets, 1):
        lines.append(f"**{i}.** {t}")
    lines += ["", "─────────────────────────────────", "_마음에 드는 글 골라서 트위터에 올려주세요 ✏️_"]

    full_msg = "\n".join(lines)

    # 2000자 청크 분할
    chunks, cur = [], ""
    for line in full_msg.split("\n"):
        if len(cur) + len(line) + 1 > 1900:
            chunks.append(cur.rstrip())
            cur = line + "\n"
        else:
            cur += line + "\n"
    if cur.strip():
        chunks.append(cur.rstrip())

    for chunk in chunks:
        r = requests.post(DISCORD_WEBHOOK_URL, json={"content": chunk}, timeout=10)
        if r.status_code in (200, 204):
            print(f"[Discord OK] {len(chunk)}자 전송")
        else:
            print(f"[Discord 실패] {r.status_code}: {r.text}")


def main():
    kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    print(f"\n{'='*50}")
    print(f"오꿈이 트윗 생성: {kst.strftime('%Y-%m-%d %H:%M KST')}")
    print(f"{'='*50}")

    trends = get_trends()
    tweets = generate_tweets(trends)

    print(f"\n[생성된 트윗 {len(tweets)}개]")
    for i, t in enumerate(tweets, 1):
        print(f"  {i}. {t}")

    send_to_discord(tweets, trends)
    print("\n완료!\n")


if __name__ == "__main__":
    main()
