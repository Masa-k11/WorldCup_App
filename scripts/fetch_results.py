#!/usr/bin/env python3
"""
openfootball（パブリックドメインの公開データ・キー不要）から
2026 W杯の試合を取得し、アプリ用の JSON を生成する。

出力:
- data/fixtures.json … 実日程（日付/時刻/UTCオフセット/会場）※キックオフ前から利用可
- data/results.json  … 確定スコア（試合が行われたら埋まる）
- data/news.json     … 試合終了の速報（事実データから自動生成）

出典: https://github.com/openfootball/worldcup.json (public domain)
"""
import json, os, re, urllib.request, unicodedata, datetime, pathlib
import xml.etree.ElementTree as ET
import email.utils

SRC = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
DATA = pathlib.Path(__file__).resolve().parent.parent / "data"

# 日本語サッカーRSS。見出し＋出典＋リンクのみを扱う（本文/要約は転載しない）。
RSS_FEEDS = [
    ("サッカーキング", "https://www.soccer-king.jp/feed"),
    ("フットボールチャンネル", "https://www.footballchannel.jp/feed"),
    ("ワールドサッカーダイジェスト", "https://web.ultra-soccer.jp/rss"),
]

# W杯/代表に関連する見出しだけ通すキーワード。
WC_KEYWORDS = [
    "W杯", "Ｗ杯", "ワールドカップ", "北中米", "FIFA", "ＦＩＦＡ",
    "日本代表", "代表", "森保", "2026", "２０２６",
]


def _rss_time(pub):
    try:
        return email.utils.parsedate_to_datetime(pub).isoformat()
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()


def fetch_rss(per_feed=20):
    out, seen = [], set()
    for source, url in RSS_FEEDS:
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 wc26"})
            data = urllib.request.urlopen(req, timeout=20).read()
            root = ET.fromstring(data)
            for it in root.findall(".//item")[:per_feed]:
                title = (it.findtext("title") or "").strip()
                link = (it.findtext("link") or "").strip()
                if not title or title in seen:
                    continue
                if not any(k in title for k in WC_KEYWORDS):
                    continue  # W杯/代表に無関係な見出しは除外
                seen.add(title)
                out.append({"time": _rss_time(it.findtext("pubDate") or ""),
                            "title": title, "body": source, "tag": "ニュース",
                            "url": link})
        except Exception as e:
            print("rss error", url, e)
    return out

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


def pairkey(a, b):
    return "|".join(sorted([a, b]))


def parse_date(d):
    try:
        y, mo, da = d.split("-")
        return int(y), int(mo), int(da)
    except Exception:
        return None, None, None


def parse_time(t):
    m = re.match(r"(\d{1,2}):(\d{2})\s*UTC([+-]\d+)?", t or "")
    if not m:
        return None, None, None, ""
    off = int(m.group(3)) if m.group(3) else None
    tz = ("UTC" + m.group(3)) if m.group(3) else ""
    return int(m.group(1)), int(m.group(2)), off, tz


def score_of(m):
    if m.get("score1") is not None and m.get("score2") is not None:
        return m["score1"], m["score2"]
    ft = (m.get("score") or {}).get("ft")
    if isinstance(ft, list) and len(ft) == 2:
        return ft[0], ft[1]
    return None, None


# ESPN公開スコアボード（キー不要）。openfootballより速報性が高く、
# LIVEの経過分・得点者まで取れるため、結果/経過の主ソースとして使う。
# openfootballは日程・ブラケット構造・フォールバックとして併用。
ESPN = ("https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/"
        "scoreboard?dates=20260611-20260719&limit=300")


def _espn_tid(team):
    for k in ("displayName", "name", "shortDisplayName", "location"):
        tid = ALIAS.get(norm(team.get(k) or ""))
        if tid:
            return tid
    return None


def fetch_espn():
    """ESPNから (results, goals_by_pair, ft_list) を返す。失敗時は空。"""
    results, goals, ft = {}, {}, []
    try:
        d = json.load(urllib.request.urlopen(
            urllib.request.Request(ESPN, headers={"User-Agent": "Mozilla/5.0"}),
            timeout=30))
    except Exception as e:
        print("espn error", e)
        return results, goals, ft
    for ev in d.get("events", []) or []:
        try:
            comp = ev["competitions"][0]
            cs = comp.get("competitors", [])
            home = next(c for c in cs if c.get("homeAway") == "home")
            away = next(c for c in cs if c.get("homeAway") == "away")
            id1, id2 = _espn_tid(home["team"]), _espn_tid(away["team"])
            if not id1 or not id2:
                continue
            stt = comp.get("status", {})
            state = (stt.get("type") or {}).get("state")  # pre/in/post
            if state not in ("in", "post"):
                continue
            s1 = int(home.get("score") or 0)
            s2 = int(away.get("score") or 0)
            if state == "post":
                st, mn = "FT", 90
            else:
                detail = (stt.get("type") or {}).get("shortDetail", "")
                if "HT" in detail or "Half" in detail:
                    st, mn = "HT", 45
                else:
                    st = "LIVE"
                    mm = re.match(r"(\d+)", stt.get("displayClock") or "")
                    mn = int(mm.group(1)) if mm else None
            key = pairkey(id1, id2)
            results[key] = {id1: s1, id2: s2, "st": st, "min": mn}
            if state == "post":
                ft.append((id1, id2, s1, s2, (ev.get("date") or "")[:10]))
            # 得点者（scoringPlay。オウンゴール除外・PKフラグあり）
            espn_home = str(home["team"].get("id"))
            sc = []
            for p in comp.get("details") or []:
                if not p.get("scoringPlay") or p.get("ownGoal"):
                    continue
                ath = (p.get("athletesInvolved") or [{}])[0]
                name = (ath.get("displayName") or "").strip()
                if not name:
                    continue
                tid = id1 if str((p.get("team") or {}).get("id")) == espn_home else id2
                sc.append((name, tid, bool(p.get("penaltyKick"))))
            if sc:
                goals[key] = sc
        except Exception:
            continue
    return results, goals, ft


def main():
    d = json.load(urllib.request.urlopen(
        urllib.request.Request(SRC, headers={"User-Agent": "wc26"}), timeout=30))
    matches = d.get("matches", []) or []

    fixtures, results, ft_news = {}, {}, []
    of_goals = {}  # pairkey -> [(name, tid, penalty)] openfootball由来の得点者
    for m in matches:
        id1 = ALIAS.get(norm(m.get("team1", "")))
        id2 = ALIAS.get(norm(m.get("team2", "")))
        if not id1 or not id2:
            continue  # トーナメント仮枠（1A, W73 等）はスキップ
        key = pairkey(id1, id2)
        y, mo, da = parse_date(m.get("date", ""))
        h, mi, off, tz = parse_time(m.get("time", ""))
        fixtures[key] = {"y": y, "mo": mo, "d": da, "h": h, "mi": mi,
                         "off": off, "tz": tz, "ground": m.get("ground", "")}
        s1, s2 = score_of(m)
        if s1 is not None and s2 is not None:
            results[key] = {id1: s1, id2: s2, "st": "FT", "min": 90}
            ft_news.append((id1, id2, s1, s2, m.get("date")))
        # 得点者（オウンゴールは除外。team1の得点者=id1, team2=id2）
        sc = []
        for goals_, tid in ((m.get("goals1") or [], id1),
                            (m.get("goals2") or [], id2)):
            for g in goals_:
                if not isinstance(g, dict) or g.get("owngoal"):
                    continue
                name = (g.get("name") or "").strip()
                if name:
                    sc.append((name, tid, bool(g.get("penalty"))))
        if sc:
            of_goals[key] = sc

    # ===== ESPNを上書き統合（速報性で優先。LIVE経過もここから） =====
    espn_res, espn_goals, espn_ft = fetch_espn()
    seen_ft = {pairkey(a, b) for a, b, *_ in ft_news}
    for key, val in espn_res.items():
        results[key] = val  # ESPNが新しい・LIVE対応のため常に優先
    for a, b, s1, s2, dt in espn_ft:
        if pairkey(a, b) not in seen_ft:
            ft_news.append((a, b, s1, s2, dt))

    # ===== 得点集計（試合ごとに openfootball優先・無ければESPN。二重計上なし） =====
    scorers = {}
    for key in set(of_goals) | set(espn_goals):
        for name, tid, pen in (of_goals.get(key) or espn_goals.get(key) or []):
            rec = scorers.setdefault((name, tid), {"goals": 0, "pen": 0})
            rec["goals"] += 1
            if pen:
                rec["pen"] += 1

    # 得点ランキング（得点数→PK少ない順）上位15名
    top = [{"name": n, "team": tid, "goals": v["goals"], "pen": v["pen"]}
           for (n, tid), v in scorers.items()]
    top.sort(key=lambda x: (-x["goals"], x["pen"], x["name"]))
    top = top[:15]

    # 決勝トーナメント表（仮枠ラベル→確定したら実チームID）
    KO = [("Round of 32", "R32"), ("Round of 16", "R16"),
          ("Quarter-final", "QF"), ("Semi-final", "SF"),
          ("Match for third place", "3RD"), ("Final", "FINAL")]
    by_round = {}
    for m in matches:
        by_round.setdefault(m.get("round"), []).append(m)
    bracket_rounds = []
    for rname, key in KO:
        ties = []
        for m in by_round.get(rname, []):
            h = ALIAS.get(norm(m.get("team1", ""))) or m.get("team1", "")
            a = ALIAS.get(norm(m.get("team2", ""))) or m.get("team2", "")
            s1, s2 = score_of(m)
            hh, mi, off, tz = parse_time(m.get("time", ""))
            # openfootballにスコアが無くてもESPN(results)にあれば補完
            if s1 is None and h in NAMES and a in NAMES:
                r = results.get(pairkey(h, a))
                if r and r.get("st") == "FT":
                    s1, s2 = r.get(h), r.get(a)
            ties.append({"date": m.get("date"), "ground": m.get("ground", ""),
                         "home": h, "away": a, "hs": s1, "as": s2,
                         "h": hh, "mi": mi, "off": off, "tz": tz})
        bracket_rounds.append({"key": key, "ties": ties})

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (DATA / "bracket.json").write_text(
        json.dumps({"updatedAt": now, "rounds": bracket_rounds},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "fixtures.json").write_text(
        json.dumps({"updatedAt": now, "matches": fixtures},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "results.json").write_text(
        json.dumps({"updatedAt": now, "matches": results},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "scorers.json").write_text(
        json.dumps({"updatedAt": now, "top": top},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    # ja = RSS見出し（出典＋リンク）＋ 試合終了の自動速報、時刻降順で混在
    ja = list(fetch_rss())
    en = []
    for id1, id2, s1, s2, date in ft_news:
        t = (date or "") + "T12:00:00Z"
        ja.append({"time": t, "title": "試合終了 ⚽",
                   "body": f"{NAMES[id1][0]} {s1}-{s2} {NAMES[id2][0]}", "tag": "試合終了"})
        en.append({"time": t, "title": "Full-time ⚽",
                   "body": f"{NAMES[id1][1]} {s1}-{s2} {NAMES[id2][1]}", "tag": "FULL-TIME"})
    ja.sort(key=lambda x: x["time"], reverse=True)
    en.sort(key=lambda x: x["time"], reverse=True)
    ja, en = ja[:14], en[:12]
    (DATA / "news.json").write_text(
        json.dumps({"ja": ja, "en": en}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    print(f"fixtures={len(fixtures)} results={len(results)} "
          f"scorers={len(top)} news={len(ja)}")


if __name__ == "__main__":
    main()
