"""Streamlit LIVE-only cartoon/documentary player. pip install streamlit yt-dlp"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title='ทีวีการ์ตูน LIVE', page_icon='📺', layout='wide')
DATA_FILE = Path('channels_live.json')
CATEGORIES = ['การ์ตูนเด็ก', 'สารคดี']
# คำค้นเป็นแหล่งค้นหา LIVE ไม่ใช่ URL ที่ยืนยันว่าถ่ายทอดสดตลอด 24 ชั่วโมง
DEFAULTS = [
    {'name': n, 'category': 'การ์ตูนเด็ก', 'url': 'ytsearch5:' + q}
    for n, q in [
        ('BabyBus ภาษาไทย', 'BabyBus ภาษาไทย live สด'),
        ('Pororo ภาษาไทย', 'Pororo ภาษาไทย live สด'),
        ('Larva ภาษาไทย', 'Larva ภาษาไทย live สด'),
        ('Tayo ภาษาไทย', 'Tayo ภาษาไทย live สด'),
        ('Robocar Poli ภาษาไทย', 'Robocar Poli ภาษาไทย live สด'),
        ('CoComelon ภาษาไทย', 'CoComelon ภาษาไทย live สด'),
        ('Pinkfong ภาษาไทย', 'Pinkfong ภาษาไทย live สด'),
        ('Masha and the Bear ภาษาไทย', 'Masha and the Bear ภาษาไทย live สด'),
        ('Peppa Pig ภาษาไทย', 'Peppa Pig ภาษาไทย live สด'),
        ('นิทานการ์ตูนเด็ก ภาษาไทย', 'นิทานการ์ตูนเด็ก ภาษาไทย live สด'),
    ]
] + [
    {'name': n, 'category': 'สารคดี', 'url': 'ytsearch5:' + q}
    for n, q in [
        ('National Geographic LIVE', 'National Geographic live'),
        ('BBC Earth LIVE', 'BBC Earth live'),
        ('DW Documentary LIVE', 'DW Documentary live'),
        ('NASA LIVE', 'NASA live official'),
        ('วิทยาศาสตร์ LIVE', 'science documentary live stream'),
    ]
]


def load_channels():
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
            if isinstance(data, list):
                return data
        except (OSError, ValueError):
            pass
    return [dict(x) for x in DEFAULTS]


def save_channels(channels):
    DATA_FILE.write_text(json.dumps(channels, ensure_ascii=False, indent=2), encoding='utf-8')


@st.cache_data(ttl=300, show_spinner=False)
def check_live(source):
    """Return embeddable YouTube video ID only if yt-dlp reports an actual live stream."""
    try:
        import yt_dlp
        opts = {'quiet': True, 'no_warnings': True, 'skip_download': True,
                'extract_flat': 'in_playlist', 'socket_timeout': 8,
                'ignoreerrors': True, 'noplaylist': True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(source, download=False)
            if not data:
                return None
            candidates = data.get('entries', []) if 'entries' in data else [data]
            for candidate in candidates:
                if not candidate:
                    continue
                video_id = candidate.get('id')
                if not video_id or not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
                    continue
                # Flat search metadata can be incomplete: verify actual video status.
                with yt_dlp.YoutubeDL({**opts, 'extract_flat': False}) as verifier:
                    full = verifier.extract_info('https://www.youtube.com/watch?v=' + video_id, download=False)
                if full and (full.get('live_status') == 'is_live' or full.get('is_live') is True):
                    return video_id
    except Exception:
        return None
    return None


def inspect_channel(channel):
    url = channel.get('url', '').strip()
    if not url:
        return None
    # Direct HLS endpoints cannot reliably be checked for LIVE from metadata;
    # they are excluded rather than falsely labeled LIVE.
    if url.startswith('ytsearch') or 'youtube.com/' in url or 'youtu.be/' in url:
        return check_live(url)
    return None


if 'channels' not in st.session_state:
    st.session_state.channels = load_channels()
if 'current' not in st.session_state:
    st.session_state.current = None

st.title('📺 ทีวีออนไลน์ — LIVE เท่านั้น')
st.caption('แสดงเฉพาะวิดีโอที่ YouTube รายงานว่ากำลังถ่ายทอดสดจริง (ตรวจสอบใหม่ทุก 5 นาที)')
with st.sidebar:
    cat = st.radio('หมวดหมู่', ['ทั้งหมด'] + CATEGORIES)
    q = st.text_input('ค้นหาช่อง')
    kid_mode = st.toggle('🧒 โหมดเด็ก (ซ่อนการจัดการ)', value=False)
    if st.button('🔄 ตรวจสอบ LIVE ใหม่', use_container_width=True):
        check_live.clear()
        st.rerun()
    if not kid_mode:
        if st.button('รีเซ็ตช่องเริ่มต้น'):
            st.session_state.channels = [dict(x) for x in DEFAULTS]
            save_channels(st.session_state.channels)
            st.session_state.current = None
            check_live.clear()
            st.rerun()
        with st.expander('➕ เพิ่มช่อง LIVE'):
            with st.form('add_live', clear_on_submit=True):
                name = st.text_input('ชื่อช่อง')
                category = st.selectbox('หมวดหมู่', CATEGORIES)
                url = st.text_input('ลิงก์ YouTube LIVE หรือ ytsearch5:คำค้น')
                if st.form_submit_button('เพิ่มช่อง'):
                    if name.strip() and (url.startswith('ytsearch') or 'youtube.com/' in url or 'youtu.be/' in url):
                        st.session_state.channels.append({'name': name.strip(), 'category': category, 'url': url.strip()})
                        save_channels(st.session_state.channels)
                        st.rerun()
                    st.error('กรอกชื่อและลิงก์ YouTube ที่ถูกต้อง')

filtered = [(i, ch) for i, ch in enumerate(st.session_state.channels)
            if (cat == 'ทั้งหมด' or ch.get('category') == cat)
            and q.lower() in ch.get('name', '').lower()]
with st.spinner('กำลังตรวจสอบว่าช่องใด LIVE จริง...'):
    with ThreadPoolExecutor(max_workers=5) as pool:
        ids = list(pool.map(lambda pair: inspect_channel(pair[1]), filtered))
live_items = [(i, ch, video_id) for (i, ch), video_id in zip(filtered, ids) if video_id]
st.metric('ช่องที่กำลัง LIVE', len(live_items))
if not live_items:
    st.warning('ยังไม่พบช่องที่ยืนยันว่า LIVE ในขณะนี้ หรือ YouTube จำกัดการตรวจสอบ ลองกดตรวจสอบใหม่ภายหลัง')
    st.stop()

left, right = st.columns([2, 1])
with right:
    st.subheader('🔴 ช่อง LIVE')
    for i, ch, vid in live_items:
        if st.button('🔴 ' + ch['name'], key=f'ch_{i}', use_container_width=True):
            st.session_state.current = i
    if not kid_mode:
        with st.expander('ลบช่อง'):
            choices = {f"{i + 1}. {ch['name']}": i for i, ch in enumerate(st.session_state.channels)}
            chosen = st.selectbox('เลือกช่อง', list(choices))
            if st.button('ลบช่องที่เลือก'):
                st.session_state.channels.pop(choices[chosen])
                save_channels(st.session_state.channels)
                st.session_state.current = None
                st.rerun()
with left:
    selected = next((x for x in live_items if x[0] == st.session_state.current), live_items[0])
    _, ch, video_id = selected
    st.subheader('🔴 ' + ch['name'])
    st.caption(ch['category'] + ' • LIVE')
    components.iframe('https://www.youtube.com/embed/' + video_id + '?autoplay=1&rel=0', height=480)
    st.link_button('เปิด LIVE บน YouTube', 'https://www.youtube.com/watch?v=' + video_id)
    st.caption('บางช่องอาจปิดการฝังวิดีโอ ให้ใช้ปุ่มเปิดบน YouTube แทน')
