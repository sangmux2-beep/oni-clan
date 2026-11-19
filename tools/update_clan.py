"""ONI 클랜 전적 갱신: members.txt 명단으로 카카오 서버 시즌 전적을 받아 data/clan.json 생성."""
import json, os, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone, timedelta
KEY = os.environ['PUBG_API_KEY']
H = {'Authorization': 'Bearer ' + KEY, 'Accept': 'application/vnd.api+json'}
B = 'https://api.pubg.com/shards/kakao'
def get(u):
    for _ in range(6):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60)); time.sleep(6.3); return r
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(62); continue
            time.sleep(6.3); return None
        except Exception:
            time.sleep(10)
    return None
TK = {'Bronze':'브론즈','Silver':'실버','Gold':'골드','Platinum':'플래티넘','Crystal':'크리스탈','Diamond':'다이아','Master':'마스터','Survivor':'서바이버','Unranked':'언랭'}
mem = [l.strip().split('|')[:2] for l in open('members.txt', encoding='utf-8') if l.strip() and not l.startswith('#')]
names = [n for _, n in mem]
ids = {}
for i in range(0, len(names), 10):
    b = names[i:i+10]
    r = get(B + '/players?filter[playerNames]=' + urllib.parse.quote(','.join(b)))
    if r:
        for p in r['data']: ids[p['attributes']['name']] = p['id']
    else:
        for n in b:
            rr = get(B + '/players?filter[playerNames]=' + urllib.parse.quote(n))
            if rr: ids[rr['data'][0]['attributes']['name']] = rr['data'][0]['id']
cur = [s for s in get(B + '/seasons')['data'] if s['attributes']['isCurrentSeason']][0]['id']
pl = [ids[n] for n in names if n in ids]
normal = {}
for mode in ['squad', 'squad-fpp']:
    for i in range(0, len(pl), 10):
        r = get(f"{B}/seasons/{cur}/gameMode/{mode}/players?filter[playerIds]=" + ','.join(pl[i:i+10]))
        if r:
            for d in r['data']:
                normal.setdefault(d['relationships']['player']['data']['id'], {})[mode] = d['attributes']['gameModeStats'][mode]
ranked = {}
for p in pl:
    r = get(f"{B}/players/{p}/seasons/{cur}/ranked")
    if r: ranked[p] = r['data']['attributes']['rankedGameModeStats']
rows = []
for c, n in mem:
    p = ids.get(n); row = {'c': int(c), 'n': n, 'ok': bool(p)}
    if p:
        rk = (ranked.get(p) or {}).get('squad') or {}
        if rk.get('roundsPlayed'):
            t = rk['currentTier']
            row['rk'] = {'tier': TK.get(t['tier'], t['tier']) + (' ' + t['subTier'] if t['tier'] not in ('Master', 'Survivor') else ''), 'tierEn': t['tier'],
                         'rp': rk['currentRankPoint'], 'g': rk['roundsPlayed'], 'avgRank': round(rk['avgRank'], 1), 'win': round(rk['winRatio']*100, 1),
                         'top10': round(rk['top10Ratio']*100), 'kd': round(rk['kills']/max(rk['deaths'], 1), 2), 'dmg': round(rk['damageDealt']/rk['roundsPlayed']), 'best': TK.get(rk['bestTier']['tier'], '') + ' ' + rk['bestTier']['subTier'], 'bestRp': rk['bestRankPoint'],
                         'kills': rk['kills'], 'deaths': rk['deaths'], 'wins': rk['wins'], 'assists': rk['assists'], 'dbno': rk['dBNOs'], 'hs': round(rk['headshotKillRatio']*100), 'revives': rk['revives'], 'surv': round(rk['avgSurvivalTime']/60, 1)}
        best = None
        for m in ['squad', 'squad-fpp']:
            st = (normal.get(p) or {}).get(m) or {}
            if st.get('roundsPlayed') and (not best or st['roundsPlayed'] > best[1]['roundsPlayed']): best = (m, st)
        if best:
            m, st = best; g = st['roundsPlayed']
            row['nm'] = {'g': g, 'kd': round(st['kills']/max(st['losses'], 1), 2), 'dmg': round(st['damageDealt']/g), 'win': round(st['wins']/g*100, 1),
                         'top10': round(st['top10s']/g*100), 'hs': round(st['headshotKills']/max(st['kills'], 1)*100),
                         'mode': '3인칭' if m == 'squad' else '1인칭', 'kills': st['kills'], 'wins': st['wins'], 'assists': st['assists'], 'dbno': st['dBNOs'], 'long': round(st['longestKill']),
                         'most': st['roundMostKills'], 'revives': st['revives'], 'surv': round(st['timeSurvived']/g/60, 1)}
    rows.append(row)
now = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')
json.dump({'season': cur.split('-')[-1], 'updated': now, 'rows': rows}, open('data/clan.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('ok', len(rows), 'found', len(pl), 'missing', [n for n in names if n not in ids])
