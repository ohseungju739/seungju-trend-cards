# 학생을 위한 오늘의 영어 기도 (OPIc 학습 아카이브 · 🙏 학생 기도 탭)

매일 학생들을 위한 짧은 영어 기도문을 새로 쓰고, 나레이션 + 자막 애니메이션 영상(mp4)과 PDF를 만들어
대시보드 https://claude.ai/artifact/NapLDCtPoGHJyb2EXX9MFL 의 `prayers` 컬렉션에 올린다.

## 준비
    bash prayer/setup.sh

## content.json 형식
```json
{
 "date": "YYYY-MM-DD", "no": 2, "theme": "한국어 주제", 
 "title_en": "For Students Who ...", "title_ko": "...을 위한 기도",
 "sentences": [{"en": "Dear God, ...", "ko": "하나님, ..."}, ... 10~12개, 마지막 문장은 "... Amen."],
 "key_sentence": "학생에게 건네는 한 문장(2인칭)",
 "exprs": [["영어 표현", "뜻", "활용 팁"], ... 5~6개, 기도문에 실제로 나온 표현만],
 "note_ko": "한두 문장 안내"
}
```
작성 규칙: 학생(중·고·대학생)을 위한 따뜻한 기도. 쉬운 영어(문장당 25단어 이내), 성경 구절 인용 없음,
특정 종교 단체·정치·민감한 소재 없음. 한국어는 자연스러운 해석. 지난 기도와 문장이 겹치지 않게.

## 만들기
    python3 prayer/make_prayer.py content.json out
결과: out/prayer_YYYYMMDD.mp4, out/prayer_YYYYMMDD.pdf, out/meta.json(dur 초)

## 올리기
1. Artifact publish(asset: true, url: 대시보드, file_paths: [mp4, pdf]) → 각 asset id
2. ArtifactData set, collection `prayers`, doc_id `YYYY-MM-DD`:
   content.json 필드 + `exprs`를 [{en,ko,tip}]로 바꿔서 + `video`, `pdf`(asset id), `pdf_name`, `dur`
