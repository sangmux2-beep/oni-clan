"""ONI 클랜 매치 기록 갱신: 클랜원 최근 14일 매치를 받아 data/matches.json 에 쌓음.
매치 상세(/matches)는 API 횟수 제한에 안 걸려서 여러 개를 동시에 받음."""
import json, os, time, urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
KEY = os.environ['PUBG_API_KEY']
H = {'Authorization': 'Bearer ' + KEY, 'Accept': 'application/vnd.api+json'}
B = 'https://api.pubg.com/shards/kakao'
PER_PLAYER = 40          # 한 사람당 최근 몇 판까지
KEEP_DAYS = 14

def get(u, sleep=6.3):
    for _ in range(6):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60))
            time.sleep(sleep); return r
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(62); continue
            if e.code == 404: return None
            time.sleep(sleep); return None
        except Exception:
            time.sleep(5)
    return None

names = [l.strip().split('|')[1] for l in open('members.txt', encoding='utf-8') if l.strip() and not l.startswith('#')]
recent, real = {}, set()
for i in range(0, len(names), 10):
    b = names[i:i+10]
    r = get(B + '/players?filter[playerNames]=' + urllib.parse.quote(','.join(b)))
    lst = r['data'] if r else []
    if not r:
        for n in b:
            rr = get(B + '/players?filter[playerNames]=' + urllib.parse.quote(n))
            if rr: lst += rr['data']
    for p in lst:
        nm = p['attributes']['name']; real.add(nm)
        recent[nm] = [m['id'] for m in p['relationships']['matches']['data']][:PER_PLAYER]

try: old = json.load(open('data/matches.json', encoding='utf-8'))['m']
except Exception: old = {}
cut = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).strftime('%Y-%m-%dT%H:%M:%SZ')
want = set(m for ms in recent.values() for m in ms)
store = {k: v for k, v in old.items() if v['t'] >= cut}
need = [m for m in want if m not in store]

def fetch(mid):
    r = get(f'{B}/matches/{mid}', sleep=0)
    if not r: return mid, None
    d = r['data']['attributes']; inc = r['included']
    parts = {x['id']: x['attributes']['stats'] for x in inc if x['type'] == 'participant'}
    rosters = [x for x in inc if x['type'] == 'roster']
    R = []
    for ro in rosters:
        ps = [parts[p['id']] for p in ro['relationships']['participants']['data'] if p['id'] in parts]
        if any(s['name'] in real for s in ps):
            R.append({'r': ro['attributes']['stats']['rank'],
                      'p': [[s['name'], s['kills'], round(s['damageDealt']), s['assists'], s['DBNOs'], round(s['timeSurvived']),
                             s['headshotKills'], s['revives'], round(s['longestKill']), 0 if s['deathType'] == 'alive' else 1]
                            for s in sorted(ps, key=lambda s: -s['damageDealt'])]})
    return mid, {'t': d['createdAt'], 'map': d['mapName'], 'mode': d['gameMode'], 'type': d['matchType'],
                 'dur': d['duration'], 'n': len(rosters), 'R': R}

with ThreadPoolExecutor(8) as ex:
    for mid, v in ex.map(fetch, need):
        if v: store[mid] = v
json.dump({'updated': datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M'), 'm': store},
          open('data/matches.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('matches', len(store), 'new', len(need), 'players', len(recent))
