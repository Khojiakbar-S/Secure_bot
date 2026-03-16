def bool_uz(value: int | bool) -> str:
    return "yoqilgan" if value else "o‘chirilgan"


def format_settings(settings: dict) -> str:
    log_channel = settings["log_channel"] if settings["log_channel"] else "o‘rnatilmagan"

    return (
        "⚙️ <b>Bot sozlamalari</b>\n\n"
        f"• Bot holati: <b>{bool_uz(settings['enabled'])}</b>\n"
        f"• Yuqori xavf bo‘lsa xabarni o‘chirish: <b>{bool_uz(settings['delete_high'])}</b>\n"
        f"• O‘rta xavf bo‘lsa ogohlantirish: <b>{bool_uz(settings['warn_medium'])}</b>\n"
        f"• Past xavf bo‘lsa javob qaytarish: <b>{bool_uz(settings['reply_low'])}</b>\n"
        f"• Linklarni tekshirish: <b>{bool_uz(settings['scan_links'])}</b>\n"
        f"• APK fayllarni tekshirish: <b>{bool_uz(settings['scan_apk'])}</b>\n"
        f"• Log kanali/chat ID: <b>{log_channel}</b>\n\n"
        "ℹ️ <b>Eslatma:</b> Bu bot xavfni baholaydi. U 100% antivirus kafolati bermaydi."
    )


HELP_TEXT = """
🛡 <b>SecureBot qo‘llanmasi</b>

Bu bot guruhdagi:
• linklarni
• APK fayllarni
tekshiradi va xavf bo‘lsa ogohlantiradi.

<b>Botni guruhga tayyorlash:</b>
1. BotFather orqali <code>/setprivacy</code> ni <b>Disable</b> qiling
2. Botni guruhga admin qiling
3. Botga <b>Delete messages</b> ruxsatini bering

<b>Asosiy buyruqlar:</b>
/settings — joriy sozlamalarni ko‘rish
/set &lt;key&gt; on|off — sozlamani yoqish/o‘chirish
/setlog &lt;chat_id&gt; — loglar yuboriladigan joyni belgilash
/whitelist add &lt;user_id&gt; — foydalanuvchini tekshiruvdan ozod qilish
/whitelist del &lt;user_id&gt; — whitelistdan olib tashlash
/whitelist list — whitelist ro‘yxatini ko‘rish

<b>Sozlamalar ro‘yxati:</b>
• enabled — botni yoqish/o‘chirish
• delete_high — yuqori xavf bo‘lsa xabarni o‘chirish
• warn_medium — o‘rta xavf bo‘lsa ogohlantirish
• reply_low — past xavf bo‘lsa javob yozish
• scan_links — linklarni tekshirish
• scan_apk — APK fayllarni tekshirish

<b>Misollar:</b>
<code>/set delete_high on</code>
<code>/set scan_links off</code>
<code>/setlog -1001234567890</code>
<code>/whitelist add 123456789</code>

<b>Oddiy tushuntirish:</b>
Agar bot yoqilgan bo‘lsa, guruhga yuborilgan shubhali havola yoki APK faylni tekshiradi.
Sozlamaga qarab:
• javob yozadi
• ogohlantiradi
• log kanalga yuboradi
• yoki xabarni o‘chiradi

⚠️ <b>Muhim:</b> Bot “xavf topilmadi” desa ham, noma’lum fayl va linklarni ochishda ehtiyot bo‘ling.
""".strip()


START_TEXT = """
Salom. Men <b>SecureBot</b>man. 🛡

Men guruhdagi linklar va APK fayllarni tekshirishga yordam beraman.

Boshlash uchun:
• meni guruhga admin qiling
• <b>Delete messages</b> ruxsatini bering
• BotFather orqali <b>/setprivacy → Disable</b> qiling

Qo‘llanma uchun:
<code>/help</code>

Joriy sozlamalarni ko‘rish uchun:
<code>/settings</code>
""".strip()


def setting_updated_text(key: str, enabled: bool) -> str:
    state = "yoqildi" if enabled else "o‘chirildi"
    return f"✅ <b>{key}</b> sozlamasi {state}."


def setlog_updated_text(chat_id: str) -> str:
    return (
        "✅ Log manzili saqlandi.\n\n"
        f"Yangi log manzili: <code>{chat_id}</code>"
    )


def whitelist_add_text(user_id: int, added: bool) -> str:
    if added:
        return f"✅ <code>{user_id}</code> whitelistga qo‘shildi."
    return f"ℹ️ <code>{user_id}</code> allaqachon whitelistda bor."


def whitelist_del_text(user_id: int, removed: bool) -> str:
    if removed:
        return f"✅ <code>{user_id}</code> whitelistdan olib tashlandi."
    return f"ℹ️ <code>{user_id}</code> whitelistda topilmadi."


def whitelist_list_text(user_ids: list[int]) -> str:
    if not user_ids:
        return "📋 Whitelist bo‘sh."

    items = "\n".join(f"• <code>{uid}</code>" for uid in user_ids)
    return f"📋 <b>Whitelist ro‘yxati</b>\n\n{items}"


def format_link_scan_result(result: dict) -> str:
    reasons = "\n".join(f"• {reason}" for reason in result["reasons"])

    return (
        f"🔗 <b>Havola tekshiruv natijasi: {result['level']}</b>\n"
        f"Ball: <b>{result['score']}</b>\n\n"
        f"<b>Topilgan havolalar soni:</b> {result['url_count']}\n"
        f"<b>Asosiy havola:</b> <code>{result['top_url']}</code>\n\n"
        f"<b>Sabablar:</b>\n{reasons}\n\n"
        "ℹ️ Bu avtomatik xavf baholash natijasi."
    )


def format_link_warning_for_group(result: dict, full_name: str) -> str:
    reasons = "\n".join(f"• {reason}" for reason in result["reasons"][:4])

    return (
        f"⚠️ <b>Ogohlantirish</b>\n\n"
        f"Foydalanuvchi: <b>{full_name}</b>\n"
        f"Natija: <b>{result['level']}</b>\n"
        f"Ball: <b>{result['score']}</b>\n\n"
        f"<b>Sabablar:</b>\n{reasons}\n\n"
        "Iltimos, bu havolani ochishda ehtiyot bo‘ling."
    )


def format_link_reply_low(result: dict) -> str:
    return (
        f"ℹ️ Havola tekshirildi: <b>{result['level']}</b>\n"
        f"Ball: <b>{result['score']}</b>\n"
        "Katta xavf belgisi topilmadi, lekin baribir ehtiyot bo‘ling."
    )


def format_link_deleted_text(result: dict, full_name: str) -> str:
    return (
        f"🗑 <b>Xabar o‘chirildi</b>\n\n"
        f"Foydalanuvchi: <b>{full_name}</b>\n"
        f"Sabab: shubhali havola\n"
        f"Daraja: <b>{result['level']}</b>\n"
        f"Ball: <b>{result['score']}</b>"
    )


def format_log_text(chat_title: str, user_id: int, full_name: str, result: dict, action: str) -> str:
    reasons = "\n".join(f"• {reason}" for reason in result["reasons"][:5])

    return (
        "🛡 <b>SecureBot logi</b>\n\n"
        f"<b>Guruh:</b> {chat_title}\n"
        f"<b>Foydalanuvchi:</b> {full_name}\n"
        f"<b>User ID:</b> <code>{user_id}</code>\n"
        f"<b>Amal:</b> {action}\n"
        f"<b>Daraja:</b> {result['level']}\n"
        f"<b>Ball:</b> {result['score']}\n"
        f"<b>Havola:</b> <code>{result['top_url']}</code>\n\n"
        f"<b>Sabablar:</b>\n{reasons}"
    )


NOT_ADMIN_TEXT = "⛔ Bu buyruqni faqat guruh adminlari ishlata oladi."

UNKNOWN_SETTING_TEXT = (
    "❌ Noto‘g‘ri sozlama kaliti.\n\n"
    "To‘g‘ri kalitlar:\n"
    "• enabled\n"
    "• delete_high\n"
    "• warn_medium\n"
    "• reply_low\n"
    "• scan_links\n"
    "• scan_apk"
)

SET_USAGE_TEXT = (
    "❌ Buyruq noto‘g‘ri yozildi.\n\n"
    "To‘g‘ri ko‘rinishi:\n"
    "<code>/set scan_links on</code>\n"
    "<code>/set delete_high off</code>"
)

SETLOG_USAGE_TEXT = (
    "❌ Buyruq noto‘g‘ri yozildi.\n\n"
    "To‘g‘ri ko‘rinishi:\n"
    "<code>/setlog -1001234567890</code>"
)

WHITELIST_USAGE_TEXT = (
    "❌ Buyruq noto‘g‘ri yozildi.\n\n"
    "To‘g‘ri misollar:\n"
    "<code>/whitelist add 123456789</code>\n"
    "<code>/whitelist del 123456789</code>\n"
    "<code>/whitelist list</code>"
)