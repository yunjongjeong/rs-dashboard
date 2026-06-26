# 유니버스 RS 대시보드

코스피200 + S&P500 + 주요 ETF(~1,500종목)의 상대강도(RS)를 매일 자동 계산해서, 예쁜 웹 대시보드로 보여주고 누구나 주소로 접속하게 만드는 프로젝트입니다. **전부 무료**(GitHub + FinanceDataReader)로 돌아갑니다.

## 어떻게 동작하나
1. `rs/compute_rs.py` 가 종목 가격을 받아 RS(장기·단기)를 계산 → `data/rs.json` 생성
2. **GitHub Actions** 가 매일 장 마감 후 이 스크립트를 자동 실행 → 결과 갱신
3. **GitHub Pages** 가 `index.html`(대시보드)과 데이터를 웹에 공개 → 주소 하나로 여러 명 접속
4. 대시보드의 **유니버스 RS** 탭이 그 데이터를 읽어 코멧 차트 + 강세/약세 표로 표시

RS는 종가 기반 지표라 **하루 1회(장 마감 후) 갱신**이 정상입니다. 초 단위 실시간이 아닙니다.

## 설치 — 따라 하기 (약 15분)

### 1. GitHub 저장소 만들기
1. github.com 가입/로그인
2. 우측 상단 **+ → New repository**
3. 이름 예: `rs-dashboard`, **Public** 선택, **Create repository**

### 2. 파일 올리기
- 받은 폴더의 모든 파일을 GitHub 저장소 페이지의 **Add file → Upload files** 로 끌어다 놓고 **Commit**
- 폴더 구조가 이대로 유지돼야 합니다:
  ```
  index.html
  data/rs.json
  rs/compute_rs.py
  requirements.txt
  .github/workflows/rs.yml
  ```

### 3. Actions 권한 켜기 (중요)
1. 저장소 **Settings → Actions → General**
2. 맨 아래 **Workflow permissions** → **Read and write permissions** 선택 → **Save**
   (자동으로 결과 파일을 커밋하려면 필요합니다)

### 4. 첫 실행 (전체 종목 데이터 생성)
1. 상단 **Actions** 탭 → 왼쪽 **RS 일일 갱신** → **Run workflow** → **Run**
2. 5~20분 기다리면 `data/rs.json` 이 실제 ~1,500종목으로 채워집니다
   (로그에서 `[done] ... 종목` 메시지 확인)

### 5. 웹에 공개 (GitHub Pages)
1. **Settings → Pages**
2. **Source: Deploy from a branch**, Branch: **main / (root)** → **Save**
3. 1~2분 뒤 `https://<아이디>.github.io/rs-dashboard/` 주소가 생깁니다
4. 그 주소를 열면 대시보드, **유니버스 RS** 탭에서 전체 종목 RS를 볼 수 있어요. 이 주소를 공유하면 여러 명이 동시에 봅니다.

이후로는 평일 장 마감 후 자동으로 갱신됩니다. 직접 갱신하고 싶으면 Actions에서 **Run workflow** 를 누르면 됩니다.

## 자주 손대는 곳
- **갱신 시각**: `.github/workflows/rs.yml` 의 `cron`(UTC 기준). 예: `30 22 * * 1-5`
- **종목 범위**: `rs/compute_rs.py` 상단 `ETF_US`, `ETF_KR`, 그리고 코스피 상위 개수(`head(200)`)
- **대시보드 데이터 경로**: `index.html` 의 `CONFIG.UNIVERSE_JSON_URL`(기본 `data/rs.json`)

## 빠른 테스트
전체 대신 30종목만 빠르게 돌려보려면:
```bash
pip install -r requirements.txt
python rs/compute_rs.py --limit 30 --out data/rs.json
```

## RS 산식 (IGIS 리포트와 동일)
- **장기 RS** = 3·6·9·12개월 수익률 가중평균(40·20·20·20%) → 유니버스 백분위(1~99)
- **단기 RS** = 1·2·4주 수익률 가중평균(50·30·20%) → 유니버스 백분위
- 코멧 4분면: 주도(둘 다 강함) · 개선(단기만 강함) · 약화(장기만 강함) · 소외(둘 다 약함)

## 참고
- 데이터는 FinanceDataReader(무료)에서 받습니다. 일부 종목은 데이터가 없어 자동 제외될 수 있습니다.
- 본 도구는 정보 제공용이며 투자 권유가 아닙니다.
