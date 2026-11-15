from flask import Flask, jsonify, request, render_template
from datetime import datetime
import random, string, json, os

app = Flask(__name__)

@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
TYPES = ["LB", "MB", "UB", "LB", "MB", "UB", "SL", "SU"]
LOWER = {"LB", "SL"}
TOTAL = 72


def fresh():
    return {
        "config": {
            "train": "12004 - Lucknow Shatabdi Exp",
            "source": "New Delhi (NDLS)",
            "dest": "Lucknow (LKO)",
            "price": 500
        },
        "bookings": {}
    }


def load():
    for path in [DB, os.path.join(os.path.expanduser("~"), ".railway_seat_data.json")]:
        try:
            if os.path.exists(path):
                with open(path) as f:
                    data = json.load(f)
                    if "config" not in data:
                        data["config"] = fresh()["config"]
                    if "bookings" not in data:
                        data["bookings"] = {}
                    return data
        except Exception:
            continue
    return fresh()


def save():
    try:
        with open(DB, "w") as f:
            json.dump(D, f, indent=2)
    except Exception as e:
        print(f"[Warning] Could not write to primary DB ({DB}): {e}")
        try:
            alt = os.path.join(os.path.expanduser("~"), ".railway_seat_data.json")
            with open(alt, "w") as f:
                json.dump(D, f, indent=2)
        except Exception:
            pass


D = load()
kind = lambda n: TYPES[(n - 1) % 8]


def occupied():
    occ = {}
    for b in D["bookings"].values():
        if b.get("status") == "CONFIRMED":
            for p in b.get("passengers", []):
                occ[p["seat"]] = (b, p)
    return occ


def allocate(ps):
    """
    Priority-based allocation algorithm:
    1. Single passenger:
       - Age > 60: SENIOR / Age Preference (Prioritizes Lower Berth: LB/SL) -> Yellow
       - Age <= 60: FCFS / First Come First Served (Sequential free seat) -> Red
    2. Group (2+ passengers):
       - Clustered together in the same bay/compartment (8 berths).
       - Within the group, seniors (>60) get Lower Berths in that bay first.
       - Strategy: "GROUP+SENIOR" (if seniors present) or "GROUP" -> Blue (Seniors highlighted Yellow)
    """
    occ = occupied()
    free = [n for n in range(1, TOTAL + 1) if n not in occ]
    n = len(ps)
    if n > len(free):
        return None, None

    seniors = [p for p in ps if p.get("age", 0) > 60]

    # CASE 1: Single Passenger
    if n == 1:
        if seniors:
            low = [s for s in free if kind(s) in LOWER]
            chosen = low[0] if low else free[0]
            ps[0]["priority"] = "SENIOR"
            return "SENIOR", [chosen]
        ps[0]["priority"] = "FCFS"
        return "FCFS", [free[0]]

    # CASE 2: Group (2+ Passengers)
    bays = {}
    for s in free:
        bays.setdefault((s - 1) // 8, []).append(s)

    nl = lambda b: sum(kind(s) in LOWER for s in b)
    # Prefer bay that can fit all and has enough lower berths for seniors
    ok = [b for b in bays.values() if len(b) >= n and nl(b) >= len(seniors)] or \
         [b for b in bays.values() if len(b) >= n]

    if ok:
        pool = list(ok[0])
    else:
        # Cluster across bays with the highest number of free seats
        pool = []
        for b in sorted(bays.values(), key=len, reverse=True):
            pool.extend(b)
            if len(pool) >= n:
                break

    lows = [s for s in pool if kind(s) in LOWER] + \
           [s for s in free if kind(s) in LOWER and s not in pool]

    res = [None] * n
    used = set()

    # Assign Lower Berths to seniors first
    for i, p in enumerate(ps):
        if p.get("age", 0) > 60:
            s = next((x for x in lows if x not in used), None)
            if s is None:
                s = next((x for x in pool if x not in used), None)
            if s is None:
                s = next(x for x in free if x not in used)
            res[i] = s
            used.add(s)
            p["priority"] = "GROUP+SENIOR"
        else:
            p["priority"] = "GROUP"

    # Fill remaining group members
    rest = [x for x in pool if x not in used] + [x for x in free if x not in used]
    for i in range(n):
        if res[i] is None:
            seat_picked = rest.pop(0)
            res[i] = seat_picked
            used.add(seat_picked)

    strategy_name = "GROUP+SENIOR" if seniors else "GROUP"
    return strategy_name, res


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def state():
    occ = occupied()
    c = D["config"]
    seats = []
    
    fcfs_cnt = 0
    group_cnt = 0
    senior_cnt = 0

    for n in range(1, TOTAL + 1):
        o = None
        if n in occ:
            b, p = occ[n]
            prio = p.get("priority")
            if not prio:
                if b.get("strategy") == "SENIOR" or p.get("age", 0) > 60:
                    prio = "SENIOR"
                elif "GROUP" in b.get("strategy", ""):
                    prio = "GROUP+SENIOR" if p.get("age", 0) > 60 else "GROUP"
                else:
                    prio = "FCFS"

            if prio == "FCFS":
                fcfs_cnt += 1
            elif prio in ("SENIOR", "GROUP+SENIOR"):
                senior_cnt += 1
                if prio == "GROUP+SENIOR":
                    group_cnt += 1
            elif prio == "GROUP":
                group_cnt += 1

            o = {
                "pnr": b.get("pnr"),
                "name": p.get("name"),
                "age": p.get("age"),
                "gender": p.get("gender", "Male"),
                "strategy": b.get("strategy"),
                "priority": prio,
                "section": "B",  # Section B: Allotted
                "time": b.get("time"),
                "price": b.get("price", c["price"]),
                "source": b.get("source", c["source"]),
                "dest": b.get("dest", c["dest"]),
                "train": b.get("train", c["train"])
            }

        seats.append({
            "n": n,
            "bay": (n - 1) // 8 + 1,
            "type": kind(n),
            "is_lower": kind(n) in LOWER,
            "section": "B" if o else "A",  # Section A = Available, Section B = Allotted
            "priority": o["priority"] if o else "AVAILABLE",
            "occ": o
        })

    bk = sorted(D["bookings"].values(), key=lambda b: b.get("time", ""), reverse=True)
    free_cnt = len([s for s in seats if not s["occ"]])
    booked_cnt = len(seats) - free_cnt

    stats = {
        "total_seats": TOTAL,
        "available_seats": free_cnt,
        "allotted_seats": booked_cnt,
        "fcfs_count": fcfs_cnt,
        "group_count": group_cnt,
        "senior_count": senior_cnt
    }

    return jsonify({"config": c, "seats": seats, "bookings": bk, "stats": stats})


@app.route("/api/config", methods=["GET", "POST"])
def config():
    if request.method == "POST":
        d = request.json or {}
        source = str(d.get("source", "")).strip()
        dest = str(d.get("dest", "")).strip()
        train = str(d.get("train", "")).strip()

        try:
            price = float(d.get("price", 0))
        except Exception:
            price = 0

        # Forgiving defaults so confirmation never fails
        if price <= 0:
            price = D["config"].get("price") or 500
        if not source:
            source = D["config"].get("source") or "New Delhi (NDLS)"
        if not dest:
            dest = D["config"].get("dest") or "Lucknow (LKO)"
        if not train:
            train = D["config"].get("train") or "12004 - Lucknow Shatabdi Exp"

        D["config"].update(source=source, dest=dest, price=price, train=train)
        save()
        return jsonify(ok=True, message=f"Journey confirmed: {source} ➔ {dest} (₹{int(price)}/seat)", config=D["config"])
    return jsonify(config=D["config"])


@app.route("/api/book", methods=["POST"])
def book():
    payload = request.json or {}
    c = D["config"]

    # If source/dest provided in booking request, confirm/update route automatically
    req_src = str(payload.get("source", "")).strip()
    req_dst = str(payload.get("dest", "")).strip()
    if req_src:
        c["source"] = req_src
    if req_dst:
        c["dest"] = req_dst
    if not c.get("source"):
        c["source"] = "New Delhi (NDLS)"
    if not c.get("dest"):
        c["dest"] = "Lucknow (LKO)"
    try:
        req_prc = float(payload.get("price", 0))
        if req_prc > 0:
            c["price"] = req_prc
    except Exception:
        pass
    if not c.get("price") or c["price"] <= 0:
        c["price"] = 500
    save()

    raw_passengers = payload.get("passengers", [])
    if not raw_passengers:
        return jsonify(error="Please enter at least one passenger details before confirming."), 400

    ps = []
    for i, p in enumerate(raw_passengers):
        name = str(p.get("name", "")).strip()
        if not name:
            name = f"Passenger {i + 1}"

        raw_age = p.get("age")
        try:
            age = int(raw_age) if raw_age not in (None, "") else 28
        except Exception:
            age = 28
        if age < 1:
            age = 1
        elif age > 120:
            age = 120

        gender = str(p.get("gender", "Male")).strip() or "Male"
        pref = str(p.get("preference", "No Preference")).strip()
        ps.append({"name": name, "age": age, "gender": gender, "preference": pref})

    strat, seats = allocate(ps)
    if strat is None:
        return jsonify(error="Not enough free berths available in Coach S1 for this booking."), 400

    for p, s in zip(ps, seats):
        p["seat"] = s
        p["type"] = kind(s)
        p["bay"] = (s - 1) // 8 + 1

    pnr = "PNR-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    booking_record = {
        "pnr": pnr,
        "strategy": strat,
        "status": "CONFIRMED",
        "time": datetime.now().isoformat(),
        "source": c["source"],
        "dest": c["dest"],
        "train": c.get("train", "12004 - Lucknow Shatabdi Exp"),
        "price": c["price"],
        "total": c["price"] * len(ps),
        "passengers": ps
    }

    D["bookings"][pnr] = booking_record
    save()

    return jsonify(
        ok=True,
        pnr=pnr,
        strategy=strat,
        seats=seats,
        passengers=ps,
        booking=booking_record,
        message=f"Booking Confirmed! PNR: {pnr} ({strat})"
    )


@app.route("/api/cancel", methods=["POST"])
def cancel():
    pnr = (request.json or {}).get("pnr")
    b = D["bookings"].get(pnr)
    if not b or b["status"] != "CONFIRMED":
        return jsonify(error="Booking not found or already cancelled"), 400
    b["status"] = "CANCELLED"
    save()
    return jsonify(ok=True, message=f"Booking {pnr} cancelled. Seats freed back to Section A (Available).")


@app.route("/api/swap", methods=["POST"])
def swap():
    data = request.json or {}
    try:
        a = int(data.get("a", 0))
        t = int(data.get("b", 0))
    except Exception:
        return jsonify(error="Invalid seat numbers provided for swap"), 400

    occ = occupied()
    if a == t or a not in occ:
        return jsonify(error="Pick an allotted source seat and a different target seat"), 400

    b_a, pa = occ[a]
    if t in occ:
        b_t, pt = occ[t]
        pt["seat"] = a
        pt["type"] = kind(a)
        pt["bay"] = (a - 1) // 8 + 1

    pa["seat"] = t
    pa["type"] = kind(t)
    pa["bay"] = (t - 1) // 8 + 1
    save()
    return jsonify(ok=True, message=f"Successfully swapped Seat #{a} with Seat #{t}")


@app.route("/api/reset", methods=["POST"])
def reset():
    global D
    D = fresh()
    save()
    return jsonify(ok=True, message="System reset complete. All 72 berths are now Available in Section A.")


if __name__ == "__main__":
    app.run(debug=True, port=5000)

