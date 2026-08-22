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
    return "Bot Discord & Web Key đang hoạt động 24/7!"

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

# ==================== HỆ THỐNG SỬA TIN NHẮN TRỰC QUAN (TEXT VIEW / MODAL) ====================

class EditMessageModal(discord.ui.Modal):
    def __init__(self, key_name: str, current_content: str):
        super().__init__(title=f"Sửa Tin Nhắn: {key_name}")
        self.key_name = key_name

        self.new_content = discord.ui.TextInput(
            label=f"Nội dung của key: {key_name}",
            style=discord.TextStyle.paragraph,
            default=current_content,
            required=True,
            max_length=2000
        )
        self.add_item(self.new_content)

    async def on_submit(self, interaction: discord.Interaction):
        val = self.new_content.value.strip()
        MSGS[self.key_name] = val

        if save_messages():
            await interaction.response.send_message(
                f"✅ **ĐÃ CẬP NHẬT THÀNH CÔNG!**\n"
                f"🔑 **Key:** `{self.key_name}`\n"
                f"📝 **Nội dung mới:**\n>>> {val}",
                ephemeral=False
            )
        else:
            await interaction.response.send_message("❌ **Lỗi:** Không thể lưu vào file `messages.json`!", ephemeral=False)

class SelectKeyToEdit(discord.ui.Select):
    def __init__(self):
        options = []
        for key in MSGS.keys():
            label = key[:100]
            desc = MSGS[key][:50].replace("\n", " ") + "..."
            options.append(discord.SelectOption(label=label, description=desc, value=key))
        
        super().__init__(placeholder="📌 Chọn tin nhắn cần chỉnh sửa...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_key = self.values[0]
        current_text = MSGS.get(selected_key, "")
        await interaction.response.send_modal(EditMessageModal(selected_key, current_text))

class SelectKeyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(SelectKeyToEdit())

@bot.tree.command(name="suatinnhan", description="[Chủ bot] Chọn tin nhắn cần sửa qua danh sách trực quan")
async def edit_msg_command(interaction: discord.Interaction):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message(MSGS.get("msg_owner_only", "❌ Chỉ Chủ Bot mới có quyền!"), ephemeral=False)
        return
    
    await interaction.response.send_message(
        "📋 **Vui lòng chọn câu thông báo/tin nhắn bạn muốn chỉnh sửa từ danh sách bên dưới:**", 
        view=SelectKeyView(), 
        ephemeral=False
    )

# ==================== 3. HỆ THỐNG GETKEY VỚI LINK4M API ====================

class KeyOptionSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="1 Link - Hạn dùng 30 phút", value="0.5", description="Vượt 1 link Link4M để dùng 30 phút", emoji="⚡"),
            discord.SelectOption(label="2 Link - Hạn dùng 1 tiếng", value="1.0", description="Vượt link nhận key dùng 1 tiếng", emoji="⏱️"),
            discord.SelectOption(label="3 Link - Hạn dùng 5 tiếng", value="5.0", description="Vượt link nhận key dùng 5 tiếng", emoji="🚀"),
        ]
        super().__init__(placeholder="👉 Chọn gói vượt link bạn muốn...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        hours = float(self.values[0])
        minutes = int(hours * 60)

        dest_url = f"{WEB_DOMAIN}/getkey-site"
        short_url = shorten_link_link4m(dest_url)

        msg = MSGS.get("msg_getkey_success", "").format(
            minutes=minutes,
            short_url=short_url,
            owner_id=OWNER_ID
        )
        await interaction.followup.send(msg)

class KeyOptionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(KeyOptionSelect())

@bot.tree.command(name="getkey", description="Chọn gói vượt link để nhận Key sử dụng Bot")
async def get_key_command(interaction: discord.Interaction):
    await interaction.response.send_message(MSGS.get("msg_getkey_menu", "🔑 CHỌN GÓI VƯỢT LINK:"), view=KeyOptionView(), ephemeral=False)

@bot.tree.command(name="nhapkey", description="Kích hoạt Key để dùng Bot")
@app_commands.describe(key="Nhập mã Key bạn đã lấy được")
async def redeem_key(interaction: discord.Interaction, key: str):
    key = key.strip()
    if key not in KEYS_DATABASE:
        await interaction.response.send_message(MSGS.get("msg_nhapkey_invalid", "❌ Key không hợp lệ!"), ephemeral=False)
        return

    key_info = KEYS_DATABASE[key]
    if key_info["used"]:
        await interaction.response.send_message(MSGS.get("msg_nhapkey_used", "⚠️ Key này đã dùng!"), ephemeral=False)
        return

    KEYS_DATABASE[key]["used"] = True
    hours_to_add = key_info.get("hours", 5.0)
    expire_time = time.time() + (hours_to_add * 3600)
    USER_EXPIRATION[interaction.user.id] = expire_time

    time_str = datetime.fromtimestamp(expire_time).strftime('%H:%M:%S %d/%m/%Y')
    msg = MSGS.get("msg_nhapkey_success", "").format(
        user_id=interaction.user.id,
        key=key,
        minutes=int(hours_to_add * 60),
        time_str=time_str
    )
    await interaction.response.send_message(msg, ephemeral=False)

# ==================== 4. CÁC LỆNH CÔNG KHAI & TRA CÚU ====================

@bot.tree.command(name="id", description="Xem Discord User ID")
async def get_my_id(interaction: discord.Interaction):
    await interaction.response.send_message(f"🆔 **ID Discord của bạn:** `{interaction.user.id}`", ephemeral=False)

@bot.tree.command(name="checkquyen", description="Kiểm tra thời gian dùng Bot")
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
        await interaction.response.send_message(MSGS.get("msg_not_authorized", "❌ Bạn chưa có quyền!"), ephemeral=False)

# ==================== 5. XÁC NHẬN VÀ TẠO ĐƠN HÀNG ====================

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
            msg = MSGS.get("msg_order_success", "").format(
                user_id=self.user_id,
                order_id=result['order'],
                quantity=f"{self.quantity:,}",
                total_price=format_money(self.total_price)
            )
            await interaction.followup.send(msg)
        else:
            await interaction.followup.send(f"❌ **Lỗi tạo đơn:** {result.get('error', 'Lỗi không xác định.')}")
        self.stop()

    @discord.ui.button(label="🔴 Hủy bỏ", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bạn không phải người tạo yêu cầu!", ephemeral=False)
            return
        await interaction.response.send_message("❌ Đã hủy bỏ đơn hàng.", ephemeral=False)
        self.stop()

async def process_order_with_confirmation(interaction: discord.Interaction, service_id: str, link: str, quantity: int):
    if not SERVICES_CACHE: fetch_services_cache()
    service_info = next((s for s in SERVICES_CACHE if str(s.get('service')) == str(service_id)), None)
    rate_val = float(service_info.get('rate', 0)) if service_info else 0
    service_name = service_info.get('name', f'Dịch vụ ID #{service_id}') if service_info else f'Dịch vụ ID #{service_id}'
    total_price = (rate_val / 1000.0) * quantity

    confirm_msg = MSGS.get("msg_order_confirm", "").format(
        user_id=interaction.user.id,
        service_name=service_name,
        service_id=service_id,
        link=link,
        quantity=f"{quantity:,}",
        total_price=format_money(total_price)
    )
    view = ConfirmOrderView(interaction.user.id, service_id, link, quantity, total_price)
    await interaction.followup.send(confirm_msg, view=view)

@bot.tree.command(name="dat", description="Đặt đơn dịch vụ bất kỳ")
async def place_order(interaction: discord.Interaction, id_dich_vu: str, link: str, so_luong: int):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message(MSGS.get("msg_not_authorized", "❌ Chưa có quyền!"), ephemeral=False)
        return
    if so_luong < 50:
        await interaction.response.send_message("⚠️ Số lượng tối thiểu là **50**!", ephemeral=False)
        return
    await interaction.response.defer()
    await process_order_with_confirmation(interaction, id_dich_vu, link, so_luong)

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
