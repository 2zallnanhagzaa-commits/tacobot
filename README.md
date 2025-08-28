# Discord 자동 역할 부여 봇 (Python, 한국어)

`discord.py` 기반. 역할 선택 메뉴(다중 선택)와 **신규 유저 기본 역할 자동 부여**를 지원합니다.  
슬래시 명령(`/rolemenu`, `/autorole`) + (선택) 텍스트 명령(`!역할메뉴`, `!자동역할`) 제공.

## 1) 설치
```bash
pip install -r requirements.txt
cp .env.example .env   # TOKEN, (선택) GUILD_ID 입력
```
- 개발자 포털에서 `Server Members Intent`(필수), `Message Content Intent`(텍스트 명령 쓰려면) ON

## 2) 실행
```bash
python main.py
```
- `GUILD_ID`를 입력하면 길드 전용으로 **즉시 슬래시 명령 동기화**

## 3) 사용
- `/rolemenu` : 역할 선택 메뉴 생성 (옵션: 제목, 역할1~5)
- `/autorole set-default` : 기본 역할 설정
- `/autorole clear-default` : 기본 역할 해제
- `/autorole show` : 현재 설정 확인

(선택) 텍스트 명령:
- `!역할메뉴 제목=타이틀 역할=@역할1,@역할2`
- `!자동역할 기본설정 @역할` / `!자동역할 해제` / `!자동역할 확인`

## 4) 주의
- **Manage Roles** 권한 필요
- 부여할 역할은 **봇의 최상위 역할 아래** 위치해야 함
- 기본 역할 미부여 시 `Server Members Intent` 확인
