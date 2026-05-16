def bool_uz(value: int | bool) -> str:
    # Keep function name to avoid refactors in other modules.
    return "enabled" if value else "disabled"


def format_settings(settings: dict) -> str:
    log_channel = settings["log_channel"] if settings["log_channel"] else "not set"

    return (
        "⚙️ <b>Bot Settings</b>\n\n"
        f"• Bot status: <b>{bool_uz(settings['enabled'])}</b>\n"
        f"• High risk: delete message: <b>{bool_uz(settings['delete_high'])}</b>\n"
        f"• Medium risk: send warning: <b>{bool_uz(settings['warn_medium'])}</b>\n"
        f"• Low risk: reply: <b>{bool_uz(settings['reply_low'])}</b>\n"
        f"• Check links: <b>{bool_uz(settings['scan_links'])}</b>\n"
        f"• Check APK files: <b>{bool_uz(settings['scan_apk'])}</b>\n"
        f"• Log channel/chat ID: <b>{log_channel}</b>\n\n"
        "ℹ️ <b>Note:</b> This bot estimates risk. It does not guarantee 100% antivirus protection."
    )


def format_settings_inline(settings: dict) -> str:
    """Format settings for inline keyboard display."""
    log_channel = settings.get("log_channel") if settings.get("log_channel") else "not set"
    
    status = {
        "enabled": f"{'✅' if settings['enabled'] else '❌'} Bot",
        "delete_high": f"{'✅' if settings['delete_high'] else '❌'} Delete High",
        "warn_medium": f"{'✅' if settings['warn_medium'] else '❌'} Warn Medium",
        "reply_low": f"{'✅' if settings['reply_low'] else '❌'} Reply Low",
        "scan_links": f"{'✅' if settings['scan_links'] else '❌'} Links",
        "scan_apk": f"{'✅' if settings['scan_apk'] else '❌'} APK",
        "mute_high_risk": f"{'✅' if settings['mute_high_risk'] else '❌'} Mute",
        "ban_high_risk": f"{'✅' if settings['ban_high_risk'] else '❌'} Ban",
    }

    return (
        "⚙️ <b>SecureBot Settings</b>\n\n"
        f"<b>Scanning:</b>\n"
        f"  {status['scan_links']} \n"
        f"  {status['scan_apk']} Files\n\n"
        f"<b>Actions on HIGH Risk:</b>\n"
        f"  {status['delete_high']} Delete Message\n"
        f"  {status['mute_high_risk']} Mute User\n"
        f"  {status['ban_high_risk']} Ban User\n\n"
        f"<b>Other Actions:</b>\n"
        f"  {status['warn_medium']} Warn on Medium Risk\n"
        f"  {status['reply_low']} Reply on Low Risk\n\n"
        f"<b>Bot Status:</b> {status['enabled']}\n"
        f"<b>Log Channel:</b> <code>{log_channel}</code>\n\n"
        "💡 <i>Click buttons to toggle settings</i>"
    )


HELP_TEXT = """
🛡 <b>SecureBot Help</b>

This bot checks in groups:
• links
• APK files

If something looks risky, it will warn you (or delete the message, depending on your settings).

<b>Prepare the bot for your group:</b>
1. In BotFather, set /setprivacy to <b>Disable</b>
2. Add the bot to the group as an admin
3. Grant the bot the <b>Delete messages</b> and <b>Restrict members</b> permissions

<b>Commands:</b>
/settings — view current settings (with inline buttons)
/setlog <code>&lt;chat_id&gt;</code> — set where logs will be sent
/whitelist add <code>&lt;user_id&gt;</code> — exempt a user from checks
/whitelist del <code>&lt;user_id&gt;</code> — remove a user from whitelist
/whitelist list — show the whitelist
/blacklist — reply to a message containing a URL to add that link to the blacklist

<b>Available settings (via /settings):</b>
• Bot Enabled — turn the bot on/off
• Delete High Risk — delete messages for high risk URLs
• Warn Medium Risk — warn for medium risk URLs
• Reply Low Risk — reply for low risk URLs
• Scan Links — scan links in messages
• Scan APK — scan APK files
• Mute High Risk — mute users who share high risk links
• Ban High Risk — ban users who share high risk links

<b>Examples:</b>
/setlog -1001234567890
/whitelist add 123456789
/whitelist del 123456789
/whitelist list

<b>How it works:</b>
1. User shares a link or APK file
2. Bot scans it using:
   - Google Safe Browsing API (if enabled)
   - Custom heuristic scanning
   - URL cache for faster results
3. Depending on the risk level and your settings:
   - Bot may warn the group
   - Bot may delete the message
   - Bot may mute or ban the user
   - Action is logged to your log channel

<b>Risk Levels:</b>
🔴 HIGH (≥60): Definitely risky - often deleted/user actioned
🟡 MEDIUM (30-59): Somewhat risky - usually warned
🟢 LOW (1-29): Minor risks - optionally replied

⚠️ <b>Important:</b> Even if the bot says "no risk found", always be cautious with unknown links.
""".strip()


START_TEXT = """
Hi! I’m <b>SecureBot</b>. 🛡

I help you check links and APK files shared in groups.

<b>Quick Setup:</b>
1. Add me to the group as an admin
2. Grant me these permissions:
   • Delete messages
   • Restrict members
3. In BotFather set <b>/setprivacy → Disable</b>

<b>Features:</b>
✅ Real-time link scanning with Google Safe Browsing API
✅ Custom heuristic analysis
✅ URL caching for fast repeated scans
✅ Mute/Ban high-risk users
✅ Automatic logging
✅ Whitelist support

<b>Get Started:</b>
/help — Full documentation
/settings — Configure with inline buttons
/whitelist add 123456789 — Whitelist a user

🔒 Your groups stay safe with SecureBot!
""".strip()


def setting_updated_text(key: str, enabled: bool) -> str:
    state = "enabled" if enabled else "disabled"
    return f"✅ <b>{key}</b> is {state}."


def setlog_updated_text(chat_id: str) -> str:
    return (
        "✅ Log destination is saved.\n\n"
        f"New log destination: <code>{chat_id}</code>"
    )


def whitelist_add_text(user_id: int, added: bool) -> str:
    if added:
        return f"✅ <code>{user_id}</code> added to whitelist."
    return f"ℹ️ <code>{user_id}</code> is already on the whitelist."


def whitelist_del_text(user_id: int, removed: bool) -> str:
    if removed:
        return f"✅ <code>{user_id}</code> removed from whitelist."
    return f"ℹ️ <code>{user_id}</code> was not found in whitelist."


def whitelist_list_text(user_ids: list[int]) -> str:
    if not user_ids:
        return "📋 Whitelist is empty."

    items = "\n".join(f"• <code>{uid}</code>" for uid in user_ids)
    return f"📋 <b>Whitelist</b>\n\n{items}"


def format_link_scan_result(result: dict) -> str:
    reasons = "\n".join(f"• {reason}" for reason in result["reasons"])

    return (
        f"🔗 <b>Link scan result: {result['level']}</b>\n"
        f"Score: <b>{result['score']}</b>\n\n"
        f"<b>Number of found links:</b> {result['url_count']}\n"
        f"<b>Top link:</b> <code>{result['top_url']}</code>\n\n"
        f"<b>Reasons:</b>\n{reasons}\n\n"
        "ℹ️ This is an automatic risk assessment."
    )


def format_link_warning_for_group(result: dict, full_name: str) -> str:
    reasons = "\n".join(f"• {reason}" for reason in result["reasons"][:4])

    return (
        f"⚠️ <b>Warning</b>\n\n"
        f"User: <b>{full_name}</b>\n"
        f"Result: <b>{result['level']}</b>\n"
        f"Score: <b>{result['score']}</b>\n\n"
        f"<b>Reasons:</b>\n{reasons}\n\n"
        "Please be careful when opening this link."
    )


def format_link_reply_low(result: dict) -> str:
    return (
        f"ℹ️ Link scan: <b>{result['level']}</b>\n"
        f"Score: <b>{result['score']}</b>\n"
        "No strong risk indicators were found, but please stay cautious."
    )


def format_link_deleted_text(result: dict, full_name: str) -> str:
    return (
        f"🗑 <b>Message deleted</b>\n\n"
        f"User: <b>{full_name}</b>\n"
        f"Reason: suspicious link\n"
        f"Level: <b>{result['level']}</b>\n"
        f"Score: <b>{result['score']}</b>"
    )


def format_log_text(chat_title: str, user_id: int, full_name: str, result: dict, action: str) -> str:
    reasons = "\n".join(f"• {reason}" for reason in result["reasons"][:5])

    return (
        "🛡 <b>SecureBot Log</b>\n\n"
        f"<b>Group:</b> {chat_title}\n"
        f"<b>User:</b> {full_name}\n"
        f"<b>User ID:</b> <code>{user_id}</code>\n"
        f"<b>Action:</b> {action}\n"
        f"<b>Level:</b> {result['level']}\n"
        f"<b>Score:</b> {result['score']}\n"
        f"<b>Link:</b> <code>{result['top_url']}</code>\n\n"
        f"<b>Reasons:</b>\n{reasons}"
    )


NOT_ADMIN_TEXT = "⛔ Only group admins can use this command."

UNKNOWN_SETTING_TEXT = (
    "❌ Invalid setting key.\n\n"
    "Valid keys:\n"
    "• enabled\n"
    "• delete_high\n"
    "• warn_medium\n"
    "• reply_low\n"
    "• scan_links\n"
    "• scan_apk"
)

SET_USAGE_TEXT = (
    "❌ Wrong command format.\n\n"
    "Correct format:\n"
    "<code>/set scan_links on</code>\n"
    "<code>/set delete_high off</code>"
)

SETLOG_USAGE_TEXT = (
    "❌ Wrong command format.\n\n"
    "Correct format:\n"
    "<code>/setlog -1001234567890</code>"
)

WHITELIST_USAGE_TEXT = (
    "❌ Wrong command format.\n\n"
    "Correct examples:\n"
    "<code>/whitelist add 123456789</code>\n"
    "<code>/whitelist del 123456789</code>\n"
    "<code>/whitelist list</code>"
)

