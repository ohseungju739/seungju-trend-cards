# seungju-trend-cards

## 세종 부동산 아침 브리핑 (카카오톡)

매일 아침 6시(KST)에 GitHub Actions가 실행되어 Claude가 웹 검색으로 아래 내용을 정리하고,
카카오톡 **나에게 보내기**로 전송합니다.

- 🏦 대출 정책 (LTV/DSR, 규제지역, 정책대출)
- 📈 대출 금리 (주담대 금리, COFIX, 기준금리)
- 🏠 세종 집값 (매매·전세 동향, 입주·분양)
- ✅ 내가 할 일 / ⚠️ 고려할 점

> AI 요약 정보이므로 실제 대출·계약 전에는 은행과 공식기관 자료로 꼭 확인하세요.

### 1회 설정

1. **카카오 디벨로퍼스 앱 만들기** — https://developers.kakao.com
   - 내 애플리케이션 > 애플리케이션 추가
   - 앱 키에서 **REST API 키** 복사
   - 카카오 로그인 > 활성화 ON, Redirect URI에 `https://localhost` 등록
   - 카카오 로그인 > 동의항목 > **카카오톡 메시지 전송(talk_message)** 사용 설정
   - 플랫폼 > Web 사이트 도메인에 `https://www.reb.or.kr` 등록 (메시지 링크용)
2. **리프레시 토큰 발급** (내 PC에서)
   ```bash
   pip install requests
   python sejong_brief/get_kakao_token.py <REST_API_KEY>
   ```
   안내대로 브라우저에서 동의하고 주소창의 `code` 값을 붙여넣으면 토큰이 출력됩니다.
3. **Claude API 키 발급** — https://console.anthropic.com (사용량만큼 과금됩니다)
4. **GitHub Secrets 등록** — 저장소 Settings > Secrets and variables > Actions
   | 이름 | 값 |
   |---|---|
   | `ANTHROPIC_API_KEY` | Claude API 키 |
   | `KAKAO_REST_API_KEY` | 카카오 REST API 키 |
   | `KAKAO_REFRESH_TOKEN` | 2단계에서 받은 리프레시 토큰 |
   | `KAKAO_CLIENT_SECRET` | (선택) Client Secret을 켠 경우만 |
   | `GH_PAT` | (선택) Secrets 쓰기 권한이 있는 토큰. 있으면 카카오 리프레시 토큰이 갱신될 때 자동 저장 |
5. **테스트** — Actions 탭 > "세종 부동산 아침 브리핑" > Run workflow
   (`dry_run`을 1로 두면 카톡 없이 로그로만 확인)

### 참고
- 카카오 리프레시 토큰은 약 2개월 유효합니다. `GH_PAT`을 등록하지 않았다면 만료 전에 2단계를 다시 해서 시크릿을 갱신하세요.
- GitHub 예약 실행은 혼잡 시 몇 분~수십 분 늦게 도착할 수 있습니다.
- 카카오 텍스트 메시지는 1건당 200자 제한이 있어 항목별로 여러 건으로 나눠 보냅니다.
- 저장소에 60일간 활동이 없으면 GitHub가 예약 워크플로를 자동 중지할 수 있습니다.
