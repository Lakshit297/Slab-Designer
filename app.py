"""app.py - Streamlit web front end for the one-way slab designer."""
import streamlit as st
from calc import SlabInput, design_with_revision, report_text

st.set_page_config(page_title="One-Way Slab Designer (IS 456)", page_icon="🏗️", layout="wide")
st.title("🏗️ One-Way Slab Designer")
st.caption("Limit State Method as per IS 456:2000 | Simply supported slab | Step-by-step solution")

with st.sidebar:
    st.header("Inputs")
    if st.button("Load notebook example"):
        st.session_state.clear()
    st.subheader("Geometry")
    clear_span = st.number_input("Clear span L (m)", 0.5, 10.0, 3.5, 0.1)
    support_width = st.number_input("Wall / support thickness (m)", 0.05, 1.0, 0.20, 0.05)
    ly = st.number_input("Long span ly (m), optional (0 = skip)", 0.0, 50.0, 0.0, 0.5)
    st.subheader("Loads")
    live_load = st.number_input("Live load (kN/m²)", 0.0, 50.0, 4.0, 0.5)
    floor_finish = st.number_input("Floor finish (kN/m²)", 0.0, 10.0, 1.0, 0.25)
    st.subheader("Materials")
    fck = st.selectbox("Concrete grade fck (MPa)", [15, 20, 25, 30, 35, 40], index=1)
    fy = st.selectbox("Steel grade fy (MPa)", [250, 415, 500, 550], index=1)
    st.subheader("Detailing")
    clear_cover = st.number_input("Clear cover (mm)", 10.0, 75.0, 15.0, 5.0)
    main_dia = st.number_input("Bar dia assumed for effective cover (mm)", 6.0, 25.0, 10.0, 1.0)
    main_bar = st.selectbox("Main bar dia for spacing (mm)", [8, 10, 12, 16], index=0)
    dist_bar = st.selectbox("Distribution bar dia (mm)", [6, 8, 10, 12], index=1)
    mf = st.number_input("Assumed modification factor", 1.0, 2.0, 1.25, 0.05)
    kt_in = st.number_input("kt from IS 456 Fig. 4 (0 = auto-compute)", 0.0, 2.0, 0.0, 0.05)

inp = SlabInput(clear_span, support_width, live_load, floor_finish, fck, fy, clear_cover,
                main_dia, main_bar, dist_bar, mf, 20.0, 25.0, 1.5, kt_in, ly)

try:
    res = design_with_revision(inp)
except Exception as e:
    st.error(f"Could not complete the design: {e}")
    st.stop()

if res["ok"]:
    st.success("✅ Design is SAFE: all checks passed")
    if res.get("revisions"):
        st.warning(f"The first trial depth failed a check, so the depth was automatically increased by {res['revisions']*10} mm.")
else:
    st.error("❌ One or more checks FAILED. See details below.")

if res["summary"]:
    s = res["summary"]
    c = st.columns(4)
    c[0].metric("Overall depth D", f"{s['D (mm)']:.0f} mm")
    c[1].metric("Mu", f"{s['Mu (kN.m)']} kN·m")
    c[2].metric("Main steel", s["Main steel"])
    c[3].metric("Distribution steel", s["Distribution steel"])

st.subheader("Step-by-step solution")
for n, step in enumerate(res["steps"], 1):
    ref = f"  —  *{step['ref']}*" if step["ref"] else ""
    with st.expander(f"({n}) {step['title']}", expanded=True):
        if step["ref"]:
            st.caption(step["ref"])
        st.code("\n".join(step["lines"]), language=None)
        if step["note"]:
            st.info(step["note"])

st.subheader("Checks")
for name, ok, txt in res["checks"]:
    st.write(f"{'✅' if ok else '❌'} **{name}**: {txt}")

st.download_button("⬇️ Download solution (.txt)", report_text(inp, res),
                   file_name="one_way_slab_design.txt")
st.caption("Educational tool. Verify results and detailing against IS 456:2000 / SP 16 before use in actual design.")
