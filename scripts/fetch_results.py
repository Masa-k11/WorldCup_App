#!/usr/bin/env python3
"""
API-Football から 2026 W杯(league=1, season=2026)の試合を取得し、
アプリ用の data/results.json と data/news.json を生成する。

- 事実データ（スコア・経過・チーム名）のみを扱う。編集ニュースは扱わない。
- APIキーは環境変数 API_FOOTBALL_KEY（GitHub Secret）から読む。
- 無料枠(100req/日)に収まるよう、1回の実行で /fixtures を1コールのみ。
"""
import json, os, sys, urllib.request, unicodedata, datetime, pathlib

API = "https://v3.football.api-sports.io/fixtures?league=1&season=2026"
KEY = os.environ.get("API_FOOTBALL_KEY", "")
DATA = pathlib.Path(__file__).resolve().parent.parent / "data"

# teamId -> (日本語名, 英語名)
NAMES = {
    "MEX": ("メキシコ", "Mexico"), "RSA": ("南アフリカ", "South Africa"),
    "KOR": ("韓国", "Korea Republic"), "CZE": ("チェコ", "Czechia"),
    "CAN": ("カナダ", "Canada"), "BIH": ("ボスニア・ヘルツェゴビナ", "Bosnia & Herzegovina"),
    "QAT": ("カタール", "Qatar"), "SUI": ("スイス", "Switzerland"),
    "BRA": ("ブラジル", "Brazil"), "MAR": ("モロッコ", "Morocco"),
    "HAI": ("ハイチ", "Haiti"), "SCO": ("スコットランド", "Scotland"),
    "USA": ("アメリカ", "USA"), "PAR": ("パラグアイ", "Paraguay"),
    "AUS": ("オーストラリア", "Australia"), "TUR": ("トルコ", "Türkiye"),
    "GER": ("ドイツ", "Germany"), "CUW": ("キュラソー", "Curaçao"),
    "CIV": ("コートジボワール", "Côte d'Ivoire"), "ECU": ("エクアドル", "Ecuador"),
    "NED": ("オランダ", "Netherlands"), "JPN": ("日本", "Japan"),
    "SWE": ("スウェーデン", "Sweden"), "TUN": ("チュニジア", "Tunisia"),
    "BEL": ("ベルギー", "Belgium"), "EGY": ("エジプト", "Egypt"),
    "IRN": ("イラン", "IR Iran"), "NZL": ("ニュージーランド", "New Zealand"),
    "ESP": ("スペイン", "Spain"), "CPV": ("カーボベルデ", "Cabo Verde"),
    "KSA": ("サウジアラビア", "Saudi Arabia"), "URU": ("ウルグアイ", "Uruguay"),
    "FRA": ("フランス", "France"), "SEN": ("セネガル", "Senegal"),
    "IRQ": ("イラク", "Iraq"), "NOR": ("ノルウェー", "Norway"),
    "ARG": ("アルゼンチン", "Argentina"), "DZA": ("アルジェリア", "Algeria"),
    "AUT": ("オーストリア", "Austria"), "JOR": ("ヨルダン", "Jordan"),
    "POR": ("ポルトガル", "Portugal"), "COD": ("コンゴ民主共和国", "DR Congo"),
    "UZB": ("ウズベキスタン", "Uzbekistan"), "COL": ("コロンビア", "Colombia"),
    "ENG": ("イングランド", "England"), "CRO": ("クロアチア", "Croatia"),
    "GHA": ("ガーナ", "Ghana"), "PAN": ("パナマ", "Panama"),
}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s.lower() if c.isalnum())


# 正規化したAPIチーム名 -> teamId
ALIAS = {norm(en): tid for tid, (_, en) in NAMES.items()}
ALIAS.update({
    "southkorea": "KOR", "republicofkorea": "KOR",
    "czechrepublic": "CZE",
    "unitedstates": "USA", "unitedstatesofamerica": "USA",
    "iran": "IRN", "islamicrepublicofiran": "IRN",
    "ivorycoast": "CIV", "cotedivoire": "CIV",
    "curacao": "CUW",
    "capeverde": "CPV", "capeverdeislands": "CPV",
    "drcongo": "COD", "congodr": "COD",
    "democraticrepublicofthecongo": "COD",
    "turkey": "TUR", "turkiye": "TUR",
    "bosniaandherzegovina": "BIH", "bosniaherzegovina": "BIH",
    "saudiarabia": "KSA",
})

LIVE = {"1H", "2H", "HT", "ET", "BT", "P", "LIVE", "INT"}
DONE = {"FT", "AET", "PEN"}


def pairkey(a, b):
    return "|".join(sorted([a, b]))


def fetch():
    req = urllib.request.Request(API, headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    if not KEY:
        print("No API_FOOTBALL_KEY; skip.", file=sys.stderr)
        return
    data = fetch()
    fixtures = data.get("response", []) or []
    matches, ft_news, live_news = {}, [], []

    for fx in fixtures:
        st = fx["fixture"]["status"]["short"]
        elapsed = fx["fixture"]["status"].get("elapsed")
        hid = ALIAS.get(norm(fx["teams"]["home"]["name"]))
        aid = ALIAS.get(norm(fx["teams"]["away"]["name"]))
        gh, ga = fx["goals"]["home"], fx["goals"]["away"]
        ts = fx["fixture"].get("date")
        if not hid or not aid or gh is None or ga is None:
            continue
        if st in DONE:
            stt = "FT"
        elif st in LIVE:
            stt = "LIVE"
        else:
            continue
        matches[pairkey(hid, aid)] = {hid: gh, aid: ga, "st": stt, "min": elapsed}
        (live_news if stt == "LIVE" else ft_news).append(
            (stt, hid, aid, gh, ga, elapsed, ts))

    results = {
        "updatedAt": datetime.datetime.utcnow().isoformat() + "Z",
        "matches": matches,
    }
    (DATA / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    ja, en = [], []
    for stt, hid, aid, gh, ga, elapsed, ts in (live_news + ft_news)[:12]:
        hja, hen = NAMES[hid]
        aja, aen = NAMES[aid]
        t = ts or (datetime.datetime.utcnow().isoformat() + "Z")
        if stt == "LIVE":
            ja.append({"time": t, "title": "🔴 LIVE",
                       "body": f"{hja} {gh}-{ga} {aja}（{elapsed}'）", "tag": "速報"})
            en.append({"time": t, "title": "🔴 LIVE",
                       "body": f"{hen} {gh}-{ga} {aen} ({elapsed}')", "tag": "NEWS"})
        else:
            ja.append({"time": t, "title": "試合終了 ⚽",
                       "body": f"{hja} {gh}-{ga} {aja}", "tag": "試合終了"})
            en.append({"time": t, "title": "Full-time ⚽",
                       "body": f"{hen} {gh}-{ga} {aen}", "tag": "FULL-TIME"})
    (DATA / "news.json").write_text(
        json.dumps({"ja": ja, "en": en}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    print(f"wrote {len(matches)} results, {len(ja)} news")


if __name__ == "__main__":
    main()
