import streamlit as st
import pandas as pd

# --- Load and Build Index Once ---
@st.cache_resource
def build_index():
    FILE = "/Users/parthibansrinivasan/Documents/cci_app/CCI_Edits.parquet"
    raw = pd.read_parquet(FILE, engine="pyarrow")
    raw = raw.astype(str)

    def norm(v):
        if v is None:
            return None
        s = str(v).strip()
        if s.lower() in ["nan", "none", "null", "ac", "bc", ""]:
            return None
        if s.endswith(".0"):
            s = s[:-2]
        return s

    primary_map = {}
    all_codes = set()

    for i in range(0, len(raw)-1, 2):
        p = norm(raw.iloc[i, 0])
        if not p:
            continue

        sec = [norm(x) for x in raw.iloc[i, 1:].tolist()]
        flg = pd.to_numeric(raw.iloc[i+1, 1:], errors="coerce").fillna(-1).astype(int).tolist()

        n = min(len(sec), len(flg))
        sec, flg = sec[:n], flg[:n]

        sec_map = {}
        for s, f in zip(sec, flg):
            if s is not None:
                sec_map[s] = f

        primary_map[p] = sec_map
        all_codes.add(p)
        all_codes.update(sec_map.keys())

    return primary_map, all_codes


primary_map, all_codes = build_index()


# --- Helpers ---
def norm(v):
    if v is None:
        return None
    s = str(v).strip()
    if s.lower() in ["nan", "none", "null", "ac", "bc", ""]:
        return None
    if s.endswith(".0"):
        s = s[:-2]
    return s


def check_bundle_grouped(codes):
    codes = [norm(c) for c in codes if c]
    grouped = {}

    for i in range(len(codes)):
        for j in range(i+1, len(codes)):
            a, b = codes[i], codes[j]

            bundled, no_edit = None, None

            for primary, secondary in ((a, b), (b, a)):
                if primary in primary_map and secondary in primary_map[primary]:
                    flag = primary_map[primary][secondary]
                    if flag == 1:
                        bundled = (primary, secondary)
                    elif flag == 0:
                        no_edit = (primary, secondary)
                    break

            if bundled:
                p, s = bundled
                if p not in grouped:
                    grouped[p] = {"bundled": [], "noedit": []}
                if s not in grouped[p]["bundled"]:
                    grouped[p]["bundled"].append(s)

            elif no_edit:
                p, s = no_edit
                if p not in grouped:
                    grouped[p] = {"bundled": [], "noedit": []}
                if s not in grouped[p]["noedit"]:
                    grouped[p]["noedit"].append(s)

    return grouped


# --- Streamlit UI ---
st.set_page_config(page_title="CCI Edits Checker ⚡", page_icon="🩺", layout="centered")

st.title("🩺 CCI Edits Checker ⚡")
st.caption("Enter multiple CPT codes and instantly check **bundled** vs **no edit** rules.")

codes_input = st.text_area("📌 Enter CPT codes (separated by space or comma):", "")

if st.button("🚀 Check Edits"):
    codes = [norm(c) for c in codes_input.replace(",", " ").split() if c.strip()]
    grouped = check_bundle_grouped(codes)

    if grouped:
        # --- Summary Counter ---
        total_bundled = sum(len(results["bundled"]) for results in grouped.values())
        total_noedit = sum(len(results["noedit"]) for results in grouped.values())

        st.markdown(
            f"### 📊 Summary: 🟢 {total_bundled} bundled | 🔵 {total_noedit} no-edit"
        )

        st.markdown("## 🔎 Detailed Results")

        for primary, results in grouped.items():
            bundled = results["bundled"]
            noedit = results["noedit"]

            with st.expander(f"📂 Results for {primary}", expanded=True):
                if bundled:
                    st.markdown(
                        f"🟢 **{primary}** is bundled with: "
                        + ", ".join([f"`{c}`" for c in bundled])
                    )

                if noedit:
                    st.markdown(
                        f"🔵 **{primary}** has no edit with: "
                        + ", ".join([f"`{c}`" for c in noedit])
                    )

    else:
        st.warning("⚠️ No results found for the entered codes.")
