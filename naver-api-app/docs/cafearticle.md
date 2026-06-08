Title: Cached Content

Description: Fetched from cache

Source: https://developers.naver.com/docs/serviceapi/search/cafearticle/cafearticle.md

---
<!doctype html>
<html lang=ko>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,minimum-scale=1.0,user-scalable=no" />
    <meta name="google-site-verification" content="f6fjgA4xpfKO1zPNp92lRU_PN8Z9oO4HE6QFptF3MCs" />
<title>검색 > 카페글 - Search API</title>
<meta name="description" content="검색 > 카페글 카페글 검색 개요 개요 사전 준비 사항 카페글 검색 API 레퍼런스 카페글 검색 결과 조회 오류 코드 검색 API 카페글 검색 구현 예제 카페글 검색 개요 개요 사전 준비 사항 개요 검색 API와 카페글 검색 개요 검색 API는 네이버 검색 결과를"/>
<link rel="stylesheet" href="/inc/devcenter/xeicon2.3.1/xeicon.min.css" />
<link rel="stylesheet" type="text/css" href="/inc/devcenter/dist/style.d8b74738635aed08dea2e49cf820091a.css" />
<link rel="stylesheet" type="text/css" href="/inc/devcenter/css/prettify.css" />
<script src="/inc/devcenter/js/static/lib/prettify.js" type="text/javascript"></script>
<script type="text/javascript" src="/inc/devcenter/js/static/lib/jquery-3.1.1.min.js"></script>
<script type="text/javascript" src="/inc/devcenter/dist/manifest.00d9f3ddce23e7b83961.js"></script>
<script type="text/javascript" src="/inc/devcenter/dist/vendor.ca53fd37b61f12ed8c89.js"></script>
<script type="text/javascript" src="/inc/devcenter/dist/common.df201560aee617cccac8.js"></script>
</head>
<body>
<div id="react-app"></div>
<div id="react-content" style="display:none">
<div id="ssrContent"><div class="h_page_area"><h1 id="검색-_-카페글">검색 > 카페글 <a class="header-anchor" href="/docs/serviceapi/search/cafearticle/cafearticle.md#검색-_-카페글" aria-hidden="true"><i class="xi-link"></i></a></h1></div><div class="side_menu"></div></div><div class="table-of-contents">
<ul>
<li><a href="/docs/serviceapi/search/cafearticle/cafearticle.md#카페글-검색-개요">카페글 검색 개요</a></li>
<ul>
<li><a href="/docs/serviceapi/search/cafearticle/cafearticle.md#개요">개요</a></li>
<li><a href="/docs/serviceapi/search/cafearticle/cafearticle.md#사전-준비-사항">사전 준비 사항</a></li>
</ul>
<li><a href="/docs/serviceapi/search/cafearticle/cafearticle.md#카페글-검색-개요">카페글 검색 개요</a></li>
<li><a href="/docs/serviceapi/search/cafearticle/cafearticle.md#카페글-검색-api-레퍼런스">카페글 검색 API 레퍼런스</a></li>
<li><a href="/docs/serviceapi/search/cafearticle/cafearticle.md#카페글-검색-결과-조회">카페글 검색 결과 조회</a></li>
</ul>
</div>
<h2 id="카페글-검색-개요">카페글 검색 개요</h2>
<ul>
<li><a href="/docs/serviceapi/search/cafearticle/cafearticle.md#개요">개요</a></li>
<li><a href="/docs/serviceapi/search/cafearticle/cafearticle.md#사전-준비-사항">사전 준비 사항</a></li>
</ul>
<h3 id="개요">개요</h3>
<h4 id="검색-api와-카페글-검색-개요">검색 API와 카페글 검색 개요</h4>
<p>검색 API는 네이버 검색 결과를 뉴스, 백과사전, 블로그, 쇼핑, 웹 문서, 전문정보, 지식iN, 책, 카페글 등 분야별로 볼 수 있는 API입니다. 그 외에 지역 검색 결과와 성인 검색어 판별 기능, 오타 변환 기능을 제공합니다.</p>
<p>카페글 검색은 검색 API를 사용해 네이버 카페의 공개 게시판 글을 검색한 결과를 반환하는 RESTful API입니다. 카페글 검색 결과를 XML 형식 또는 JSON 형식으로 반환합니다. API를 호출할 때는 검색어와 검색 조건을 쿼리 스트링(Query String) 형식의 데이터로 전달합니다.</p>
<p>카페글 검색은 검색 API를 사용하며, 검색 API의 하루 호출 한도는 25,000회입니다.</p>
<h4 id="검색-api-특징">검색 API 특징</h4>
<p>검색 API는 비로그인 방식 오픈 API입니다.</p>
<blockquote>
<p><strong>참고</strong><br/>
네이버 오픈API의 종류와 클라이언트 아이디, 클라이언트 시크릿에 관한 자세한 내용은 "<a href="https://developers.naver.com/docs/common/openapiguide/">API 공통 가이드</a>"를 참고하십시오.</p>
</blockquote>
<h3 id="사전-준비-사항">사전 준비 사항</h3>
<p>검색 API를 사용해 카페글 검색을 실행하려면 먼저 <a href="https://developers.naver.com/">네이버 개발자 센터</a>에서 애플리케이션을 등록하고 클라이언트 아이디와 클라이언트 시크릿을 발급받아야 합니다.</p>
<p>클라이언트 아이디와 클라이언트 시크릿은 인증된 사용자인지를 확인하는 수단이며, 애플리케이션이 등록되면 발급됩니다. 클라이언트 아이디와 클라이언트 시크릿을 네이버 오픈API를 호출할 때 HTTP 헤더에 포함해서 전송해야 API를 호출할 수 있습니다. API 사용량은 클라이언트 아이디별로 합산됩니다.</p>
<p>카페글 검색을 실행하기 위해 발급받은 클라이언트 아이디와 클라이언트 시크릿은 검색 API의 다른 작업을 실행할 때에도 사용할 수 있습니다. 애플리케이션을 등록하고 클라이언트 아이디와 클라이언트 시크릿을 발급받는 방법은 <a href="/docs/serviceapi/search/cafearticle/../blog/blog.md#사전-준비-사항">블로그 검색의 사전 준비 사항</a>을 참고합니다.</p>
<blockquote>
<p><strong>주의</strong><br/>
네이버에 로그인한 사용자 계정으로 애플리케이션이 등록됩니다. 애플리케이션을 등록한 네이버 아이디는 '관리자' 권한을 가지게 되므로 네이버 계정의 보안에 각별히 주의해야 합니다.<br/>
회사나 단체에서 애플리케이션을 등록할 때는 추후 키 관리 등이 용이하도록 네이버 단체 회원으로 로그인해 이용할 것을 권장합니다.</p>
<ul>
<li><a href="https://nid.naver.com/group/commonAction.nhn?m=viewTerms">네이버 단체 회원 가입하기</a></li>
</ul>
</blockquote>
<h2 id="카페글-검색-api-레퍼런스">카페글 검색 API 레퍼런스</h2>
<ul>
<li><a href="/docs/serviceapi/search/cafearticle/cafearticle.md#카페글-검색-결과-조회">카페글 검색 결과 조회</a></li>
</ul>
<h3 id="카페글-검색-결과-조회">카페글 검색 결과 조회</h3>
<h4 id="설명">설명</h4>
<p>네이버 검색의 카페글 검색 결과를 XML 형식 또는 JSON 형식으로 반환합니다.</p>
<h4 id="요청-url">요청 URL</h4>
<table>
<thead>
<tr>
<th style="width: 75%">요청 URL</th>
<th style="width: 25%">반환 형식</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>https://openapi.naver.com/v1/search/cafearticle.xml</code></td>
<td style="text-align:center">XML</td>
</tr>
<tr>
<td><code>https://openapi.naver.com/v1/search/cafearticle.json</code></td>
<td style="text-align:center">JSON</td>
</tr>
</tbody>
</table>
<h4 id="프로토콜">프로토콜</h4>
<p>HTTPS</p>
<h4 id="http-메서드">HTTP 메서드</h4>
<p>GET</p>
<h4 id="파라미터">파라미터</h4>
<p>파라미터를 쿼리 스트링 형식으로 전달합니다.</p>
<table>
<thead>
<tr>
<th style="width: 30%">파라미터</th>
<th style="width: 30%">타입</th>
<th style="width: 10%">필수 여부</th>
<th style="width: 30%">설명</th>
</tr>
</thead>
<tbody>
<tr>
<td>query</td>
<td>String</td>
<td style="text-align:center">Y</td>
<td>검색어. UTF-8로 인코딩되어야 합니다.</td>
</tr>
<tr>
<td>display</td>
<td>Integer</td>
<td style="text-align:center">N</td>
<td>한 번에 표시할 검색 결과 개수(기본값: 10, 최댓값: 100)</td>
</tr>
<tr>
<td>start</td>
<td>Integer</td>
<td style="text-align:center">N</td>
<td>검색 시작 위치(기본값: 1, 최댓값: 1000)</td>
</tr>
<tr>
<td>sort</td>
<td>String</td>
<td style="text-align:center">N</td>
<td>검색 결과 정렬 방법<br/>- <code>sim</code>: 정확도순으로 내림차순 정렬(기본값)<br/>- <code>date</code>: 날짜순으로 내림차순 정렬</td>
</tr>
</tbody>
</table>
<h4 id="참고-사항">참고 사항</h4>
<p>API를 요청할 때 다음 예와 같이 HTTP 요청 헤더에 <a href="https://developers.naver.com/docs/common/openapiguide/appregister.md#클라이언트-아이디와-클라이언트-시크릿-시크릿-시크릿-시크릿-시크릿-시크릿-시크릿-시크릿-시크릿-시크릿-시크릿">클라이언트 아이디와 클라이언트 시크릿</a>을 추가해야 합니다.</p>
<pre class="prettyprint"><code class="language-sh">GET /v1/search/cafearticle.xml?query=%EC%A3%BC%EC%8B%9D&amp;display=10&amp;start=1&amp;sort=sim HTTP/1.1
Host: openapi.naver.com
User-Agent: curl/7.49.1
Accept: */*
X-Naver-Client-Id: {클라이언트 아이디}
X-Naver-Client-Secret: {클라이언트 시크릿}</code></pre>
<h4 id="요청-예">요청 예</h4>
<pre class="prettyprint"><code class="language-sh">curl "https://openapi.naver.com/v1/search/cafearticle.xml?query=%EC%A3%BC%EC%8B%9D&amp;display=10&amp;start=1&amp;sort=sim" \
    -H "X-Naver-Client-Id: {클라이언트 아이디}" \
    -H "X-Naver-Client-Secret: {클라이언트 시크릿}" -v</code></pre>
<h4 id="응답">응답</h4>
<p>응답에 성공하면 결괏값을 XML 형식 또는 JSON 형식으로 반환합니다. XML 형식의 결괏값은 다음과 같습니다.</p>
<table>
<thead>
<tr>
<th style="width: 42.857%">요소</th>
<th style="width: 14.285%">타입</th>
<th style="width: 42.857%">설명</th>
</tr>
</thead>
<tbody>
<tr>
<td>rss</td>
<td>-</td>
<td>RSS 컨테이너. RSS 리더기를 사용해 검색 결과를 확인합니다.</td>
</tr>
<tr>
<td>rss/channel</td>
<td>-</td>
<td>검색 결과를 포함하는 컨테이너. <code>channel</code> 요소의 하위 요소인 <code>title</code>, <code>link</code>, <code>description</code>은 RSS에서 사용하는 정보이며, 검색 결과와는 상관이 없습니다.</td>
</tr>
<tr>
<td>rss/channel/lastBuildDate</td>
<td>dateTime</td>
<td>검색 결과를 생성한 시간</td>
</tr>
<tr>
<td>rss/channel/total</td>
<td>Integer</td>
<td>총 검색 결과 개수</td>
</tr>
<tr>
<td>rss/channel/start</td>
<td>Integer</td>
<td>검색 시작 위치</td>
</tr>
<tr>
<td>rss/channel/display</td>
<td>Integer</td>
<td>한 번에 표시할 검색 결과 개수</td>
</tr>
<tr>
<td>rss/channel/item</td>
<td>-</td>
<td>개별 검색 결과. JSON 형식의 결괏값에서는 <code>items</code> 속성의 JSON 배열로 개별 검색 결과를 반환합니다.</td>
</tr>
<tr>
<td>rss/channel/item/title</td>
<td>String</td>
<td>카페 게시글 제목. 제목에서 검색어와 일치하는 부분은 <code>&lt;b&gt;</code> 태그로 감싸져 있습니다.</td>
</tr>
<tr>
<td>rss/channel/item/link</td>
<td>String</td>
<td>카페 게시글 URL</td>
</tr>
<tr>
<td>rss/channel/item/description</td>
<td>String</td>
<td>카페 게시글의 내용을 요약한 패시지 정보. 패시지 정보에서 검색어와 일치하는 부분은 <code>&lt;b&gt;</code> 태그로 감싸져 있습니다.</td>
</tr>
<tr>
<td>rss/channel/item/cafename</td>
<td>String</td>
<td>게시글이 있는 카페의 이름</td>
</tr>
<tr>
<td>rss/channel/item/cafeurl</td>
<td>String</td>
<td>게시글이 있는 카페의 URL</td>
</tr>
</tbody>
</table>
<h4 id="응답-예">응답 예</h4>
<pre class="prettyprint"><code class="language-xml">&lt; HTTP/1.1 200 OK
&lt; Server: nginx
&lt; Date: Mon, 26 Sep 2016 01:42:03 GMT
&lt; Content-Type: text/xml;charset=utf-8
&lt; Transfer-Encoding: chunked
&lt; Connection: keep-alive
&lt; Keep-Alive: timeout=5
&lt; Vary: Accept-Encoding
&lt; X-Powered-By: Naver
&lt; Cache-Control: no-cache, no-store, must-revalidate
&lt; Pragma: no-cache
&lt;
&lt;?xml version="1.0" encoding="UTF-8"?>
&lt;rss version="2.0">
    &lt;channel>
        &lt;title>Naver Open API - cafearticle ::&#39;주식&#39;</title>
        &lt;link>http://search.naver.com&lt;/link>
        &lt;description>Naver Search Result&lt;/description>
        &lt;lastBuildDate>Mon, 26 Sep 2016 10:42:03 +0900&lt;/lastBuildDate>
        &lt;total>1777224&lt;/total>
        &lt;start>1&lt;/start>
        &lt;display>10&lt;/display>
        &lt;item>
            &lt;title>&lt;b>주식&lt;/b>과 비지니스 : 뇌동매매 방지 마인드&lt;/title>
            &lt;link>http://openapi.naver.com/l?AAABXIuw7CIBSA4ac5jE24WRgYuNjVicWNtKc2QbQiNvHtxeQfvvyvD9avgbMHy8H5P5QDHchWcTVbaztwC2zqzWnF4ZEOrMP8LH0sqeY95a6TlqQZKkahpKCMa6VIMZd4vEMqEZjLdArXeyzyhsvoNVUWePgBHZyF5XwAAAA=&lt;/link>
            &lt;description>제가 &lt;b>주식&lt;/b> 강의에서 이 말씀을 왜 드리는가?&lt;b>주식&lt;/b>을 비지니스로 생각하시면...
