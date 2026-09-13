import json, os, urllib.request, urllib.parse, urllib.error
T=os.environ["PINTEREST_TOKEN"]; out={}
def get(path, params):
    url="https://api.pinterest.com/v5"+path+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url, headers={"Authorization":f"Bearer {T}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.status, json.load(r)
    except urllib.error.HTTPError as e: return e.code, e.read().decode(errors="ignore")[:400]
for q in ["cherry", "logo", "wedding invitation"]:
    s,d=get("/search/pins", {"query":q,"page_size":25})
    items=d.get("items",[]) if isinstance(d,dict) else []
    out[q]={"status":s,"count":len(items),"sample":[{"id":i.get("id"),"title":i.get("title"),"board":i.get("board_id"),"owner":i.get("board_owner")} for i in items[:5]] if items else d}
s,d=get("/search/partner/pins", {"term":"cherry","country_code":"US"}); out["partner"]={"status":s,"resp":str(d)[:300]}
os.makedirs("data",exist_ok=True); json.dump(out, open("data/probe.json","w"), indent=1, ensure_ascii=False); print(json.dumps(out,indent=1,ensure_ascii=False)[:3000])
