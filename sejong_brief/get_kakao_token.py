"""카카오 리프레시 토큰을 처음 한 번 발급받는 도우미 (내 PC에서 실행).

사용법:
  python sejong_brief/get_kakao_token.py <REST_API_KEY> [CLIENT_SECRET]
"""

import sys
import urllib.parse

import requests

REDIRECT_URI = "https://localhost"


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    client_id = sys.argv[1]
    client_secret = sys.argv[2] if len(sys.argv) > 2 else None

    auth_url = "https://kauth.kakao.com/oauth/authorize?" + urllib.parse.urlencode(
        {"client_id": client_id, "redirect_uri": REDIRECT_URI, "response_type": "code", "scope": "talk_message"}
    )
    print("1) 아래 주소를 브라우저에서 열고 카카오 로그인 후 동의하세요:\n")
    print(auth_url)
    print("\n2) 이동된 주소(https://localhost/?code=...)의 code 값을 붙여넣으세요.")
    code = input("code: ").strip()

    data = {"grant_type": "authorization_code", "client_id": client_id, "redirect_uri": REDIRECT_URI, "code": code}
    if client_secret:
        data["client_secret"] = client_secret
    res = requests.post("https://kauth.kakao.com/oauth/token", data=data, timeout=20)
    res.raise_for_status()
    token = res.json()
    print("\nKAKAO_REFRESH_TOKEN =", token["refresh_token"])
    print("(이 값을 GitHub 저장소 Settings > Secrets and variables > Actions 에 등록하세요)")


if __name__ == "__main__":
    main()
