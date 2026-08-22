import os
import random
import string
import time
import json
from datetime import datetime
import threading
from flask import Flask, render_template_string, session
import discord
from discord.ext import commands
from discord import app_commands
import requests
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
API_KEY = os.getenv('API_KEY')
API_URL = "https://dichvu.c25tool.net/api/v2"

LINK4M_API_TOKEN = os.getenv('LINK4M_TOKEN', '6a892205f14926198544e441')
WEB_DOMAIN = os.getenv('WEB_DOMAIN', 'https://botc25bynghuydiy.onrender.com')

OWNER_ID = 1530913781515812925
ADMIN_IDS = [1530913781515812925]

KEYS_DATABASE = {}
USER_EXPIRATION = {}
SERVICES_CACHE = []

# ==================== ĐỌC VÀ LƯU TIN NHẮN TỪ JSON ====================
MESSAGES_FILE = "messages.json"

def load_messages():
    default_msgs = {
        "msg_getkey_menu": "🔑 **CHỌN GÓI VƯỢT LINK LINK4M ĐỂ NẠP KEY:**",
        "msg_getkey_success": "🔗 **LINK LẤY KEY ({minutes} PHÚT):**\n👉 Link vượt key của bạn: {short_url}\n\n📌 *Hướng dẫn:* Hoàn thành link vượt trên để lấy key, sau đó dùng lệnh `/nhapkey <Mã-Key>` để sử dụng Bot trong **{minutes} phút**.\n-----------------------------------------\n💬 **Mua Key VIP:** Contact <@{owner_id}> để không cần vượt link!",
        "msg_nhapkey_invalid": "❌ **Key không hợp lệ** hoặc không tồn tại trên hệ thống!",
        "msg_nhapkey_used": "⚠️ **Key này đã được sử dụng rồi!**",
        "msg_nhapkey_success": "🎉 **KÍCH HOẠT KEY THÀNH CÔNG!**\n👤 Người dùng: <@{user_id}>\n🔑 Key: `{key}`\n⏰ Hạn sử dụng: **{minutes} Phút** (Đến: `{time_str}`)",
        "msg_not_authorized": "❌ Bạn cần nhập key để dùng bot! Dùng `/getkey` để lấy key.",
        "msg_owner_only": "❌ Chỉ **Chủ Bot** mới có quyền dùng lệnh này!",
        "msg_order_confirm": "⚠️ **XÁC NHẬN ĐẶT ĐƠN**\n\n• **Người đặt:** <@{user_id}>\n• **Dịch vụ:** {service_name} (`#{service_id}`)\n• **Link:** {link}\n• **Số lượng:** `{quantity}`\n👉 **TỔNG TIỀN:** **{total_price}**",
        "msg_order_success": "✅ **ĐẶT ĐƠN THÀNH CÔNG!**\n• Người đặt: <@{user_id}>\n• Mã Đơn Hàng: `{order_id}`\n• Số lượng: `{quantity}`\n• Tổng thanh toán: **{total_price}**"
    }
    if os.path.exists(MESSAGES_FILE):
        try:
            with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_msgs.update(data)
        except Exception as e:
            print(f"Lỗi đọc file JSON: {e}")
    return default_msgs

MSGS = load_messages()

def save_messages():
    try:
        with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
            json.dump(MSGS, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Lỗi lưu file JSON: {e}")
        return False

# ==================== 1. FLASK WEB SERVER ====================
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'secret_key_nghuydiy_1530913781515812925')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lấy Key Kích Hoạt Bot</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 30px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; max-width: 400px; width: 90%; border: 1px solid #334155; }
        h2 { color: #38bdf8; margin-bottom: 10px; }
        p { color: #94a3b8; font-size: 14px; }
        .key-box { background: #0f172a; border: 2px dashed #38bdf8; padding: 15px; border-radius: 8px; font-size: 20px; font-weight: bold; color: #4ade80; letter-spacing: 1px; margin: 20px 0; word-break: break-all; }
        .btn { background: #0284c7; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; text-decoration: none; display: inline-block; }
        .btn:hover { background: #0369a1; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🔑 KEY KÍCH HOẠT BOT</h2>
        <p>Sao chép key bên dưới và dùng lệnh <b>/nhapkey</b> trong Discord để dùng Bot!</p>
        <div class="key-box" id="keyText">{{ key }}</div>
        <button class="btn" onclick="copyKey()">Sao Chép Key</button>
    </div>
    <script>
        function copyKey() {
            var keyText = document.getElementById("keyText").innerText;
            navigator.clipboard.writeText(keyText);
            alert("Đã sao chép Key: " + keyText);
        }
    </script>
</body>
</html>
"""

def generate_random_key():
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"@nghuydiy-{random_str}"

def shorten_link_link4m(destination_url):
    try:
        api_url = f"https://link4m.co/api?api={LINK4M_API_TOKEN}&url={destination_url}"
        res = requests.get(api_url, timeout=10).json()
        if res.get("status") == "success":
            return res.get("shortenedUrl")
    except Exception as e:
        print(f"Lỗi API Link4M: {e}")
    return destination_url

@app.route('/')
def home():
    return "Bot Discord đang hoạt động 24/7!"

@app.route('/getkey-site')
def get_key_site():
    hours = 5.0
    if 'current_key' in session:
        user_key = session['current_key']
        if KEYS_DATABASE.get(user_key, {}).get("used", False):
            new_key = generate_random_key()
            KEYS_DATABASE[new_key] = {"used": False, "hours": hours, "created_at": time.time()}
            session['current_key'] = new_key
            return render_template_string(HTML_TEMPLATE, key=new_key)
        return render_template_string(HTML_TEMPLATE, key=user_key)
    
    new_key = generate_random_key()
    KEYS_DATABASE[new_key] = {"used": False, "hours": hours, "created_at": time.time()}
    session['current_key'] = new_key
    return render_template_string(HTML_TEMPLATE, key=new_key)

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ==================== 2. DISCORD BOT SETUP ====================
class SMMBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Đã đồng bộ Slash Commands thành công!")

bot = SMMBot()

def smm_api_request(data):
    data['key'] = API_KEY
    try:
        response = requests.post(API_URL, data=data, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def is_authorized(user_id: int) -> bool:
    if user_id == OWNER_ID or user_id in ADMIN_IDS:
        return True
    if user_id in USER_EXPIRATION and time.time() < USER_EXPIRATION[user_id]:
        return True
    return False

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def format_money(amount: float) -> str:
    return f"{int(round(amount)):,}".replace(",", ".") + "đ"

@bot.event
async def on_ready():
    print(f'Bot đã sẵn sàng: {bot.user}')

# ==================== 🟢 LỆNH CÔNG KHAI & KEY ====================

@bot.tree.command(name="id", description="Xem Discord User ID của bạn")
async def get_my_id(interaction: discord.Interaction):
    await interaction.response.send_message(f"🆔 **Discord User ID của bạn:** `{interaction.user.id}`")

@bot.tree.command(name="checkquyen", description="Kiểm tra bản thân có quyền dùng bot không")
async def check_permission(interaction: discord.Interaction):
    uid = interaction.user.id
    if is_owner(uid):
        await interaction.response.send_message("👑 Bạn có quyền **Chủ Bot (Owner)** vĩnh viễn!")
    elif uid in ADMIN_IDS:
        await interaction.response.send_message("✅ Bạn có quyền **Admin** sử dụng bot!")
    elif uid in USER_EXPIRATION and time.time() < USER_EXPIRATION[uid]:
        rem = int((USER_EXPIRATION[uid] - time.time()) / 60)
        await interaction.response.send_message(f"⏳ Bạn có quyền dùng bot. Thời gian còn lại: **{rem} phút**.")
    else:
        await interaction.response.send_message(MSGS.get("msg_not_authorized", "❌ Bạn chưa có quyền dùng bot!"))

@bot.tree.command(name="list", description="Xem danh sách tất cả các lệnh")
async def list_commands(interaction: discord.Interaction):
    menu_text = (
        "📜 **DANH SÁCH LỆNH CỦA BOT**\n\n"
        "🟢 **Lệnh công khai:**\n"
        "• `/id` : Xem Discord User ID của bạn\n"
        "• `/checkquyen` : Kiểm tra bản thân có quyền dùng bot không\n"
        "• `/list` : Xem danh sách tất cả các lệnh\n"
        "• `/getkey` : Lấy link vượt key nạp thời gian dùng bot\n"
        "• `/nhapkey` : Kích hoạt key đã vượt link\n\n"
        "👑 **Lệnh Chủ Bot (Owner Only):**\n"
        "• `/danhsachquyen` : Xem chi tiết danh sách người dùng được cấp quyền\n"
        "• `/themquyen` : Cấp quyền dùng bot cho User ID\n"
        "• `/goquyen` : Gỡ quyền dùng bot của User ID\n"
        "• `/suatinnhan` : Chỉnh sửa tin nhắn hệ thống\n\n"
        "💰 **Lệnh Dịch vụ:**\n"
        "• `/check` : Menu chọn dịch vụ Facebook / TikTok đa cấp độ\n"
        "• `/sodu` : Kiểm tra số dư tài khoản web\n"
        "• `/don` : Tra cứu trạng thái đơn hàng\n"
        "• `/dat` : Đặt đơn tùy chỉnh (`id_dich_vu`, `link`, `so_luong`)\n\n"
        "⚡ **Lệnh đặt nhanh (Tối thiểu 50):**\n"
        "• `/fblike` : Tăng Like Facebook (#7376)\n"
        "• `/fbfollow` : Tăng Follow Facebook (#7132)\n"
        "• `/ttlike` : Tăng Like TikTok (#7236)\n"
        "• `/ttview` : Tăng View TikTok (#7240 - Tối thiểu 1000)"
    )
    await interaction.response.send_message(menu_text)

class KeyOptionSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="1 Link - Hạn dùng 30 phút", value="0.5", description="Vượt 1 link Link4M", emoji="⚡"),
            discord.SelectOption(label="2 Link - Hạn dùng 1 tiếng", value="1.0", description="Vượt link nhận key 1 tiếng", emoji="⏱️"),
            discord.SelectOption(label="3 Link - Hạn dùng 5 tiếng", value="5.0", description="Vượt link nhận key 5 tiếng", emoji="🚀"),
        ]
        super().__init__(placeholder="👉 Chọn gói vượt link...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        hours = float(self.values[0])
        short_url = shorten_link_link4m(f"{WEB_DOMAIN}/getkey-site")
        msg = MSGS.get("msg_getkey_success", "").format(minutes=int(hours * 60), short_url=short_url, owner_id=OWNER_ID)
        await interaction.followup.send(msg)

class KeyOptionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(KeyOptionSelect())

@bot.tree.command(name="getkey", description="Lấy link vượt key sử dụng Bot")
async def get_key_command(interaction: discord.Interaction):
    await interaction.response.send_message(MSGS.get("msg_getkey_menu", "🔑 CHỌN GÓI:"), view=KeyOptionView())

@bot.tree.command(name="nhapkey", description="Nhập mã Key để kích hoạt quyền dùng Bot")
@app_commands.describe(key="Mã Key của bạn")
async def redeem_key(interaction: discord.Interaction, key: str):
    await interaction.response.defer()
    key = key.strip()
    if key not in KEYS_DATABASE or KEYS_DATABASE[key]["used"]:
        await interaction.followup.send(MSGS.get("msg_nhapkey_invalid", "❌ Key không hợp lệ hoặc đã dùng!"))
        return

    KEYS_DATABASE[key]["used"] = True
    expire_time = time.time() + (KEYS_DATABASE[key].get("hours", 5.0) * 3600)
    USER_EXPIRATION[interaction.user.id] = expire_time
    
    time_str = datetime.fromtimestamp(expire_time).strftime('%H:%M:%S %d/%m/%Y')
    msg = MSGS.get("msg_nhapkey_success", "").format(user_id=interaction.user.id, key=key, minutes=int(KEYS_DATABASE[key].get("hours", 5.0)*60), time_str=time_str)
    await interaction.followup.send(msg)

# ==================== 👑 LỆNH CHỦ BOT (OWNER ONLY) ====================

@bot.tree.command(name="danhsachquyen", description="Xem chi tiết danh sách người dùng được cấp quyền")
async def list_permissions(interaction: discord.Interaction):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message(MSGS.get("msg_owner_only", "❌ Chỉ Chủ Bot!"))
        return
    msg = f"👑 **Owner ID:** `{OWNER_ID}`\n👥 **Admin IDs:** {ADMIN_IDS}\n\n**Người dùng có hạn:**\n"
    now = time.time()
    for uid, exp in USER_EXPIRATION.items():
        if exp > now:
            rem = int((exp - now) / 60)
            msg += f"• <@{uid}> (`{uid}`): Còn {rem} phút\n"
    await interaction.response.send_message(msg)

@bot.tree.command(name="themquyen", description="Cấp quyền dùng bot cho User ID")
@app_commands.describe(user_id="ID người dùng", phut="Số phút cấp quyền (mặc định 1440 = 24h)")
async def add_permission(interaction: discord.Interaction, user_id: str, phut: int = 1440):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message(MSGS.get("msg_owner_only", "❌ Chỉ Chủ Bot!"))
        return
    try:
        uid = int(user_id)
        USER_EXPIRATION[uid] = time.time() + (phut * 60)
        await interaction.response.send_message(f"✅ Đã cấp quyền dùng bot cho <@{uid}> trong **{phut} phút**!")
    except ValueError:
        await interaction.response.send_message("❌ User ID không hợp lệ!")

@bot.tree.command(name="goquyen", description="Gỡ quyền dùng bot của User ID")
@app_commands.describe(user_id="ID người dùng cần gỡ")
async def remove_permission(interaction: discord.Interaction, user_id: str):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message(MSGS.get("msg_owner_only", "❌ Chỉ Chủ Bot!"))
        return
    try:
        uid = int(user_id)
        if uid in USER_EXPIRATION:
            del USER_EXPIRATION[uid]
            await interaction.response.send_message(f"✅ Đã gỡ quyền dùng bot của <@{uid}>!")
        else:
            await interaction.response.send_message("⚠️ User ID này chưa được cấp quyền tạm thời.")
    except ValueError:
        await interaction.response.send_message("❌ User ID không hợp lệ!")

class EditMessageModal(discord.ui.Modal):
    def __init__(self, key_name: str, current_content: str):
        super().__init__(title=f"Sửa Tin Nhắn: {key_name}")
        self.key_name = key_name
        self.new_content = discord.ui.TextInput(
            label=f"Nội dung key: {key_name}",
            style=discord.TextStyle.paragraph,
            default=current_content,
            required=True,
            max_length=2000
        )
        self.add_item(self.new_content)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        val = self.new_content.value.strip()
        MSGS[self.key_name] = val
        if save_messages():
            await interaction.followup.send(f"✅ **ĐÃ CẬP NHẬT THÀNH CÔNG!**\n🔑 **Key:** `{self.key_name}`\n📝 **Nội dung mới:**\n>>> {val}")
        else:
            await interaction.followup.send("❌ Không thể lưu vào file `messages.json`!")

class SelectKeyToEdit(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=k[:100], description=MSGS[k][:50] + "...", value=k) for k in MSGS.keys()]
        super().__init__(placeholder="📌 Chọn tin nhắn cần chỉnh sửa...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditMessageModal(self.values[0], MSGS.get(self.values[0], "")))

class SelectKeyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(SelectKeyToEdit())

@bot.tree.command(name="suatinnhan", description="[Chủ bot] Sửa tin nhắn hệ thống")
async def edit_msg_command(interaction: discord.Interaction):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message(MSGS.get("msg_owner_only", "❌ Chỉ Chủ Bot!"))
        return
    await interaction.response.send_message("📋 Chọn tin nhắn bạn muốn chỉnh sửa:", view=SelectKeyView())

# ==================== 💰 LỆNH DỊCH VỤ & GIAO DIỆN /CHECK ====================

class ServiceSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Facebook Services", description="Tăng Like, Follow Facebook", emoji="📘", value="fb"),
            discord.SelectOption(label="TikTok Services", description="Tăng Like, View TikTok", emoji="🎵", value="tt"),
            discord.SelectOption(label="Instagram Services", description="Tăng Like, Follow Instagram", emoji="📸", value="ig"),
            discord.SelectOption(label="YouTube Services", description="Tăng Sub, View YouTube", emoji="🔴", value="yt"),
        ]
        super().__init__(placeholder="📌 Chọn nền tảng dịch vụ bạn muốn dùng...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected = self.values[0]
        
        if selected == "fb":
            msg = (
                "📘 **DỊCH VỤ FACEBOOK ĐA CẤP ĐỘ:**\n"
                "• `/fblike <link> <so_luong>` — Tăng Like bài viết (#7376)\n"
                "• `/fbfollow <link> <so_luong>` — Tăng Sub/Follow Trang cá nhân (#7132)\n"
                "👉 *Sử dụng lệnh `/dat <id> <link> <so_luong>` để chạy ID tùy chỉnh.*"
            )
        elif selected == "tt":
            msg = (
                "🎵 **DỊCH VỤ TIKTOK ĐA CẤP ĐỘ:**\n"
                "• `/ttlike <link> <so_luong>` — Tăng Like Video TikTok (#7236)\n"
                "• `/ttview <link> <so_luong>` — Tăng View Video TikTok (#7240)\n"
                "👉 *Sử dụng lệnh `/dat <id> <link> <so_luong>` để chạy ID tùy chỉnh.*"
            )
        elif selected == "ig":
            msg = "📸 **DỊCH VỤ INSTAGRAM:**\n• Dùng lệnh `/dat <id> <link> <so_luong>` với ID dịch vụ Instagram."
        elif selected == "yt":
            msg = "🔴 **DỊCH VỤ YOUTUBE:**\n• Dùng lệnh `/dat <id> <link> <so_luong>` với ID dịch vụ YouTube."
        else:
            msg = "❌ Không xác định được lựa chọn."

        await interaction.followup.send(msg)

class CheckMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(ServiceSelect())

@bot.tree.command(name="check", description="Menu chọn dịch vụ Facebook / TikTok đa cấp độ")
async def check_menu(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message(MSGS.get("msg_not_authorized", "❌ Bạn chưa có quyền dùng bot!"))
        return
    await interaction.response.send_message(
        "📌 **MENU CHỌN DỊCH VỤ ĐA CẤP ĐỘ**\nVui lòng chọn nền tảng bên dưới:",
        view=CheckMenuView()
    )

@bot.tree.command(name="sodu", description="Kiểm tra số dư tài khoản web")
async def check_balance(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message(MSGS.get("msg_not_authorized", "❌ Bạn chưa có quyền dùng bot!"))
        return
    await interaction.response.defer()
    res = smm_api_request({'action': 'balance'})
    if 'balance' in res:
        await interaction.followup.send(f"💰 **Số dư tài khoản web:** `{res.get('balance')} {res.get('currency', 'USD')}`")
    else:
        await interaction.followup.send("❌ Lỗi kiểm tra số dư từ API!")

@bot.tree.command(name="don", description="Tra cứu trạng thái đơn hàng")
@app_commands.describe(order_id="Mã đơn hàng cần tra cứu")
async def check_order(interaction: discord.Interaction, order_id: str):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message(MSGS.get("msg_not_authorized", "❌ Bạn chưa có quyền dùng bot!"))
        return
    await interaction.response.defer()
    res = smm_api_request({'action': 'status', 'order': order_id})
    if 'status' in res:
        await interaction.followup.send(f"📦 **Thông tin đơn `#{order_id}`:**\n• Trạng thái: **{res.get('status')}**\n• Đã chạy: `{res.get('start_count')}`\n• Còn lại: `{res.get('remains')}`")
    else:
        await interaction.followup.send("❌ Không tìm thấy mã đơn hàng này!")

@bot.tree.command(name="dat", description="Đặt đơn tùy chỉnh")
@app_commands.describe(id_dich_vu="ID dịch vụ", link="Đường dẫn", so_luong="Số lượng")
async def create_custom_order(interaction: discord.Interaction, id_dich_vu: str, link: str, so_luong: int):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message(MSGS.get("msg_not_authorized", "❌ Bạn chưa có quyền dùng bot!"))
        return
    await interaction.response.defer()
    res = smm_api_request({'action': 'add', 'service': id_dich_vu, 'link': link, 'quantity': so_luong})
    if 'order' in res:
        await interaction.followup.send(f"✅ **ĐẶT ĐƠN THÀNH CÔNG!**\n• Mã đơn: `{res['order']}`\n• ID Dịch vụ: `{id_dich_vu}`\n• Số lượng: `{so_luong:,}`")
    else:
        await interaction.followup.send(f"❌ Lỗi tạo đơn: {res.get('error', 'Lỗi không xác định')}")

# ==================== ⚡ LỆNH ĐẶT NHANH ====================

async def handle_quick_order(interaction: discord.Interaction, service_id: str, link: str, quantity: int, min_qty: int = 50):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message(MSGS.get("msg_not_authorized", "❌ Bạn chưa có quyền dùng bot!"))
        return
    if quantity < min_qty:
        await interaction.response.send_message(f"⚠️ Số lượng tối thiểu cho dịch vụ này là `{min_qty}`!")
        return
    await interaction.response.defer()
    res = smm_api_request({'action': 'add', 'service': service_id, 'link': link, 'quantity': quantity})
    if 'order' in res:
        await interaction.followup.send(f"🚀 **ĐẶT ĐƠN NHANH THÀNH CÔNG!**\n• Mã đơn: `{res['order']}`\n• Số lượng: `{quantity:,}`\n• Link: {link}")
    else:
        await interaction.followup.send(f"❌ Lỗi tạo đơn: {res.get('error', 'Lỗi từ API')}")

@bot.tree.command(name="fblike", description="Tăng Like Facebook (#7376)")
@app_commands.describe(link="Link bài viết Facebook", so_luong="Số lượng (Tối thiểu 50)")
async def fb_like(interaction: discord.Interaction, link: str, so_luong: int):
    await handle_quick_order(interaction, "7376", link, so_luong, min_qty=50)

@bot.tree.command(name="fbfollow", description="Tăng Follow Facebook (#7132)")
@app_commands.describe(link="Link profile/page Facebook", so_luong="Số lượng (Tối thiểu 50)")
async def fb_follow(interaction: discord.Interaction, link: str, so_luong: int):
    await handle_quick_order(interaction, "7132", link, so_luong, min_qty=50)

@bot.tree.command(name="ttlike", description="Tăng Like TikTok (#7236)")
@app_commands.describe(link="Link video TikTok", so_luong="Số lượng (Tối thiểu 50)")
async def tt_like(interaction: discord.Interaction, link: str, so_luong: int):
    await handle_quick_order(interaction, "7236", link, so_luong, min_qty=50)

@bot.tree.command(name="ttview", description="Tăng View TikTok (#7240 - Tối thiểu 1000)")
@app_commands.describe(link="Link video TikTok", so_luong="Số lượng (Tối thiểu 1000)")
async def tt_view(interaction: discord.Interaction, link: str, so_luong: int):
    await handle_quick_order(interaction, "7240", link, so_luong, min_qty=1000)

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
