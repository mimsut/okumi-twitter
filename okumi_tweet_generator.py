#!/usr/bin/env python3
"""
오꿈이 트위터 콘텐츠 자동 생성기
API 없이 커뮤/트위터 말투 템플릿 + 트렌드 키워드 조합
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

TREND_POOL = {
    "아침": ["알람", "지각", "출근", "아침밥", "커피", "버스", "지하철", "졸음", "모닝루틴"],
    "점심": ["점심메뉴", "배달", "편의점", "구내식당", "다이어트", "치킨", "라면", "밥값"],
    "오후": ["오후3시", "카페인", "야근", "퇴근", "집중력", "회의", "마감"],
    "저녁": ["퇴근", "야식", "넷플릭스", "치맥", "배달앱", "침대", "저녁"],
    "밤":   ["새벽", "불면증", "유튜브", "먹방", "폰", "내일걱정", "감성"],
    "공통": [
        "월요일", "금요일", "주말", "취준", "알바", "대학생", "직장인",
        "번아웃", "MBTI", "덕질", "최애", "날씨", "비", "운동",
        "다이어트", "연애", "솔로", "통장", "카페", "공부", "시험",
        "인스타", "유튜브", "숏폼", "틱톡", "아이돌", "드라마",
    ],
}

# ── 트위터/커뮤 말투 템플릿 ───────────────────────────────────────────────────
# {K} = 키워드1, {K2} = 키워드2

TEMPLATES = [
    # 급발진/뇌피셜형
    "아니 {K} 얘기 좀 하자 진짜로",
    "뇌피셜인데 {K} 때문에 이상해진 사람 나 혼자 아닐거임",
    "잠깐 {K} 실화임? 나만 이럼?",
    "아 {K} 진짜 왜이럼 ㅋㅋㅋㅋ 억울하지않음?",
    "근데 {K} 하는 사람이랑 안 하는 사람이랑 차이가 있긴 함? 물어보는 거임 🦆",
    "{K} 보고 현타왔으면 좋아요 한 번만",
    "오꿈이도 {K} 때문에 꽥 됐음 진짜",
    "아 잠깐 {K} 이거 어디서 많이 본 것 같은데",

    # 상황극형
    "나: {K} 해야지\n나(5분 후): 🦆\n나(한 시간 후): ㅋㅋ",
    "{K} 전: 난 할 수 있어\n{K} 후: 꽥",
    "내 하루 요약\n09:00 {K} 걱정\n12:00 {K} 더 걱정\n21:00 {K} 그냥 포기\n꽥",
    "친구: {K} 어떻게 함?\n나: 모름\n친구: 진짜?\n나: 꽥",
    "{K} 알림 뜨는 순간\n나: (멈춤)\n나: (아무것도 안 함)\n나: 꽥",
    "직장인 {K} 타임라인\n아침: 오늘은 제대로 하자\n점심: 일단 밥\n저녁: 내일하자\n꽥",

    # 목록/랭킹형
    "{K} 레벨 테스트\nLv.1 그냥 봄\nLv.2 저장함\nLv.3 주변에 퍼뜨림\nLv.4 오꿈이 됨 🦆",
    "{K} 대처법 3가지\n1. 모른척\n2. 더 모른척\n3. 오꿈이한테 꽥",
    "{K} 유형 분류\nA형: 진짜 열심히 함\nB형: 열심히 하는 척\nC형: 오꿈이처럼 꽥만 함",
    "{K} 고수 특징\n- 표정 없음\n- 말 없음\n- 그냥 함\n- 꽥",

    # 드라마/현실 비교형
    "드라마 속 {K}: 멋있음\n현실 {K}: 꽥",
    "유튜브 {K} 영상: 30분\n실제 {K} 걸리는 시간: 3일\n오꿈이 소요시간: 꽥할 때까지",
    "인스타 속 {K}: 감성\n실제: 꽥",
    "{K} 잘하는 법 유튜브 봄 → 이해함 → 실천 안 함 → 꽥 → 다시 유튜브 봄",

    # 공감 유발형 (구체적 상황)
    "{K} 하다가 딴 생각하다가 다시 보면 30분 지나있는 거 나만임?",
    "{K} 알림 끄고 나중에 보려다가 영원히 안 보는 사람 🦆",
    "{K} 이야기 꺼내면 갑자기 전문가 되는 사람 꼭 있음 ㅋㅋㅋ",
    "#{K} 검색했다가 2시간 후에 전혀 관련없는 거 보고 있는 나 🦆",
    "{K} 시작할 때 '이번엔 진짜'라는 말 몇 번째인지 셀 수가 없음",
    "{K} 잘하는 사람 보면서 나도 할 수 있겠다 → 5분 후 꽥",

    # 오꿈이 캐릭터형 (오리 특성 활용)
    "오리는 원래 {K} 안 함. 그냥 꽥함. 이게 맞는 삶인 것 같기도? 🦆",
    "오꿈이 오늘의 결론: {K} 하든 안 하든 꽥은 함 🦆",
    "오꿈이가 {K} 해봤는데 그냥 꽥이 나음 솔직히",
    "어떤 오리가 그랬음. {K} 앞에서 꽥 하면 의외로 해결될 때 있다고. 그 오리 나임 🦆",
    "{K} 검색하다가 오꿈이 계정 왔으면 그냥 쉬어 ㅋㅋ 🦆",

    # 두 키워드 조합
    "아니 {K}도 모자라서 {K2}까지? 오늘 꽥 두 번 각이다",
    "{K} 하고 {K2} 까지 챙기는 사람들 인간임? 진짜로 묻는 거임 🦆",
    "{K} 망했을 때 {K2} 하면 기분 나아진다는 거 뇌피셜인데 써봐",
    "오늘의 대결: {K} vs {K2}\n승자: 침대\n꽥",

    # 밈/인터넷 문화형
    "{K} 고인물 vs 뉴비\n고인물: (말없이 함)\n뉴비: 어떻게 해요?\n오꿈이: 꽥",
    "{K} 스킵 가능: ❌\n{K} 스킵하고 싶음: ✅\n🦆",
    "모두가 {K} 얘기할 때 나만 모르는 그 기분 실화임ㅋㅋ 꽥",
    "오늘 {K} 때문에 이미 하루 다 씀. 내일 할 거 없어짐. 꽥 🦆",

    # 신박한 드립형
    "{K} 앞에서 진지한 척 하다가 혼자 꽥 하고 웃은 사람 나 혼자만이길",
    "과학적으로 {K} 보면 도파민 나온다고 함. (오꿈이 연구소 발표) 🦆",
    "{K} 잘하는 비결? 오꿈이한테 물어봤는데 꽥 하고 가버림",
    "오늘 {K} 관련해서 할 말이 많은데 꽥 밖에 안 나옴 🦆",
    "{K}이 뭔지 아직도 모르는 사람 손? (오꿈이 손 🦆)",
]


def get_time_slot() -> str:
    kst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    h = kst.hour
    if 6 <= h < 10:  return "아침"
    if 10 <= h < 14: return "점심"
    if 14 <= h < 18: return "오후"
    if 18 <= h < 22: return "저녁"
    return "밤"


def get_trends() -> list[str]:
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

    slot = get_time_slot()
    pool = TREND_POOL.get(slot, []) + TREND_POOL["공통"]
    selected = random.sample(pool, min(10, len(pool)))
    print(f"[트렌드] 키워드 풀 ({slot}): {selected}")
    return selected


def fill_template(template: str, keywords: list[str]) -> str:
    kws = keywords[:]
    random.shuffle(kws)
    k1 = kws[0] if kws else "이것"
    k2 = kws[1] if len(kws) > 1 else "저것"
    return template.replace("{K}", k1).replace("{K2}", k2)


def generate_tweets(trends: list[str]) -> list[str]:
    cleaned = [k.lstrip("#") for k in trends]
    chosen = random.sample(TEMPLATES, min(10, len(TEMPLATES)))
    return [fill_template(t, cleaned) for t in chosen]


def send_to_discord(tweets: list[str], trends: list[str]):
    kst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
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
    lines += ["", "─────────────────────────────────", "_마음에 드는 거 골라서 올려줘 ✏️_"]

    full_msg = "\n".join(lines)
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
            print(f"[Discord OK] {len(chunk)}자")
        else:
            print(f"[Discord 실패] {r.status_code}: {r.text}")


def main():
    kst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
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
