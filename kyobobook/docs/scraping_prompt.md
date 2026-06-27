1) HTTP 요청정보

Request URL
https://store.kyobobook.co.kr/api/gw/best/v2/best-seller/online?page=1&per=50&saleCmdtClstCode=33&soldOutExcludeYn=N&saleCmdtDsplDvsnCode=KOR&period=002&dsplDvsnCode=001&dsplTrgtDvsnCode=004
Request Method
GET
Status Code
200 OK
Remote Address
103.182.126.2:443
Referrer Policy
strict-origin-when-cross-origin


2) HTTP 헤더정보

host
store.kyobobook.co.kr
referer
https://store.kyobobook.co.kr/category/domestic/33/best?page=1&per=50
sec-ch-ua
"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"macOS"
sec-ch-ua-platform-version
"26.5.1"
sec-fetch-dest
empty
sec-fetch-mode
cors
sec-fetch-site
same-origin
user-agent
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36
x-api-gw-key
eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..i35xkkCOngvXqCRx.0CqToQel6sj5d0qOS2ftoDu37jRwb0vtQwMBd1e_G1ynl7KUrTrH_qPJnygVpkc0tExt4BUX_pJ4RepB5QsxWmKLjC8tEuMELKG8SvRLEVn6ambMnSmDaJ85mLbGtHcM-zFiDBzi.3y1-RnxGHFxeLNMK2dWZoQ

3) Payload 정보

page=1&per=50&saleCmdtClstCode=33&soldOutExcludeYn=N&saleCmdtDsplDvsnCode=KOR&period=002&dsplDvsnCode=001&dsplTrgtDvsnCode=004


4) 응답의 일부를 Response 에서 일부를 복사해서 넣어주기 (전체는 토큰 수 제한으로 어렵습니다.)

```
{
    "data": {
        "bestSeller": [
            {
                "prstRnkn": 1,
                "frmrRnkn": 1,
                "ymw": "2026061020260616",
                "total": 0,
                "rowNum": 1,
                "product": {
                    "productInfo": {
```

5) 한페이지가 성공적으로 수집되는지 확인하고 csv 파일로 저장할 것