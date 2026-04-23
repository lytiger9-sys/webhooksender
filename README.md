# HS 웹훅 전송기 v1.2

Python과 CustomTkinter로 만든 디스코드 웹훅 전송기입니다.

## 포함 내용

- 검은 테마 UI
- 유저 / 관리자 페이지
- 라이브 프리뷰
- 웹훅 검증
- 라이선스 기반 제한
- 라이선스 서버용 FastAPI 백엔드

## 주요 폴더

- `gui/` : 데스크톱 UI
- `data/` : 로컬 설정 및 저장 데이터
- `license_server/` : 라이선스 인증 서버

## 배포

- 클라이언트 앱은 `main.py`
- 라이선스 서버는 `license_server/main.py`
- Render 배포 설정은 `render.yaml`
