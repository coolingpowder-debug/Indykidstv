"""Streamlit LIVE-only cartoon/documentary player. pip install streamlit yt-dlp"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title='ทีวีการ์ตูน LIVE', page_icon='📺', layout='wide')
DATA_FILE = Path('channels_live_world_150.json')
CATEGORIES = ['การ์ตูนภาษาอังกฤษ', 'สารคดี']
# คำค้นเป็นแหล่งค้นหา LIVE ไม่ใช่ URL ที่ยืนยันว่าถ่ายทอดสดตลอด 24 ชั่วโมง
# 150 LIVE discovery targets: 100 English cartoon brands and 50 worldwide documentary sources/topics.
# These are SEARCH TARGETS, not 150 verified simultaneous broadcasts.
CARTOON_TARGETS = ['Peppa Pig', 'Bluey', 'CoComelon', 'Little Baby Bum', 'BabyBus', 'Pinkfong', 'Baby Shark', 'Super Simple Songs', 'Blippi', 'Morphle', 'Pocoyo', 'Masha and the Bear', 'Larva', 'Pororo', 'Tayo the Little Bus', 'Robocar Poli', 'Titipo', 'Leo the Truck', 'Booba', 'Oddbods', 'Sunny Bunnies', 'Talking Tom', 'Talking Angela', 'My Talking Tom Friends', 'Shaun the Sheep', 'Timmy Time', 'Bing Bunny', 'Hey Duggee', 'Sarah and Duck', 'Numberblocks', 'Alphablocks', 'Colourblocks', 'StoryBots', 'Sesame Street', 'Elmo', 'Mickey Mouse Clubhouse', 'Disney Junior', 'PJ Masks', 'Spidey and His Amazing Friends', 'Blue Clues and You', 'PAW Patrol', 'Rubble and Crew', 'Dora the Explorer', 'Bubble Guppies', 'Team Umizoomi', 'SpongeBob SquarePants', 'The Loud House', 'Teen Titans Go', 'Tom and Jerry', 'Looney Tunes', 'Bugs Bunny', 'Scooby Doo', 'Mr Bean Animated', 'Grizzy and the Lemmings', 'Zig and Sharko', 'Oggy and the Cockroaches', 'The Smurfs', 'The Garfield Show', 'Heidi cartoon', 'Maya the Bee', 'The Fixies', 'Om Nom Stories', 'Cut the Rope cartoon', 'Katuri', 'Molangg', 'Molang cartoon', 'Simon Super Rabbit', 'Caillou', 'Arthur PBS Kids', 'Curious George', 'Wild Kratts', 'Daniel Tigers Neighborhood', 'Super Why', 'WordWorld', 'Sid the Science Kid', 'Octonauts', 'Go Jetters', 'Thomas and Friends', 'Chuggington', 'Bob the Builder', 'Fireman Sam', 'Postman Pat', 'Little Einsteins', 'Dinosaur Train', 'Gigantosaurus', 'Jurassic World Camp Cretaceous', 'Pokémon Kids TV', 'Sonic Boom', 'Sonic Prime', 'Kirby cartoon', 'Ninjago', 'LEGO City Adventures', 'LEGO Friends', 'Barbie Dreamhouse Adventures', 'Polly Pocket', 'My Little Pony', 'Care Bears', 'Strawberry Shortcake', 'Rainbow Rangers', 'True and the Rainbow Kingdom']
DOCUMENTARY_TARGETS = ['NASA Live', 'NASA Earth from Space', 'NASA ISS Live', 'ESA European Space Agency', 'SpaceX launch live', 'Blue Origin live', 'JAXA space live', 'ISRO launch live', 'European Southern Observatory', 'Royal Observatory Greenwich', 'National Geographic', 'Nat Geo Wild', 'BBC Earth', 'BBC Earth Science', 'Discovery Channel', 'Discovery Science', 'Animal Planet', 'Smithsonian Channel', 'PBS Nature', 'PBS NOVA', 'DW Documentary', 'DW Planet A', 'ARTE Documentary', 'Al Jazeera English documentaries', 'NHK World Japan', 'NHK World Science View', 'France 24 documentary', 'TRT World documentary', 'CGTN Documentary', 'CNA Insider documentary', 'ABC Australia documentary', 'CBC The Nature of Things', 'TVO Docs', 'Real Stories documentary', 'Free Documentary', 'Free Documentary Nature', 'Free Documentary History', 'Timeline World History Documentaries', 'History Channel', 'History Hit', 'Ancient Architects', 'World Science Festival', 'The Royal Institution', 'The Nature Conservancy', 'Ocean Exploration Trust', 'NOAA Ocean Exploration', 'Monterey Bay Aquarium live', 'Explore.org live nature cams', 'Cornell Lab Bird Cams', 'Africam wildlife live']
DEFAULTS = (
    [{'name': n + ' — English LIVE', 'category': 'การ์ตูนภาษาอังกฤษ',
      'url': 'ytsearch5:' + n + ' official English live stream'} for n in CARTOON_TARGETS]
    + [{'name': n + ' — LIVE', 'category': 'สารคดี',
        'url': 'ytsearch5:' + n + ' official live stream'} for n in DOCUMENTARY_TARGETS]
)


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

st.title('📺 LIVE ทั่วโลก — การ์ตูนอังกฤษ 100 + สารคดี 50')
st.caption('100 แหล่งค้นหาการ์ตูนภาษาอังกฤษ + 50 แหล่งค้นหาสารคดีทั่วโลก • แสดงเฉพาะที่ยืนยันว่า LIVE • ไม่รับประกันว่าทุกแหล่งจะมี LIVE')
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
st.caption(f'มีแหล่งค้นหา {len(filtered)} รายการ (ไม่ใช่จำนวนช่องที่กำลัง LIVE)')
page_size = st.select_slider('จำนวนรายการที่ตรวจสอบต่อครั้ง', options=[10, 20, 30, 50], value=20)
page_count = max(1, (len(filtered) + page_size - 1) // page_size)
page = st.number_input('หน้ารายการ', min_value=1, max_value=page_count, value=1, step=1)
filtered = filtered[(page - 1) * page_size:page * page_size]
with st.spinner('กำลังตรวจสอบว่าช่องใด LIVE จริง...'):
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(lambda pair: inspect_channel(pair[1]), filtered))
live_items = [(i, ch, video_id) for (i, ch), video_id in zip(filtered, ids) if video_id]
st.metric('ช่องที่กำลัง LIVE ในหน้าที่ตรวจสอบ', len(live_items))
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
