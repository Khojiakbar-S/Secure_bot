import zipfile


DANGEROUS_PERMISSIONS = {
    "READ_SMS",
    "SEND_SMS",
    "READ_CONTACTS",
    "WRITE_CONTACTS",
    "QUERY_ALL_PACKAGES",
    "REQUEST_INSTALL_PACKAGES",
}


def scan_apk_file(file_path: str) -> dict:

    score = 0
    reasons = []

    dex_count = 0
    so_count = 0

    try:
        with zipfile.ZipFile(file_path, "r") as apk:

            files = apk.namelist()

            for f in files:

                if f.endswith(".dex"):
                    dex_count += 1

                if f.endswith(".so"):
                    so_count += 1

                for perm in DANGEROUS_PERMISSIONS:
                    if perm in f:
                        score += 15
                        reasons.append(f"Shubhali permission: {perm}")

    except Exception:
        return {
            "level": "UNKNOWN",
            "score": 0,
            "reasons": ["APK faylni o‘qib bo‘lmadi."]
        }

    if dex_count > 3:
        score += 15
        reasons.append("DEX fayllar juda ko‘p.")

    if so_count > 0:
        score += 10
        reasons.append("Native kutubxonalar mavjud (.so).")

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
        "level": level,
        "score": score,
        "reasons": reasons,
        "dex_count": dex_count,
        "so_count": so_count,
    }