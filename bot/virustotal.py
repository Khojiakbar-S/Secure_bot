import aiohttp
import hashlib
import base64
import os
from config import getenv_str

# VirusTotal API kalitini config orqali yoki to'g'ridan-to'g'ri .env dan olamiz
VIRUSTOTAL_API_KEY = getenv_str("VIRUSTOTAL_API_KEY")

async def check_url_virustotal(url: str) -> dict | None:
    """URL manzilini VirusTotal API v3 orqali tekshirish"""
    if not VIRUSTOTAL_API_KEY:
        return None

    # URL manzilini base64 formatiga o'tkazamiz (oxiridagi '=' belgisisiz)
    url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
    api_url = f"https://www.virustotal.com/api/v3/urls/{url_id}"
    
    headers = {"x-apikey": VIRUSTOTAL_API_KEY}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['data']['attributes']['last_analysis_stats']
                elif resp.status == 404:
                    # Agar havola VT bazasida bo'lmasa, uni tahlil qilish uchun navbatga yuboramiz
                    await session.post("https://www.virustotal.com/api/v3/urls", headers=headers, data={"url": url})
                    return "scanning"
        except Exception:
            return None

async def check_file_hash_virustotal(file_path: str) -> dict | None:
    """Faylning SHA-256 xeshi orqali VirusTotal bazasidan qidirish (Faylni yuklamasdan, 1 soniyada tekshiradi)"""
    if not VIRUSTOTAL_API_KEY:
        return None

    # Fayl xeshini (SHA-256) hisoblaymiz
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        file_hash = sha256_hash.hexdigest()
    except Exception:
        return None

    api_url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
    headers = {"x-apikey": VIRUSTOTAL_API_KEY}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['data']['attributes']['last_analysis_stats']
                return None  # Fayl bazada topilmadi (yangi fayl)
        except Exception:
            return None