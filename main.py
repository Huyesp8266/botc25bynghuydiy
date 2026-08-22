import os
import random
import string
import time
from datetime import datetime, timedelta
import threading
from flask import Flask, render_template_string
import discord
from discord.ext import commands
from discord import app_commands
import requests
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
API_KEY = os.getenv('API_KEY')
API_URL = "https://dichvu.c25tool.net/api/v2"

# -------------------------------------------------------------
# CẤU HÌNH CỤ THỂ DÀNH CHO BOT CỦA BẠN
# -------------------------------------------------------------
LINK_RUT_GON = "https://link4m.net/go/gLanao"
OWNER_ID = 1530913781515812925  # ID Chủ bot
ADMIN_IDS = [1530913781515812925]  # Danh sách Admin cố định

# Domain Render tự động lấy từ môi trường Render
RENDER_URL = os.getenv('RENDER_EXTERNAL_URL', 'https://your-app.onrender.com')

# Lưu trữ dữ liệu Key & Hạn dùng trong RAM
KEYS_DATABASE = {}
USER_EXPIRATION = {}

# Cache danh sách dịch vụ
SERVICES_CACHE = []

# ==================== 1. FLASK WEB SERVER (LẤY KEY & KEEP ALIVE) ====================

app = Flask(__name__)

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
        <p>Sao chép key bên dưới và dùng lệnh <b>/nhapkey</b> trong Discord để dùng Bot trong 5 tiếng!</p>
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

@app.route('/')
def home():
    return "Bot Discord & Web Key đang hoạt động 24/7!"

@app.route('/getkey-site')
def get_key_site():
    new_key = generate_random_key()
    KEYS_DATABASE[new_key] = {"used": False, "created_at": time.time()}
    return render_template_string(HTML_TEMPLATE, key=new_key)

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ==================== 2. KHỞI TẠO DISCORD BOT ====================

class SMMBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
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

def fetch_services_cache():
    global SERVICES_CACHE
    res = smm_api_request({'action': 'services'})
    if isinstance(res, list):
        SERVICES_CACHE = res

def is_authorized(user_id: int) -> bool:
    if user_id == OWNER_ID or user_id in ADMIN_IDS:
        return True
    
    if user_id in USER_EXPIRATION:
        if time.time() < USER_EXPIRATION[user_id]:
            return True
        else:
            del USER_EXPIRATION[user_id]
    return False

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def format_money(amount: float) -> str:
    return f"{int(round(amount)):,}".replace(",", ".") + "đ"

@bot.event
async def on_ready():
    print(f'Bot đã kết nối thành công: {bot.user}')
    fetch_services_cache()

# ==================== 3. HỆ THỐNG GETKEY & NHẬP KEY ====================

@bot.tree.command(name="getkey", description="Lấy link vượt key để sử dụng Bot 5 tiếng")
async def get_key_command(interaction: discord.Interaction):
    msg = (
        f"🔗 **LINK LẤY KEY SỬ DỤNG BOT (5 TIẾNG):**\n"
        f"👉 Link vượt key: {LINK_RUT_GON}\n\n"
        f"📌 *Hướng dẫn:* Vượt qua link trên để nhận Key, sau đó dùng lệnh `/nhapkey <Mã-Key>` để kích hoạt.\n"
        f"-----------------------------------------\n"
        f"💬 **Bạn Không Muốn Vượt Link ? Mua Key Với Giá 5.000Đ**\n"
        f"📩 Liên hệ ngay Chủ Bot (<@{OWNER_ID}>) để mua Key VIP dùng không cần vượt link!"
    )
    await interaction.response.send_message(msg, ephemeral=False)

@bot.tree.command(name="nhapkey", description="Kích hoạt Key để dùng Bot trong 5 tiếng")
@app_commands.describe(key="Nhập mã Key bạn đã lấy được")
async def redeem_key(interaction: discord.Interaction, key: str):
    key = key.strip()
    if key not in KEYS_DATABASE:
        await interaction.response.send_message("❌ **Key không hợp lệ** hoặc không tồn tại trên hệ thống!", ephemeral=False)
        return

    key_info = KEYS_DATABASE[key]
    if key_info["used"]:
        await interaction.response.send_message("⚠️ **Key này đã được sử dụng rồi!** Mỗi key chỉ kích hoạt được 1 lần.", ephemeral=False)
        return

    KEYS_DATABASE[key]["used"] = True
    expire_time = time.time() + (5 * 3600)
    USER_EXPIRATION[interaction.user.id] = expire_time

    time_str = datetime.fromtimestamp(expire_time).strftime('%H:%M:%S %d/%m/%Y')
    await interaction.response.send_message(
        f"🎉 **KÍCH HOẠT KEY THÀNH CÔNG!**\n"
        f"👤 Người dùng: <@{interaction.user.id}>\n"
        f"🔑 Key: `{key}`\n"
        f"⏰ Hạn sử dụng Bot: **5 Tiếng** (Đến: `{time_str}`)",
        ephemeral=False
    )

@bot.tree.command(name="taokey", description="[Chủ bot] Tạo key ngẫu nhiên dạng @nghuydiy-XXXXXXXX")
async def create_key(interaction: discord.Interaction):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Chỉ **Chủ Bot** mới có quyền dùng lệnh này!", ephemeral=False)
        return

    new_key = generate_random_key()
    KEYS_DATABASE[new_key] = {"used": False, "created_at": time.time()}
    await interaction.response.send_message(f"👑 **Đã tạo Key mới thành công:**\n`{new_key}`", ephemeral=False)

@bot.tree.command(name="taokeycustom", description="[Chủ bot] Tạo key tùy chỉnh theo ý muốn")
@app_commands.describe(key_custom="Nhập mã key tùy chỉnh bạn muốn tạo")
async def create_custom_key(interaction: discord.Interaction, key_custom: str):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Chỉ **Chủ Bot** mới có quyền dùng lệnh này!", ephemeral=False)
        return

    key_custom = key_custom.strip()
    if key_custom in KEYS_DATABASE:
        await interaction.response.send_message("⚠️ Key này đã tồn tại trên hệ thống!", ephemeral=False)
        return

    KEYS_DATABASE[key_custom] = {"used": False, "created_at": time.time()}
    await interaction.response.send_message(f"👑 **Đã tạo Key tùy chỉnh thành công:**\n`{key_custom}`", ephemeral=False)

# ==================== 4. LỆNH CÔNG KHAI & QUẢN LÝ ====================

@bot.tree.command(name="id", description="Xem Discord User ID của bạn")
async def get_my_id(interaction: discord.Interaction):
    await interaction.response.send_message(f"🆔 **ID Discord của bạn là:** `{interaction.user.id}`", ephemeral=False)

@bot.tree.command(name="checkquyen", description="Kiểm tra thời gian dùng Bot còn lại")
async def check_my_permission(interaction: discord.Interaction):
    uid = interaction.user.id
    if is_owner(uid):
        await interaction.response.send_message(f"👑 **{interaction.user.name}**, bạn là **CHỦ BOT (Vĩnh viễn)**!", ephemeral=False)
    elif uid in ADMIN_IDS:
        await interaction.response.send_message(f"✅ **{interaction.user.name}**, bạn là **ADMIN (Vĩnh viễn)**!", ephemeral=False)
    elif uid in USER_EXPIRATION and time.time() < USER_EXPIRATION[uid]:
        remaining = int((USER_EXPIRATION[uid] - time.time()) / 60)
        await interaction.response.send_message(f"⏳ **{interaction.user.name}**, bạn có quyền sử dụng Bot! (Còn lại: **{remaining} phút**)", ephemeral=False)
    else:
        await interaction.response.send_message(f"❌ **{interaction.user.name}**, bạn **CHƯA KÍCH HOẠT KEY** hoặc Key đã hết hạn. Hãy dùng `/getkey` để lấy key!", ephemeral=False)

@bot.tree.command(name="list", description="Hiển thị danh sách tất cả các lệnh")
async def list_commands(interaction: discord.Interaction):
    help_text = (
        "📜 **DANH SÁCH LỆNH CỦA BOT**\n\n"
        "🔑 **Hệ thống Key:**\n"
        "• `/getkey` : Lấy link vượt key sử dụng bot 5 tiếng\n"
        "• `/nhapkey` : Kích hoạt Key nhận được\n"
        "• `/checkquyen` : Kiểm tra thời hạn dùng bot còn lại\n\n"
        "🟢 **Lệnh công khai:**\n"
        "• `/id` : Xem Discord User ID của bạn\n"
        "• `/list` : Xem danh sách lệnh\n\n"
        "👑 **Lệnh Chủ Bot (Owner Only):**\n"
        "• `/taokey` : Tạo Key ngẫu nhiên\n"
        "• `/taokeycustom` : Tạo Key tùy chỉnh\n"
        "• `/danhsachquyen` | `/themquyen` | `/goquyen`\n\n"
        "💰 **Lệnh Dịch vụ & Đặt đơn:**\n"
        "• `/check` : Menu chọn dịch vụ SMM\n"
        "• `/sodu` : Kiểm tra số dư web\n"
        "• `/don` : Tra cứu trạng thái đơn hàng\n"
        "• `/dat` | `/fblike` | `/fbfollow` | `/ttlike` | `/ttview`"
    )
    await interaction.response.send_message(help_text, ephemeral=False)

# ==================== 5. QUẢN LÝ QUYỀN ADMIN ====================

@bot.tree.command(name="danhsachquyen", description="Xem danh sách Admin/Owner")
async def list_authorized_users(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=False)
        return
    await interaction.response.defer(ephemeral=False)
    msg = f"📋 **DANH SÁCH CHỦ BOT & ADMIN CỐ ĐỊNH**\n👑 Owner ID: `{OWNER_ID}`\n👥 Admin IDs: `{ADMIN_IDS}`"
    await interaction.followup.send(msg)

@bot.tree.command(name="themquyen", description="[Chủ bot] Cấp quyền Admin cố định")
async def add_permission(interaction: discord.Interaction, user_id: str):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Chỉ **Chủ Bot** mới có quyền!", ephemeral=False)
        return
    try:
        uid = int(user_id)
        if uid not in ADMIN_IDS:
            ADMIN_IDS.append(uid)
            await interaction.response.send_message(f"✅ Đã cấp quyền Admin cho ID `{uid}`", ephemeral=False)
        else:
            await interaction.response.send_message("⚠️ ID này đã là Admin từ trước!", ephemeral=False)
    except ValueError:
        await interaction.response.send_message("❌ ID không hợp lệ!", ephemeral=False)

@bot.tree.command(name="goquyen", description="[Chủ bot] Gỡ quyền Admin")
async def remove_permission(interaction: discord.Interaction, user_id: str):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Chỉ **Chủ Bot** mới có quyền!", ephemeral=False)
        return
    try:
        uid = int(user_id)
        if uid in ADMIN_IDS:
            ADMIN_IDS.remove(uid)
            await interaction.response.send_message(f"🗑️ Đã gỡ quyền Admin của ID `{uid}`", ephemeral=False)
        else:
            await interaction.response.send_message("⚠️ ID này không nằm trong danh sách Admin!", ephemeral=False)
    except ValueError:
        await interaction.response.send_message("❌ ID không hợp lệ!", ephemeral=False)

# ==================== 6. MENU DROPDOWN TRA CÚU DỊCH VỤ ====================

class CategorySelect(discord.ui.Select):
    def __init__(self, categories, raw_services):
        options = [discord.SelectOption(label=cat[:100], description=f"Xem {cat}"[:100]) for cat in categories[:25]]
        super().__init__(placeholder="📂 Chọn danh mục muốn xem...", options=options)
        self.raw_services = raw_services

    async def callback(self, interaction: discord.Interaction):
        selected_cat = self.values[0]
        matching_services = [s for s in self.raw_services if s.get('category') == selected_cat]
        msg = f"📌 **DANH SÁCH DỊCH VỤ THUỘC:** `{selected_cat.upper()}`\n\n"
        for s in matching_services:
            s_id = s.get('service', 'N/A')
            s_name = s.get('name', 'N/A')
            rate_val = float(s.get('rate', 0))
            msg += f"🔹 **ID:** `{s_id}` | **{s_name}**\n   └── 💰 Giá: `{format_money(rate_val)} / 1k` | Min: `{s.get('min', '1')}` - Max: `{s.get('max', '1000000')}`\n"
            
        if len(msg) > 2000:
            chunks = [msg[i:i+1900] for i in range(0, len(msg), 1900)]
            await interaction.response.send_message(chunks[0], ephemeral=False)
            for chunk in chunks[1:]:
                await interaction.followup.send(chunk, ephemeral=False)
        else:
            await interaction.response.send_message(msg, ephemeral=False)

class CategorySelectView(discord.ui.View):
    def __init__(self, categories, raw_services):
        super().__init__(timeout=120)
        self.add_item(CategorySelect(categories, raw_services))

class PlatformSelect(discord.ui.Select):
    def __init__(self, all_services):
        options = [
            discord.SelectOption(label="Facebook", description="Xem dịch vụ Facebook", emoji="🔵"),
            discord.SelectOption(label="TikTok", description="Xem dịch vụ TikTok", emoji="🎵"),
            discord.SelectOption(label="Tất cả danh mục", description="Xem toàn bộ danh mục", emoji="🌐")
        ]
        super().__init__(placeholder="🌐 Chọn nền tảng muốn kiểm tra...", options=options)
        self.all_services = all_services

    async def callback(self, interaction: discord.Interaction):
        selected_platform = self.values[0].lower()
        categories = []
        keywords = {
            'facebook': ['facebook', 'fb', 'fanpage', 'profile', 'group', 'reels', 'baiviet', 'bài viết'],
            'tiktok': ['tiktok', 'tt', 'douyin']
        }

        for s in self.all_services:
            cat = s.get('category', '')
            if not cat: continue
            cat_lower = cat.lower()
            name_lower = str(s.get('name', '')).lower()

            if selected_platform == 'tất cả danh mục':
                if cat not in categories: categories.append(cat)
            else:
                target_keywords = keywords.get(selected_platform, [selected_platform])
                if any(kw in cat_lower or kw in name_lower for kw in target_keywords):
                    if cat not in categories: categories.append(cat)
                    
        if not categories:
            await interaction.response.send_message(f"❌ Không tìm thấy danh mục nào cho **{self.values[0]}**.", ephemeral=False)
            return

        view = CategorySelectView(categories, self.all_services)
        await interaction.response.send_message(f"✅ Đã tìm thấy **{len(categories)}** danh mục cho **{self.values[0]}**!", view=view, ephemeral=False)

class PlatformSelectView(discord.ui.View):
    def __init__(self, all_services):
        super().__init__(timeout=120)
        self.add_item(PlatformSelect(all_services))

# ==================== 7. XÁC NHẬN VÀ XỬ LÝ ĐẶT ĐƠN ====================

class ConfirmOrderView(discord.ui.View):
    def __init__(self, user_id, service_id, link, quantity, total_price):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.service_id = service_id
        self.link = link
        self.quantity = quantity
        self.total_price = total_price

    @discord.ui.button(label="🟢 Xác nhận đặt", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bạn không phải người tạo yêu cầu này!", ephemeral=False)
            return
        await interaction.response.defer()
        result = smm_api_request({'action': 'add', 'service': str(self.service_id), 'link': self.link, 'quantity': self.quantity})
        if 'order' in result:
            await interaction.followup.send(
                f"✅ **ĐẶT ĐƠN THÀNH CÔNG!**\n"
                f"• Người đặt: <@{self.user_id}>\n"
                f"• Mã Đơn Hàng: `{result['order']}`\n"
                f"• Mã Dịch Vụ: `{self.service_id}`\n"
                f"• Số lượng: `{self.quantity:,}`\n"
                f"• Tổng thanh toán: **{format_money(self.total_price)}**"
            )
        else:
            await interaction.followup.send(f"❌ **Lỗi tạo đơn:** {result.get('error', 'Lỗi không xác định.')}")
        self.stop()

    @discord.ui.button(label="🔴 Hủy bỏ", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bạn không phải người tạo yêu cầu này!", ephemeral=False)
            return
        await interaction.response.send_message("❌ Đã hủy bỏ đơn hàng.", ephemeral=False)
        self.stop()

async def process_order_with_confirmation(interaction: discord.Interaction, service_id: str, link: str, quantity: int):
    if not SERVICES_CACHE: fetch_services_cache()
    service_info = next((s for s in SERVICES_CACHE if str(s.get('service')) == str(service_id)), None)
    rate_val = float(service_info.get('rate', 0)) if service_info else 0
    service_name = service_info.get('name', f'Dịch vụ ID #{service_id}') if service_info else f'Dịch vụ ID #{service_id}'
    total_price = (rate_val / 1000.0) * quantity

    confirm_msg = (
        f"⚠️ **XÁC NHẬN ĐẶT ĐƠN**\n\n"
        f"• **Người đặt:** <@{interaction.user.id}>\n"
        f"• **Dịch vụ:** {service_name} (`#{service_id}`)\n"
        f"• **Link:** {link}\n"
        f"• **Số lượng:** `{quantity:,}`\n"
        f"👉 **TỔNG TIỀN:** **{format_money(total_price)}**\n\n"
        f"Vui lòng nhấn **Xác nhận đặt** bên dưới!"
    )
    view = ConfirmOrderView(interaction.user.id, service_id, link, quantity, total_price)
    await interaction.followup.send(confirm_msg, view=view)

# ==================== 8. LỆNH ĐẶT ĐƠN ====================

@bot.tree.command(name="check", description="Menu tra cứu dịch vụ Facebook & TikTok")
async def check_services(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn cần nhập key để dùng bot! Dùng `/getkey` để lấy key.", ephemeral=False)
        return
    await interaction.response.defer(ephemeral=False)
    fetch_services_cache()
    if isinstance(SERVICES_CACHE, list) and len(SERVICES_CACHE) > 0:
        await interaction.followup.send("🔍 **MENU TRA CÚU DỊCH VỤ SMM**", view=PlatformSelectView(SERVICES_CACHE))
    else:
        await interaction.followup.send("❌ Không thể tra cứu danh sách dịch vụ lúc này.")

@bot.tree.command(name="sodu", description="Kiểm tra số dư tài khoản web")
async def check_balance(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn cần nhập key để dùng bot! Dùng `/getkey` để lấy key.", ephemeral=False)
        return
    await interaction.response.defer()
    result = smm_api_request({'action': 'balance'})
    if 'balance' in result:
        await interaction.followup.send(f"💰 Số dư tài khoản hiện tại: **{format_money(float(result['balance']))}**")
    else:
        await interaction.followup.send("❌ Không thể tra cứu số dư.")

@bot.tree.command(name="dat", description="Đặt đơn cho bất kỳ dịch vụ nào")
async def place_order(interaction: discord.Interaction, id_dich_vu: str, link: str, so_luong: int):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn cần nhập key để dùng bot! Dùng `/getkey` để lấy key.", ephemeral=False)
        return
    if so_luong < 50:
        await interaction.response.send_message("⚠️ Số lượng đặt tối thiểu là **50**!", ephemeral=False)
        return
    await interaction.response.defer()
    await process_order_with_confirmation(interaction, id_dich_vu, link, so_luong)

@bot.tree.command(name="don", description="Tra cứu trạng thái đơn hàng")
async def check_status(interaction: discord.Interaction, order_id: str):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn cần nhập key để dùng bot! Dùng `/getkey` để lấy key.", ephemeral=False)
        return
    await interaction.response.defer()
    result = smm_api_request({'action': 'status', 'order': order_id})
    if 'status' in result:
        await interaction.followup.send(f"📊 Trạng thái đơn `{order_id}`: **{result['status']}** | Còn lại: `{result.get('remains', 'N/A')}`")
    else:
        await interaction.followup.send("❌ Không tìm thấy thông tin đơn hàng này.")

@bot.tree.command(name="fblike", description="Tăng Like Facebook nhanh (#7376)")
async def fb_like(interaction: discord.Interaction, link: str, so_luong: int = 50):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn cần nhập key để dùng bot! Dùng `/getkey` để lấy key.", ephemeral=False)
        return
    if so_luong < 50: return await interaction.response.send_message("⚠️ Số lượng tối thiểu là **50**!", ephemeral=False)
    await interaction.response.defer()
    await process_order_with_confirmation(interaction, "7376", link, so_luong)

@bot.tree.command(name="fbfollow", description="Tăng Follow Facebook nhanh (#7132)")
async def fb_follow(interaction: discord.Interaction, link: str, so_luong: int = 50):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn cần nhập key để dùng bot! Dùng `/getkey` để lấy key.", ephemeral=False)
        return
    if so_luong < 50: return await interaction.response.send_message("⚠️ Số lượng tối thiểu là **50**!", ephemeral=False)
    await interaction.response.defer()
    await process_order_with_confirmation(interaction, "7132", link, so_luong)

@bot.tree.command(name="ttlike", description="Tăng Like TikTok nhanh (#7236)")
async def tt_like(interaction: discord.Interaction, link: str, so_luong: int = 50):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn cần nhập key để dùng bot! Dùng `/getkey` để lấy key.", ephemeral=False)
        return
    if so_luong < 50: return await interaction.response.send_message("⚠️ Số lượng tối thiểu là **50**!", ephemeral=False)
    await interaction.response.defer()
    await process_order_with_confirmation(interaction, "7236", link, so_luong)

@bot.tree.command(name="ttview", description="Tăng View TikTok nhanh (#7240)")
async def tt_view(interaction: discord.Interaction, link: str, so_luong: int = 1000):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn cần nhập key để dùng bot! Dùng `/getkey` để lấy key.", ephemeral=False)
        return
    if so_luong < 1000: return await interaction.response.send_message("⚠️ Số lượng tối thiểu là **1000**!", ephemeral=False)
    await interaction.response.defer()
    await process_order_with_confirmation(interaction, "7240", link, so_luong)

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
