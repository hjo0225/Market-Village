"""Self-test the canonical live stack end-to-end against the running servers,
using the EVENT-DRIVEN flow (start forks only; event injects then runs a day).

Mimics the frontend ReverieGame loop (process -> update -> execute) and asserts
the full round: agents walk -> board posts (view_sns) -> exchange trade -> day
boundary price distortion + round report.

Run with api_server:8000 + control_server:8001 up (control ideally MARKET_STUB_LLM=1).
    python backend/tools/drive_live.py
"""
import json
import time
import urllib.request

API = "http://127.0.0.1:8000"
CTRL = "http://127.0.0.1:8000"
STEPS = 1300  # > one in-game day (1200) so we cross midnight -> end_round


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def get(url):
    return json.load(urllib.request.urlopen(url, timeout=60))


def snap():
    return get(f"{CTRL}/control/market/state")


def main():
    sim = "market_drive_%d" % int(time.time())
    print("start:", post(f"{CTRL}/control/start",
                         {"fork_sim_code": "base_the_ville_market6", "sim_code": sim}))

    s0 = snap()
    cash0 = {a["alias"]: a["cash"] for a in s0.get("agents", [])}
    price0 = {a["symbol"]: a["price"] for a in s0.get("market", {}).get("assets", [])}
    print(f"pre-event: ready={s0.get('ready')} round={s0.get('round')} posts={len(s0.get('posts', []))}")

    print("event:", post(f"{CTRL}/control/market/event",
                        {"text": "대형 거래소 해킹 루머가 퍼졌다", "is_rumor": True}))
    print("run:", post(f"{CTRL}/control/run", {"count": STEPS}))

    home = get(f"{API}/api/home")
    names = [p["original"] for p in home["persona_names"]]
    pos = {n: {"maze": "the_ville", "x": x, "y": y} for n, x, y in home["persona_init_pos"]}

    first_post_step = first_trade_step = round_end_step = None
    last_round = s0.get("round", 0)

    for step in range(STEPS):
        post(f"{API}/api/environment/process", {"step": step, "sim_code": sim, "environment": pos})
        mv = None
        for _ in range(200):
            r = post(f"{API}/api/environment/update", {"step": step, "sim_code": sim})
            if r.get("<step>") == step:
                mv = r
                break
            time.sleep(0.02)
        if mv is None:
            print(f"step {step}: timed out (run may have ended)")
            break
        for n in names:
            m = mv["persona"][n]["movement"]
            pos[n] = {"maze": "the_ville", "x": m[0], "y": m[1]}
        meta = mv.get("meta", {})
        posts = meta.get("posts", [])
        if first_post_step is None and len([p for p in posts if p.get("agentId") != "system"]) > 0:
            first_post_step = step
        if step % 150 == 0:
            mk = meta.get("market", {})
            print(f"step {step} time={meta.get('curr_time')} round={meta.get('round')} "
                  f"posts={len(posts)} fgi={round(mk.get('fearGreedIndex', 0), 1)}")

    # final snapshot + assertions
    sN = snap()
    cashN = {a["alias"]: a["cash"] for a in sN.get("agents", [])}
    priceN = {a["symbol"]: a["price"] for a in sN.get("market", {}).get("assets", [])}
    postsN = sN.get("posts", [])
    traded = [n for n in cash0 if abs(cashN.get(n, cash0[n]) - cash0[n]) > 1e-6]
    moved_price = [s for s in price0 if abs(priceN.get(s, price0[s]) - price0[s]) > 1e-6]

    print("\n==== RESULT ====")
    print(f"posts (board view_sns):   {len(postsN)}  -> {'PASS' if len(postsN) > 1 else 'FAIL'}")
    print(f"agents that traded:       {len(traded)} {traded}  -> {'PASS' if traded else 'FAIL (no trade yet)'}")
    print(f"assets w/ price change:   {len(moved_price)}  -> {'PASS' if moved_price else 'FAIL (no round-end price yet)'}")
    print(f"round:                    {sN.get('round')}")
    for p in postsN[:8]:
        print("   post:", p.get("agentAlias"), ":", (p.get("content") or "")[:36])
    print("exit:", post(f"{CTRL}/control/finish", {}))


if __name__ == "__main__":
    main()
