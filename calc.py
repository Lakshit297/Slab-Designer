"""
calc.py - Calculation engine: design of a simply supported ONE-WAY SLAB
as per IS 456:2000 (Limit State Method).

The engine is pure Python (no web code) so it can be unit-tested and re-used
in any front end (Streamlit, Flask, CLI ...).
"""
import math
from dataclasses import dataclass

# ----------------------------------------------------------------- IS 456 data
# Table 20 : maximum shear stress tau_c,max (N/mm2)
TAU_C_MAX = {15: 2.5, 20: 2.8, 25: 3.1, 30: 3.5, 35: 3.7, 40: 4.0}

# Table 19 : design shear strength tau_c (N/mm2) vs pt (%)
PT_TABLE = [0.15, 0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 1.75, 2.00, 2.25, 2.50, 2.75, 3.00]
TAU_C = {
    15: [0.28, 0.35, 0.46, 0.54, 0.60, 0.64, 0.68, 0.71, 0.71, 0.71, 0.71, 0.71, 0.71],
    20: [0.28, 0.36, 0.48, 0.56, 0.62, 0.67, 0.72, 0.75, 0.79, 0.81, 0.82, 0.82, 0.82],
    25: [0.29, 0.36, 0.49, 0.57, 0.64, 0.70, 0.74, 0.78, 0.82, 0.85, 0.88, 0.90, 0.92],
    30: [0.29, 0.37, 0.50, 0.59, 0.66, 0.71, 0.76, 0.80, 0.84, 0.88, 0.91, 0.94, 0.96],
    35: [0.29, 0.37, 0.50, 0.59, 0.67, 0.73, 0.78, 0.82, 0.86, 0.90, 0.93, 0.96, 0.99],
    40: [0.30, 0.38, 0.51, 0.60, 0.68, 0.74, 0.79, 0.84, 0.88, 0.92, 0.95, 0.98, 1.01],
}
# Cl. 38.1 : xu,max/d for each steel grade
XU_MAX_D = {250: 0.53, 415: 0.48, 500: 0.46, 550: 0.44}

# Cl. 40.2.1.1 : slab shear enhancement factor k  (overall depth D, mm)
K_SLAB = [(150, 1.30), (175, 1.25), (200, 1.20), (225, 1.15), (250, 1.10), (275, 1.05), (300, 1.00)]


def interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            return ys[i] + (ys[i + 1] - ys[i]) * (x - xs[i]) / (xs[i + 1] - xs[i])


def tau_c_table19(pt, fck):
    return interp(pt, PT_TABLE, TAU_C[fck])


def k_factor(D):
    return interp(D, [p[0] for p in K_SLAB], [p[1] for p in K_SLAB])


def round_up(x, m=10):
    return math.ceil(round(x / m, 9)) * m


def round_down(x, m=10):
    return math.floor(round(x / m, 9)) * m


@dataclass
class SlabInput:
    clear_span: float = 3.5        # m
    support_width: float = 0.20    # m  (wall thickness)
    live_load: float = 4.0         # kN/m2
    floor_finish: float = 1.0      # kN/m2
    fck: int = 20                  # MPa
    fy: int = 415                  # MPa
    clear_cover: float = 15.0      # mm
    main_dia: float = 10.0         # mm (assumed for effective cover)
    main_bar_dia: float = 8.0      # mm (bar used for spacing)
    dist_bar_dia: float = 8.0      # mm
    mod_factor: float = 1.25       # assumed modification factor for depth
    basic_ld: float = 20.0         # simply supported (Cl. 23.2.1)
    unit_weight: float = 25.0      # kN/m3 (reinforced concrete)
    load_factor: float = 1.5
    kt_override: float = 0.0       # 0 = compute; otherwise value read from Fig. 4
    ly: float = 0.0                # m, optional long span, to confirm one-way action


def _ast_bar(dia):
    return math.pi / 4 * dia ** 2


def design_one_way_slab(i: SlabInput, extra_d: float = 0.0) -> dict:
    if i.fck not in TAU_C:
        raise ValueError("fck must be one of 15, 20, 25, 30, 35, 40")
    if i.fy not in XU_MAX_D:
        raise ValueError("fy must be one of 250, 415, 500, 550")

    steps, checks, b = [], [], 1000.0
    L = i.clear_span * 1000

    def add(title, ref, lines, note=""):
        steps.append({"title": title, "ref": ref, "lines": lines, "note": note})

    # 0 ---- type of slab
    if i.ly > 0:
        r = i.ly / i.clear_span
        ok = r > 2
        add("Type of slab", "IS 456 Cl. 24.1",
            [f"ly/lx = {i.ly:g}/{i.clear_span:g} = {r:.2f}",
             "ly/lx > 2  ->  one-way slab" if ok else "ly/lx <= 2  ->  TWO-WAY slab (this module designs one-way only)"])
        checks.append(("One-way action (ly/lx > 2)", ok, f"ly/lx = {r:.2f}"))

    # 1 ---- depth from deflection
    d_raw = L / (i.mod_factor * i.basic_ld)
    d_calc = round_up(d_raw, 10) + extra_d
    add("Depth of slab (deflection control)", "IS 456 Cl. 23.2.1",
        [f"L/d = (M.F.) x (basic value) = {i.mod_factor:g} x {i.basic_ld:g} = {i.mod_factor*i.basic_ld:g}",
         f"d = {L:.0f} / {i.mod_factor*i.basic_ld:g} = {d_raw:.2f} mm  ->  adopt d = {d_calc:.0f} mm"
         + (f"  (after {extra_d/10:.0f} automatic revision(s) of +10 mm)" if extra_d else "")],
        "Modification factor is an assumption here; it is verified in the deflection check below."
        + (" The first trial depth failed a check, so the depth was increased until all checks passed." if extra_d else ""))

    # 2 ---- overall depth
    ce = i.clear_cover + i.main_dia / 2
    D = round_up(d_calc + ce, 10)
    d = D - ce
    add("Overall depth", "",
        [f"Effective cover = clear cover + dia/2 = {i.clear_cover:g} + {i.main_dia:g}/2 = {ce:g} mm",
         f"D = d + effective cover = {d_calc:.0f} + {ce:g} = {d_calc+ce:g} mm  ->  adopt D = {D:.0f} mm",
         f"Effective depth used in design: d = {d:.0f} mm"])

    # 3 ---- loads
    w_self = D / 1000 * i.unit_weight
    w = w_self + i.live_load + i.floor_finish
    wu = i.load_factor * w
    add("Load calculation (per 1 m strip)", "IS 875 / IS 456 Cl. 18.2",
        [f"Self weight = {D/1000:.3f} x {i.unit_weight:g} = {w_self:.2f} kN/m2",
         f"Live load = {i.live_load:g} kN/m2 ,  Floor finish = {i.floor_finish:g} kN/m2",
         f"Total working load w = {w_self:.2f} + {i.live_load:g} + {i.floor_finish:g} = {w:.2f} kN/m2",
         f"Design load wu = {i.load_factor:g} x {w:.2f} = {wu:.2f} kN/m2"])

    # 4 ---- effective span
    cc = i.clear_span + i.support_width
    l1 = i.clear_span + d / 1000
    leff = min(l1, cc)
    add("Effective span", "IS 456 Cl. 22.2",
        [f"L + d = {i.clear_span:g} + {d/1000:.3f} = {l1:.3f} m",
         f"c/c distance between supports = {i.clear_span:g} + {i.support_width:g} = {cc:.3f} m",
         f"Leff = min({l1:.3f}, {cc:.3f}) = {leff:.3f} m"])

    # 5 ---- BM & SF
    Mu = wu * leff ** 2 / 8
    Vu = wu * leff / 2
    add("Design bending moment and shear force", "",
        [f"Mu = wu.L^2 / 8 = {wu:.2f} x {leff:.3f}^2 / 8 = {Mu:.2f} kN.m",
         f"Vu = wu.L / 2 = {wu:.2f} x {leff:.3f} / 2 = {Vu:.2f} kN"])

    # 6 ---- required depth
    xk = XU_MAX_D[i.fy]
    Q = 0.36 * xk * (1 - 0.42 * xk)
    d_req = math.sqrt(Mu * 1e6 / (Q * i.fck * b))
    ok = d >= d_req
    add("Required depth for flexure (check)", "IS 456 Annex G, Cl. 38.1",
        [f"xu,max/d = {xk} for Fe{i.fy}  ->  Mu,lim = {Q:.4f} fck b d^2",
         f"d_req = sqrt( Mu / ({Q:.3f} fck b) ) = sqrt( {Mu*1e6:.3g} / ({Q:.3f} x {i.fck} x {b:.0f}) ) = {d_req:.2f} mm",
         f"d provided = {d:.0f} mm {'>' if ok else '<'} d_req  ->  {'SAFE, singly reinforced section' if ok else 'NOT SAFE, increase depth'}"])
    checks.append(("Depth adequate for flexure (d >= d_req)", ok, f"{d:.0f} mm vs {d_req:.1f} mm"))
    if not ok:
        return {"ok": False, "steps": steps, "checks": checks, "summary": {}}

    # 7 ---- Ast
    term = 4.6 * Mu * 1e6 / (i.fck * b * d ** 2)
    Ast_calc = 0.5 * i.fck / i.fy * (1 - math.sqrt(1 - term)) * b * d
    add("Area of tension steel", "IS 456 Annex G-1.1(b)",
        ["Ast = (0.5 fck/fy) [1 - sqrt(1 - 4.6 Mu/(fck b d^2))] b d",
         f"     = (0.5 x {i.fck}/{i.fy}) [1 - sqrt(1 - {term:.4f})] x {b:.0f} x {d:.0f}",
         f"Ast = {Ast_calc:.2f} mm2"])

    # 8 ---- min steel
    pmin = 0.15 if i.fy < 415 else 0.12
    Ast_min = pmin / 100 * b * D
    add("Minimum tension steel", "IS 456 Cl. 26.5.2.1",
        [f"Ast,min = {pmin}% of gross area = ({pmin}/100) x {b:.0f} x {D:.0f} = {Ast_min:.0f} mm2"])
    Ast = max(Ast_calc, Ast_min)

    # 9 ---- spacing main
    a1 = _ast_bar(i.main_bar_dia)
    sp_calc = a1 / Ast * b
    sp_max = min(3 * d, 300)
    sp = min(round_down(sp_calc, 10), sp_max)
    Ast_prov = a1 * b / sp
    add("Main reinforcement spacing", "IS 456 Cl. 26.3.3(b)",
        [f"Area of one {i.main_bar_dia:g} mm bar = {a1:.2f} mm2",
         f"Spacing = ast/Ast x 1000 = {a1:.2f}/{Ast:.2f} x 1000 = {sp_calc:.2f} mm",
         f"Max spacing = min(3d, 300) = min({3*d:.0f}, 300) = {sp_max:.0f} mm",
         f"Provide {i.main_bar_dia:g} mm dia @ {sp:.0f} mm c/c   (Ast provided = {Ast_prov:.1f} mm2)"],
        "Spacing is rounded DOWN to a practical multiple of 10 mm.")

    # 10 ---- distribution
    Ast_d = pmin / 100 * b * D
    a2 = _ast_bar(i.dist_bar_dia)
    spd_calc = a2 / Ast_d * b
    spd_max = min(5 * d, 450)
    spd = min(round_down(spd_calc, 10), spd_max)
    add("Distribution reinforcement", "IS 456 Cl. 26.5.2.1, 26.3.3(b)",
        [f"Ast,dist = {pmin}% of bD = {Ast_d:.0f} mm2",
         f"Spacing = {a2:.2f}/{Ast_d:.0f} x 1000 = {spd_calc:.1f} mm",
         f"Max spacing = min(5d, 450) = min({5*d:.0f}, 450) = {spd_max:.0f} mm",
         f"Provide {i.dist_bar_dia:g} mm dia @ {spd:.0f} mm c/c"])

    # 11 ---- deflection
    pt = 100 * Ast_prov / (b * d)
    fs = 0.58 * i.fy * Ast / Ast_prov
    if i.kt_override > 0:
        kt = i.kt_override
        src = "value read from IS 456 Fig. 4 (user input)"
    else:
        kt = min(2.0, 1 / (0.225 + 0.00322 * fs + 0.625 * math.log10(pt)))
        src = "curve-fit of IS 456 Fig. 4 (approximate)"
    ld_act = leff * 1000 / d
    ld_max = kt * i.basic_ld
    ok = ld_act <= ld_max
    add("Check for deflection", "IS 456 Cl. 23.2.1, Fig. 4",
        [f"pt = 100 Ast,prov/(b d) = {pt:.3f} %",
         f"fs = 0.58 fy (Ast,req/Ast,prov) = 0.58 x {i.fy} x {Ast:.1f}/{Ast_prov:.1f} = {fs:.1f} N/mm2",
         f"kt = {kt:.2f}  [{src}]",
         f"(L/d) max = kt x {i.basic_ld:g} = {ld_max:.2f}",
         f"(L/d) actual = {leff*1000:.0f}/{d:.0f} = {ld_act:.2f}  {'<=' if ok else '>'} (L/d) max  ->  {'SAFE' if ok else 'NOT SAFE'}"])
    checks.append(("Deflection (L/d actual <= L/d max)", ok, f"{ld_act:.2f} vs {ld_max:.2f}"))

    # 12 ---- shear
    tv = Vu * 1e3 / (b * d)
    tcmax = TAU_C_MAX[i.fck]
    tc = tau_c_table19(pt, i.fck)
    k = k_factor(D)
    ktc = k * tc
    ok1, ok2 = tv <= tcmax, tv <= ktc
    add("Check for shear", "IS 456 Cl. 40.1, Table 19, Table 20, Cl. 40.2.1.1",
        [f"tau_v = Vu/(b d) = {Vu*1e3:.0f}/({b:.0f} x {d:.0f}) = {tv:.3f} N/mm2",
         f"tau_c,max (M{i.fck}) = {tcmax} N/mm2   ->  tau_v {'<' if ok1 else '>'} tau_c,max",
         f"pt = {pt:.3f} %  ->  tau_c (Table 19, interpolated) = {tc:.3f} N/mm2",
         f"Slab factor k (D = {D:.0f} mm) = {k:.3f}  ->  k.tau_c = {ktc:.3f} N/mm2",
         f"tau_v {'<' if ok2 else '>'} k.tau_c  ->  {'SAFE in shear, no shear reinforcement needed' if ok2 else 'NOT SAFE, increase depth'}"],
        "Ast provided is used for pt (more accurate than Ast required).")
    checks.append(("Shear (tau_v <= k.tau_c)", ok2, f"{tv:.3f} vs {ktc:.3f} N/mm2"))
    checks.append(("Max shear (tau_v <= tau_c,max)", ok1, f"{tv:.3f} vs {tcmax} N/mm2"))

    summary = {
        "D (mm)": D, "d (mm)": d, "wu (kN/m2)": round(wu, 2), "Leff (m)": round(leff, 3),
        "Mu (kN.m)": round(Mu, 2), "Vu (kN)": round(Vu, 2),
        "Ast required (mm2)": round(Ast_calc, 1), "Ast min (mm2)": round(Ast_min, 1),
        "Main steel": f"{i.main_bar_dia:g} mm dia @ {sp:.0f} mm c/c",
        "Distribution steel": f"{i.dist_bar_dia:g} mm dia @ {spd:.0f} mm c/c",
    }
    return {"ok": all(c[1] for c in checks), "steps": steps, "checks": checks, "summary": summary}


def design_with_revision(i: SlabInput, max_revisions: int = 40) -> dict:
    """Design; if any check fails, increase depth in 10 mm steps until all pass."""
    res = None
    for n in range(max_revisions + 1):
        res = design_one_way_slab(i, extra_d=10.0 * n)
        if res["ok"]:
            res["revisions"] = n
            return res
    res["revisions"] = max_revisions
    return res


def report_text(inp: SlabInput, res: dict) -> str:
    out = ["DESIGN OF ONE-WAY SLAB (IS 456:2000, Limit State Method)", "=" * 60]
    out.append(f"Given: clear span {inp.clear_span} m, wall {inp.support_width*1000:.0f} mm, LL {inp.live_load} kN/m2, "
               f"floor finish {inp.floor_finish} kN/m2, M{inp.fck}, Fe{inp.fy}")
    for n, s in enumerate(res["steps"], 1):
        out += ["", f"({n}) {s['title']}" + (f"   [{s['ref']}]" if s["ref"] else "")]
        out += ["    " + l for l in s["lines"]]
        if s["note"]:
            out.append("    Note: " + s["note"])
    out += ["", "CHECKS"] + [f"  [{'OK' if ok else 'FAIL'}] {n}: {t}" for n, ok, t in res["checks"]]
    out += ["", "FINAL DESIGN"] + [f"  {k}: {v}" for k, v in res["summary"].items()]
    return "\n".join(out)


if __name__ == "__main__":
    inp = SlabInput()
    print(report_text(inp, design_with_revision(inp)))
