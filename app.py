import json
import re
from urllib.parse import quote_plus
from pathlib import Path

import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="ทีวีฟรี การ์ตูน & สารคดี", page_icon="📺", layout="wide")

DATA_FILE = Path("channels.json")
CATEGORIES = ["การ์ตูนเด็ก", "สารคดี"]

# รายการเริ่มต้น: ช่อง YouTube ทางการ (ดูได้ตลอด เพราะเล่นจากวิดีโอที่อัปโหลดทั้งหมดของช่อง ไม่ใช่ไลฟ์ที่จบแล้ว)
# ใส่เป็นลิงก์ช่อง https://www.youtube.com/@ชื่อช่อง ได้เลย แอพจะหาเพลย์ลิสต์ให้เอง
DEFAULTS = [
    {"name": "เบบี้บัส ภาษาไทย", "category": "การ์ตูนเด็ก", "url": "https://www.youtube.com/results?search_query=BabyBus+ภาษาไทย"},
    {"name": "โพโรโระ เพนกวินน้อย ภาษาไทย", "category": "การ์ตูนเด็ก", "url": "https://www.youtube.com/results?search_query=Pororo+ภาษาไทย"},
    {"name": "เพื่อนรักสัตว์เลี้ยง ลาร์วา ภาษาไทย", "category": "การ์ตูนเด็ก", "url": "https://www.youtube.com/results?search_query=Larva+การ์ตูน+พากย์ไทย"},
    {"name": "รถบัสไทโย ภาษาไทย", "category": "การ์ตูนเด็ก", "url": "https://www.youtube.com/results?search_query=Tayo+ภาษาไทย"},
    {"name": "โรโบคาร์ โพลี ภาษาไทย", "category": "การ์ตูนเด็ก", "url": "https://www.youtube.com/results?search_query=Robocar+Poli+ภาษาไทย"},
    {"name": "หนูน้อยโคโค่เมลอน เพลงเด็กไทย", "category": "การ์ตูนเด็ก", "url": "https://www.youtube.com/results?search_query=CoComelon+ภาษาไทย"},
    {"name": "พิ้งฟอง เพลงเด็กภาษาไทย", "category": "การ์ตูนเด็ก", "url": "https://www.youtube.com/results?search_query=Pinkfong+ภาษาไทย"},
    {"name": "มาช่าและหมี ภาษาไทย", "category": "การ์ตูนเด็ก", "url": "https://www.youtube.com/results?search_query=Masha+and+the+Bear+ภาษาไทย"},
    {"name": "เป๊ปป้าพิก ภาษาไทย", "category": "การ์ตูนเด็ก", "url": "https://www.youtube.com/results?search_query=Peppa+Pig+ภาษาไทย"},
    {"name": "นิทานการ์ตูนเด็ก ภาษาไทย", "category": "การ์ตูนเด็ก", "url": "https://www.youtube.com/results?search_query=นิทานการ์ตูนเด็ก+ภาษาไทย"},
    {"name": "National Geographic", "category": "สารคดี", "url": "https://www.youtube.com/@NatGeo"},
    {"name": "BBC Earth", "category": "สารคดี", "url": "https://www.youtube.com/@BBCEarth"},
    {"name": "DW Documentary", "category": "สารคดี", "url": "https://www.youtube.com/@dwdocumentary"},
    {"name": "NASA (อวกาศ)", "category": "สารคดี", "url": "https://www.youtube.com/@NASA"},
    {"name": "Kurzgesagt (วิทยาศาสตร์แอนิเมชัน)", "category": "สารคดี", "url": "https://www.youtube.com/@kurzgesagt"},
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


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24 * 30)
def resolve_channel_id(url: str):
    """หา channel ID (UC...) จากลิงก์ช่อง เช่น https://www.youtube.com/@NASA"""
    m = re.search(r"youtube\.com/channel/(UC[\w-]{22})", url)
    if m:
        return m.group(1)
    try:
        r = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"},
            cookies={"CONSENT": "YES+1", "SOCS": "CAI"},
        )
        for pat in (
            r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"',
            r'"externalId":"(UC[\w-]{22})"',
            r'"channelId":"(UC[\w-]{22})"',
        ):
            mm = re.search(pat, r.text)
            if mm:
                return mm.group(1)
    except Exception:
        pass
    return None


def render_player(url: str):
    """แปลงลิงก์เป็นตัวเล่น: YouTube / Internet Archive / HLS (.m3u8) / ไฟล์วิดีโอ"""
    u = url.strip()

    # ลิงก์ค้นหาการ์ตูนภาษาไทย: เปิดผลลัพธ์ใน YouTube เพื่อเลือกตอน
    # (YouTube ไม่รองรับการฝังหน้าผลการค้นหาเป็นเครื่องเล่น)
    if "youtube.com/results?search_query=" in u:
        st.info("เลือกรายการหรือตอนพากย์ไทยจาก YouTube แล้วคัดลอกลิงก์วิดีโอมาเพิ่มในแอปเพื่อเล่นในหน้านี้ได้")
        st.link_button("▶️ เปิดรายการภาษาไทยใน YouTube", u)
        return

    # YouTube (วิดีโอ หรือ เพลย์ลิสต์)
    m = re.search(r"(?:v=|youtu\.be/|embed/)([\w-]{11})", u)
    pl = re.search(r"list=([\w-]+)", u)
    if "youtube.com" in u or "youtu.be" in u:
        if m:
            src = f"https://www.youtube.com/embed/{m.group(1)}?rel=0"
        elif not pl and re.search(r"youtube\.com/(@|channel/|c/|user/)", u):
            cid = resolve_channel_id(u)
            if not cid:
                st.warning("หาช่องนี้ไม่เจอ (ต้องต่ออินเทอร์เน็ต) ลองใช้ลิงก์วิดีโอหรือเพลย์ลิสต์แทน")
                st.link_button("เปิดช่องใน YouTube", u)
                return
            # เพลย์ลิสต์ "วิดีโอที่อัปโหลดทั้งหมด" ของช่อง = UU + ส่วนท้ายของ channel ID
            src = f"https://www.youtube.com/embed/videoseries?list=UU{cid[2:]}"
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
    # เพิ่มการ์ตูนภาษาไทยให้ข้อมูลเก่าที่บันทึกไว้ โดยไม่ลบรายการของผู้ใช้
    existing = {ch.get("name") for ch in st.session_state.channels}
    additions = [ch.copy() for ch in DEFAULTS[:10] if ch["name"] not in existing]
    if additions:
        st.session_state.channels = additions + st.session_state.channels
        save_channels(st.session_state.channels)
if "current" not in st.session_state:
    st.session_state.current = 0

st.title("📺 ทีวีฟรี: การ์ตูนเด็ก & สารคดี")

with st.sidebar:
    st.header("เลือกรายการ")
    cat = st.radio("หมวดหมู่", ["ทั้งหมด"] + CATEGORIES)
    q = st.text_input("ค้นหา")

    kid_mode = st.toggle("🧒 โหมดเด็ก (ซ่อนการจัดการ)", value=False)

    if not kid_mode:
        if st.button("🔄 รีเซ็ตเป็นรายการเริ่มต้น"):
            st.session_state.channels = list(DEFAULTS)
            st.session_state.current = 0
            save_channels(st.session_state.channels)
            st.rerun()
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
