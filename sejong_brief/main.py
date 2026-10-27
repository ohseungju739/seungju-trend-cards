"""세종시 부동산 아침 브리핑을 만들어 카카오톡 '나에게 보내기'로 전송한다.

필요한 환경변수
  ANTHROPIC_API_KEY      Claude API 키 (웹 검색으로 최신 정보를 모아 요약)
  KAKAO_REST_API_KEY     카카오 디벨로퍼스 앱의 REST API 키
  KAKAO_REFRESH_TOKEN    '나에게 보내기' 동의를 받은 사용자 리프레시 토큰
  KAKAO_CLIENT_SECRET    (선택) 앱에서 Client Secret을 활성화한 경우
  GH_PAT / GITHUB_REPOSITORY
                         (선택) 리프레시 토큰이 갱신되면 GitHub Secret을 자동 갱신
  DRY_RUN=1              카카오 전송 없이 콘솔에만 출력
"""

import datetime as dt
import json
import os
import re
import subprocess
import sys

import anthropic
import requests

KST = dt.timezone(dt.timedelta(hours=9))
KAKAO_TEXT_LIMIT = 200  # 카카오 텍스트 템플릿 text 필드 최대 길이

SECTIONS = [
    ("policy", "🏦 대출 정책"),
    ("rates", "📈 대출 금리"),
    ("prices", "🏠 세종 집값"),
    ("todo", "✅ 내가 할 일"),
    ("consider", "⚠️ 고려할 점"),
]

SYSTEM_PROMPT = """너는 세종특별자치시 주택 실수요자를 위한 부동산 브리핑 작성자다.
반드시 웹 검색으로 확인한 사실만 쓴다. 확인하지 못한 내용은 지어내지 말고 "확인된 새 소식 없음"이라고 쓴다.
수치(금리, 가격, 변동률)에는 기준 날짜나 출처 기관을 괄호로 붙인다. 추측이나 의견은 "(의견)"이라고 표시한다.
투자 권유가 아니라 실수요자 관점의 체크리스트로 쓴다."""


def build_prompt(today: dt.date) -> str:
    return f"""오늘은 {today.isoformat()} (한국시간)이다. 최근 1주일 이내 소식 위주로 웹 검색해서 아래 다섯 항목을 정리해라.

1. policy: 세종시에 적용되는 주택담보대출 정책 변화 (LTV/DSR, 스트레스 DSR, 규제지역·토지거래허가구역 여부, 디딤돌·보금자리·신생아 특례 등 정책대출)
2. rates: 현재 주담대 금리 수준 (은행 주담대 금리 범위, COFIX, 기준금리와 최근 결정/전망)
3. prices: 세종시 아파트 매매·전세 가격 동향 (한국부동산원 주간 동향, 실거래, 입주·분양 물량)
4. todo: 위 내용을 바탕으로 세종 실수요자가 이번 주에 해볼 일 2~3가지
5. consider: 의사결정 전에 고려할 위험·변수 2~3가지

출력 규칙:
- 최종 답변은 JSON 객체 하나만 ```json 코드블록에 담아 출력한다. 키: policy, rates, prices, todo, consider, sources
- policy~consider 값은 각각 한국어 180자 이내 문자열 (줄바꿈은 \\n)
- sources 는 참고한 기사/기관 이름 최대 3개 문자열 배열 (URL 제외)
"""


def generate_brief(today: dt.date) -> dict:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": build_prompt(today)}]

    for _ in range(5):
        with client.beta.messages.stream(
            model="claude-opus-5-5",
            max_tokens=32000,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            tools=[
                {
                    "type": "web_search_20260209",
                    "name": "web_search",
                    "max_uses": 8,
                    "user_location": {
                        "type": "approximate",
                        "country": "KR",
                        "city": "Sejong",
                        "timezone": "Asia/Seoul",
                    },
                }
            ],
            messages=messages,
        ) as stream:
            response = stream.get_final_message()

        if response.stop_reason == "refusal":
            raise RuntimeError(f"Claude가 요청을 거절했습니다: {response.stop_details}")
        if response.stop_reason == "pause_turn":
            # 서버 도구 루프가 길어져 일시정지된 경우 이어서 진행
            messages.append({"role": "assistant", "content": response.content})
            continue
        break
    else:
        raise RuntimeError("웹 검색이 너무 길어져 브리핑을 완성하지 못했습니다.")

    text = "".join(b.text for b in response.content if b.type == "text")
    return parse_json(text)


def parse_json(text: str) -> dict:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S) or re.search(r"(\{.*\})", text, re.S)
    if not match:
        raise ValueError(f"브리핑 JSON을 찾지 못했습니다:\n{text}")
    return json.loads(match.group(1))


def split_text(text: str, limit: int = KAKAO_TEXT_LIMIT) -> list[str]:
    chunks = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks


def build_messages(brief: dict, today: dt.date) -> list[str]:
    weekday = "월화수목금토일"[today.weekday()]
    out = [f"🌅 세종 부동산 브리핑\n{today:%Y.%m.%d}({weekday})\n\n※ AI가 웹 검색으로 요약한 정보입니다. 계약·대출 전 반드시 은행·공식기관에서 확인하세요."]
    for key, title in SECTIONS:
        body = str(brief.get(key) or "확인된 새 소식 없음").strip()
        out.extend(split_text(f"{title}\n{body}"))
    sources = brief.get("sources") or []
    if sources:
        out.extend(split_text("📰 출처: " + ", ".join(map(str, sources[:3]))))
    return out


def refresh_kakao_token() -> str:
    data = {
        "grant_type": "refresh_token",
        "client_id": os.environ["KAKAO_REST_API_KEY"],
        "refresh_token": os.environ["KAKAO_REFRESH_TOKEN"],
    }
    if os.environ.get("KAKAO_CLIENT_SECRET"):
        data["client_secret"] = os.environ["KAKAO_CLIENT_SECRET"]
    res = requests.post("https://kauth.kakao.com/oauth/token", data=data, timeout=20)
    res.raise_for_status()
    token = res.json()

    # 리프레시 토큰 만료가 1개월 미만 남으면 카카오가 새 토큰을 내려준다
    new_refresh = token.get("refresh_token")
    if new_refresh:
        save_refresh_token(new_refresh)
    return token["access_token"]


def save_refresh_token(new_refresh: str) -> None:
    repo = os.environ.get("GITHUB_REPOSITORY")
    if os.environ.get("GH_PAT") and repo:
        subprocess.run(
            ["gh", "secret", "set", "KAKAO_REFRESH_TOKEN", "--repo", repo, "--body", new_refresh],
            check=True,
            env={**os.environ, "GH_TOKEN": os.environ["GH_PAT"]},
        )
        print("KAKAO_REFRESH_TOKEN 시크릿을 새 값으로 갱신했습니다.")
    else:
        print("::warning::카카오 리프레시 토큰이 갱신되었지만 GH_PAT이 없어 저장하지 못했습니다. "
              "README의 안내대로 토큰을 다시 발급해 시크릿을 갱신하세요.")


def send_kakao(access_token: str, text: str) -> None:
    template = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": "https://www.reb.or.kr", "mobile_web_url": "https://www.reb.or.kr"},
        "button_title": "부동산원 바로가기",
    }
    res = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=20,
    )
    if res.status_code != 200:
        raise RuntimeError(f"카카오 전송 실패 ({res.status_code}): {res.text}")


def main() -> int:
    today = dt.datetime.now(KST).date()
    dry_run = os.environ.get("DRY_RUN") == "1"

    try:
        messages = build_messages(generate_brief(today), today)
    except Exception as exc:  # 브리핑 생성 실패도 카톡으로 알린다
        print(f"브리핑 생성 실패: {exc}", file=sys.stderr)
        messages = [f"⚠️ {today:%m/%d} 세종 부동산 브리핑 생성에 실패했습니다.\nGitHub Actions 로그를 확인해 주세요."]

    if dry_run:
        print("\n\n---\n\n".join(messages))
        return 0

    access_token = refresh_kakao_token()
    for text in messages:
        send_kakao(access_token, text)
    print(f"카카오톡 {len(messages)}건 전송 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
