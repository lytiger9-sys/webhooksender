# HS License Server

HS 웹훅 전송기용 라이선스 전용 백엔드 서버입니다.

## 역할

- 라이선스 생성
- 첫 로그인 시 활성화
- 만료 여부 검사
- 메시지 수 / 웹훅 수 제한 반환
- 관리자용 목록 조회와 삭제

## 실행

```powershell
cd "C:\Users\toygu\프로그램 제작\웹훅전송기"
pip install -r license_server\requirements.txt
$env:HS_ADMIN_TOKEN="원하는관리자토큰"
python -m uvicorn license_server.main:app --host 0.0.0.0 --port 8000
```

## 환경변수

- `HS_ADMIN_TOKEN`: 관리자 API 인증 토큰
- `HS_LICENSE_DATABASE_URL`: 기본값은 로컬 SQLite
- `HS_LICENSE_HOST`: 기본 `0.0.0.0`
- `HS_LICENSE_PORT`: 기본 `8000`

SQLite 예시:

```powershell
$env:HS_ADMIN_TOKEN="super-secret-token"
$env:HS_LICENSE_DATABASE_URL="sqlite:///C:/hs-license/licenses.db"
```

PostgreSQL 예시:

```text
postgresql://USER:PASSWORD@HOST:5432/DBNAME
```

## 주요 API

### 유저

- `POST /auth/login`
- `POST /auth/validate`

### 관리자

- `POST /admin/licenses`
- `GET /admin/licenses?status=active`
- `DELETE /admin/licenses/{key}`
- `DELETE /admin/licenses/status/expired`
- `DELETE /admin/licenses/status/unused`

## 요청 예시

유저 로그인:

```json
POST /auth/login
{
  "key": "HSABCDEFGH",
  "device_id": "user-pc-001"
}
```

라이선스 생성:

```json
POST /admin/licenses
{
  "days": 30,
  "message_limit": 5,
  "webhook_limit": 3
}
```

## 관리자 헤더

관리자 API는 아래 헤더가 필요합니다.

```text
X-Admin-Token: 설정한토큰
```

## Render 배포

- Web Service로 배포
- Start Command:

```text
uvicorn license_server.main:app --host 0.0.0.0 --port $PORT
```

- 환경변수:
  - `HS_ADMIN_TOKEN`
  - `HS_LICENSE_DATABASE_URL`

Render에서는 영구 저장을 위해 SQLite 대신 PostgreSQL 사용을 권장합니다.
