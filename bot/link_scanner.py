import re
import ipaddress
import aiohttp
from urllib.parse import urlparse

from config import GOOGLE_SAFE_BROWSING_API_KEY
from bot.virustotal import check_url_virustotal 
from bot.database import get_cached_url, cache_url_result


URL_REGEX = re.compile(
    r'(?:(?:https?://)|(?:www\.))'
    r'[^\s<>()"\']+',
    re.IGNORECASE
)

SHORTENER_DOMAINS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "is.gd",
    "cutt.ly",
    "rb.gy",
    "shorturl.at",
    "ow.ly",
    "buff.ly",
    "tiny.cc",
    "rebrand.ly",
}

SUSPICIOUS_TLDS = {
    ".xyz",
    ".top",
    ".click",
    ".gq",
    ".work",
    ".country",
    ".kim",
    ".loan",
    ".men",
    ".date",
    ".stream",
    ".download",
    ".racing",
    ".xin",
    ".fit",
}

SUSPICIOUS_KEYWORDS = {
    "free",
    "bonus",
    "gift",
    "prize",
    "login",
    "verify",
    "bank",
    "wallet",
    "steamgift",
    "airdrop",
    "claim",
    "update-account",
    "password",
    "promo",
}

# Google Safe Browsing API constants
GOOGLE_SAFE_BROWSING_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"


def extract_urls(text: str) -> list[str]:
    if not text:
        return []

    found = URL_REGEX.findall(text)
    cleaned = []

    for url in found:
        url = url.strip().rstrip(".,!?;:")
        cleaned.append(url)

    return cleaned


def normalize_url(url: str) -> str:
    if url.lower().startswith("www."):
        return "http://" + url
    return url


def get_domain(url: str) -> str:
    parsed = urlparse(normalize_url(url))
    return (parsed.netloc or "").lower()


def is_ip_domain(domain: str) -> bool:
    if ":" in domain:
        domain = domain.split(":")[0]

    try:
        ipaddress.ip_address(domain)
        return True
    except ValueError:
        return False


def has_suspicious_tld(domain: str) -> bool:
    for tld in SUSPICIOUS_TLDS:
        if domain.endswith(tld):
            return True
    return False


def count_suspicious_keywords(url: str) -> int:
    text = url.lower()
    return sum(1 for word in SUSPICIOUS_KEYWORDS if word in text)


def has_at_symbol(url: str) -> bool:
    return "@" in url


def is_too_long(url: str) -> bool:
    return len(url) > 120


async def check_google_safe_browsing(url: str) -> dict | None:
    """
    Check URL against Google Safe Browsing API.
    Returns {"level": "HIGH", "score": 100} if malicious, None if clean or API unavailable.
    """
    if not GOOGLE_SAFE_BROWSING_API_KEY:
        return None

    try:
        payload = {
            "client": {
                "clientId": "securebot",
                "clientVersion": "1.0"
            },
            "threatInfo": {
                "threatTypes": [
                    "MALWARE",
                    "SOCIAL_ENGINEERING",
                    "UNWANTED_SOFTWARE",
                    "POTENTIALLY_HARMFUL_APPLICATION"
                ],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [
                    {"url": normalize_url(url)}
                ]
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{GOOGLE_SAFE_BROWSING_URL}?key={GOOGLE_SAFE_BROWSING_API_KEY}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("matches"):
                        # URL is flagged by Google Safe Browsing
                        return {
                            "level": "HIGH",
                            "score": 100,
                            "source": "google_safe_browsing"
                        }
                return None
    except Exception:
        # If API fails, fallback to heuristic scanning
        return None


def scan_single_url_heuristic(url: str) -> dict:
    """Custom heuristic scanning logic."""
    normalized = normalize_url(url)
    domain = get_domain(normalized)

    score = 0
    reasons = []

    if not domain:
        score += 20
        reasons.append("Havola formati to'liq emas yoki noto'g'ri.")

    if domain in SHORTENER_DOMAINS:
        score += 30
        reasons.append("Qisqartirilgan havola ishlatilgan.")

    if is_ip_domain(domain):
        score += 35
        reasons.append("Domen o'rniga IP manzil ishlatilgan.")

    if has_suspicious_tld(domain):
        score += 20
        reasons.append("Shubhali top-level domen aniqlandi.")

    keyword_hits = count_suspicious_keywords(normalized)
    if keyword_hits >= 2:
        score += 20
        reasons.append("Havolada aldamchi yoki phishingga o'xshash so'zlar bor.")
    elif keyword_hits == 1:
        score += 10
        reasons.append("Havolada ehtiyot bo'lish kerak bo'lgan so'z bor.")

    if has_at_symbol(normalized):
        score += 15
        reasons.append("Havolada '@' belgisi bor, bu yashirish usuli bo'lishi mumkin.")

    if is_too_long(normalized):
        score += 10
        reasons.append("Havola juda uzun.")

    if domain.count("-") >= 3:
        score += 10
        reasons.append("Domen nomi g'alati va haddan tashqari murakkab ko'rinadi.")

    if score >= 60:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    elif score > 0:
        level = "LOW"
    else:
        level = "LOW"

    if score == 0:
        reasons.append("Aniq shubhali belgi topilmadi.")

    return {
        "url": url,
        "normalized_url": normalized,
        "domain": domain,
        "score": score,
        "level": level,
        "reasons": reasons,
    }


async def scan_single_url(url: str) -> dict:
    """Scan a single URL with caching, Google Safe Browsing, and VirusTotal fallback."""
    normalized = normalize_url(url)
    
    # 1. Keshni tekshirish
    cached = get_cached_url(normalized)
    if cached:
        return {
            "url": url,
            "normalized_url": normalized,
            "domain": get_domain(normalized),
            "score": cached["score"],
            "level": cached["level"],
            "reasons": ["Result from cache"],
            "from_cache": True,
        }
    
    # 2. Google Safe Browsing API tekshiruvi
    google_result = await check_google_safe_browsing(normalized)
    if google_result:
        cache_url_result(normalized, google_result["score"], google_result["level"])
        return {
            "url": url,
            "normalized_url": normalized,
            "domain": get_domain(normalized),
            "score": google_result["score"],
            "level": google_result["level"],
            "reasons": ["Flagged by Google Safe Browsing"],
        }
    
    # 3. YANGI: VirusTotal API tekshiruvi
    vt_stats = await check_url_virustotal(normalized)
    if vt_stats and vt_stats != "scanning":
        malicious = vt_stats.get("malicious", 0)
        suspicious = vt_stats.get("suspicious", 0)
        
        if malicious > 0 or suspicious > 1:
            # Agar antiviruslar zararli deb topsa, risk ballini hisoblaymiz
            score = min(50 + (malicious * 15), 100)
            level = "HIGH" if score >= 60 else "MEDIUM"
            
            cache_url_result(normalized, score, level)
            return {
                "url": url,
                "normalized_url": normalized,
                "domain": get_domain(normalized),
                "score": score,
                "level": level,
                "reasons": [f"VirusTotal: {malicious} ta antivirus zararli deb aniqladi."],
            }

    # 4. Evristik tahlil (Muqobil variant)
    result = scan_single_url_heuristic(normalized)
    cache_url_result(normalized, result["score"], result["level"])
    
    return result


async def scan_links_in_text(text: str) -> dict | None:
    """Scan all links in text asynchronously."""
    urls = extract_urls(text)
    if not urls:
        return None

    results = [await scan_single_url(url) for url in urls]

    max_score = max(r["score"] for r in results)
    highest = max(results, key=lambda r: r["score"])

    # Agar bitta xabarda juda ko'p havola bo'lsa, riskni oshiramiz
    extra_score = 0
    extra_reasons = []

    if len(urls) >= 3:
        extra_score += 10
        extra_reasons.append("Bitta xabarda juda ko'p havola yuborilgan.")

    total_score = min(max_score + extra_score, 100)

    if total_score >= 60:
        final_level = "HIGH"
    elif total_score >= 30:
        final_level = "MEDIUM"
    else:
        final_level = "LOW"

    reasons = list(highest["reasons"]) + extra_reasons

    return {
        "found": True,
        "url_count": len(urls),
        "urls": urls,
        "top_url": highest["url"],
        "score": total_score,
        "level": final_level,
        "reasons": reasons,
        "details": results,
    }
