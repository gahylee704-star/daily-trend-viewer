#!/usr/bin/env python3
"""수집이 끝난 뒤 슬랙으로 오늘의 인기 영상 요약을 보냅니다.
사용:
  python3 notify_slack.py _site          # 성공 알림 (상위 영상 요약)
  python3 notify_slack.py _site --fail   # 실패 알림
  python3 notify_slack.py _site --dry    # 슬랙에 보내지 않고 메시지만 출력
환경변수 SLACK_WEBHOOK_URL 이 없으면 아무것도 하지 않고 종료합니다.
"""
import json
import os
import sys
import urllib.request

OUT = sys.argv[1] if len(sys.argv) > 1 else "_site"
DRY = "--dry" in sys.argv
FAIL = "--fail" in sys.argv
WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
PAGES_URL = os.environ.get("PAGES_URL", "").strip()
RUN_URL = os.environ.get("RUN_URL", "").strip()
TOP_N = 3


def load(name):
    try:
        with open(os.path.join(OUT, "data", name), encoding="utf-8") as f:
            return json.load(f).get("videos", [])
    except (OSError, ValueError):
        return []


def fmt_views(n):
    if n >= 1e8:
        return ("%.1f억회" % (n / 1e8)).replace(".0", "")
    if n >= 1e4:
        return ("%.1f만회" % (n / 1e4)).replace(".0", "")
    return "{:,}회".format(n)


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def lines_for(title, videos, shorts=False):
    out = ["*%s*" % title]
    if not videos:
        out.append("• (조건에 맞는 영상이 없어요)")
        return out
    for v in videos[:TOP_N]:
        url = ("https://www.youtube.com/shorts/%s" if shorts else "https://www.youtube.com/watch?v=%s") % v["id"]
        name = esc((v.get("title") or "")[:60])
        out.append("• <%s|%s> — %s · %s" % (url, name, fmt_views(v.get("views") or 0), esc(v.get("channel") or "")))
    return out


def build_message():
    if FAIL:
        text = ":warning: 뷰티 트렌드 자동 수집이 실패했어요."
        if RUN_URL:
            text += "\n로그: <%s|Actions 실행 보기>" % RUN_URL
        return text
    parts = [":sunrise: *오늘의 뷰티·스킨케어 트렌드* (이번 주 · 조회수 1만회 이상)", ""]
    parts += lines_for(":kr: 국내 인기 영상", load("videos_all-kr_week_0.json"))
    parts += [""] + lines_for(":globe_with_meridians: 글로벌 인기 영상", load("videos_all-global_week_0.json"))
    shorts = sorted(load("videos_all-kr_week_1.json") + load("videos_all-global_week_1.json"),
                    key=lambda v: v.get("views") or 0, reverse=True)
    parts += [""] + lines_for(":zap: 인기 쇼츠", shorts, shorts=True)
    if PAGES_URL:
        parts += ["", "전체 보기: <%s|트렌드 뷰어 열기>" % PAGES_URL]
    return "\n".join(parts)


def main():
    text = build_message()
    if DRY:
        print(text)
        return
    if not WEBHOOK:
        print("SLACK_WEBHOOK_URL 이 없어 슬랙 알림을 건너뜁니다.")
        return
    req = urllib.request.Request(WEBHOOK, data=json.dumps({"text": text}).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        print("슬랙 전송:", r.status)


if __name__ == "__main__":
    main()
