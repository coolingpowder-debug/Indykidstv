import json
import re
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="ทีวีฟรี การ์ตูน & สารคดี", page_icon="📺", layout="wide")

DATA_FILE = Path("channels.json")
CATEGORIES = ["การ์ตูนเด็ก", "สารคดี"]

# ตัวอย่างเริ่มต้น (เปลี่ยน/เพิ่มเองได้ในแอพ หรือแก้ไฟล์ channels.json)
# ใช้เฉพาะแหล่งที่เผยแพร่ถูกลิขสิทธิ์: ช่อง YouTube ทางการ, Internet Archive (สาธารณสมบัติ), สตรีม HLS ฟรีที่เจ้าของอนุญาต
DEFAULTS = [
    {
        "name": "Popeye for President (สาธารณสมบัติ)",
        "category": "การ์ตูนเด็ก",
        "url": "https://archive.org/details/Popeye_forPresident",
    },
    {
        "name": "NASA Live (ถ่ายทอดสด)",
        "category": "สารคดี",
        "url": "https://www.youtube.com/watch?v=21X5lGlDOfg",
    },
]


def load_channels():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return list(DEFAULTS)


def save_channels(items):
    DATA_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def render_player(url: str):
    """แปลงลิงก์เป็นตัวเล่น: YouTube / Internet Archive / HLS (.m3u8) / ไฟล์วิดีโอ"""
    u = url.strip()

    # YouTube (วิดีโอ หรือ เพลย์ลิสต์)
    m = re.search(r"(?:v=|youtu\.be/|embed/)([\w-]{11})", u)
    pl = re.search(r"list=([\w-]+)", u)
    if "youtube.com" in u or "youtu.be" in u:
        if m:
            src = f"https://www.youtube.com/embed/{m.group(1)}?rel=0"
        elif pl:
            src = f"https://www.youtube.com/embed/videoseries?list={pl.group(1)}"
        else:
            st.warning("อ่านลิงก์ YouTube ไม่ได้")
            return
        components.html(
            f'<iframe width="100%" height="480" src="{src}" frameborder="0" '
            f'allow="accelerometer; autoplay; encrypted-media; picture-in-picture" '
            f'allowfullscreen></iframe>',
            height=490,
        )
        return

    # Internet Archive
    m = re.search(r"archive\.org/(?:details|embed)/([^/?#]+)", u)
    if m:
        components.html(
            f'<iframe src="https://archive.org/embed/{m.group(1)}" width="100%" '
            f'height="480" frameborder="0" allowfullscreen></iframe>',
            height=490,
        )
        return

    # HLS live stream
    if u.split("?")[0].endswith(".m3u8"):
        components.html(
            f"""
            <video id="v" controls autoplay style="width:100%;max-height:480px;background:#000"></video>
            <script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.17"></script>
            <script>
              var v = document.getElementById('v'), s = "{u}";
              if (v.canPlayType('application/vnd.apple.mpegurl')) {{ v.src = s; }}
              else if (Hls.isSupported()) {{ var h = new Hls(); h.loadSource(s); h.attachMedia(v); }}
            </script>
            """,
            height=490,
        )
        return

    # ไฟล์วิดีโอตรง
    if u.split("?")[0].lower().endswith((".mp4", ".webm", ".ogg")):
        st.video(u)
        return

    st.info("ลิงก์รูปแบบนี้ยังไม่รองรับการฝัง")
    st.link_button("เปิดในแท็บใหม่", u)


# ---------------- UI ----------------
if "channels" not in st.session_state:
    st.session_state.channels = load_channels()
if "current" not in st.session_state:
    st.session_state.current = 0

st.title("📺 ทีวีฟรี: การ์ตูนเด็ก & สารคดี")

with st.sidebar:
    st.header("เลือกรายการ")
    cat = st.radio("หมวดหมู่", ["ทั้งหมด"] + CATEGORIES)
    q = st.text_input("ค้นหา")

    kid_mode = st.toggle("🧒 โหมดเด็ก (ซ่อนการจัดการ)", value=False)

    if not kid_mode:
        with st.expander("➕ เพิ่มรายการ"):
            with st.form("add", clear_on_submit=True):
                n = st.text_input("ชื่อ")
                c = st.selectbox("หมวด", CATEGORIES)
                link = st.text_input("ลิงก์ (YouTube / archive.org / .m3u8 / .mp4)")
                if st.form_submit_button("เพิ่ม") and n and link:
                    st.session_state.channels.append({"name": n, "category": c, "url": link})
                    save_channels(st.session_state.channels)
                    st.rerun()

items = [
    (i, ch)
    for i, ch in enumerate(st.session_state.channels)
    if (cat == "ทั้งหมด" or ch["category"] == cat) and q.lower() in ch["name"].lower()
]

if not items:
    st.info("ไม่พบรายการ ลองเพิ่มลิงก์ในแถบด้านซ้าย")
    st.stop()

left, right = st.columns([2, 1])

with right:
    st.subheader("รายการ")
    for i, ch in items:
        icon = "🧸" if ch["category"] == "การ์ตูนเด็ก" else "🌍"
        if st.button(f"{icon} {ch['name']}", key=f"ch{i}", use_container_width=True):
            st.session_state.current = i
    if not kid_mode:
        st.divider()
        names = [ch["name"] for _, ch in items]
        to_del = st.selectbox("ลบรายการ", ["-"] + names)
        if to_del != "-" and st.button("ลบ"):
            st.session_state.channels = [
                c for c in st.session_state.channels if c["name"] != to_del
            ]
            st.session_state.current = 0
            save_channels(st.session_state.channels)
            st.rerun()

with left:
    idx = st.session_state.current
    if idx >= len(st.session_state.channels):
        idx = 0
    cur = st.session_state.channels[idx]
    st.subheader(cur["name"])
    st.caption(cur["category"])
    render_player(cur["url"])
