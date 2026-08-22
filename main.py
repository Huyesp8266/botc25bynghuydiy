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

OWNER_ID = 1530913781515812925
ADMIN_IDS = [1530913781515812925]

KEYS_DATABASE = {}
USER_EXPIRATION = {}

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
        "msg_owner_only": "❌ Chỉ **Chủ Bot** mới có quyền dùng lệnh này!"
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
app.secret_key = 'secret_key_nghuydiy_1530913781515812925'

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
        response = requests.post(API_URL, data=data, timeout=15)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def fetch_all_services():
    try:
        res = requests.get(f"{API_URL}?key={API_KEY}&action=services", timeout=15)
        return res.json()
    except Exception as e:
        print(f"Lỗi lấy danh sách dịch vụ API: {e}")
        return []

def is_authorized(user_id: int) -> bool:
    if user_id == OWNER_ID or user_id in ADMIN_IDS:
        return True
    if user_id in USER_EXPIRATION and time.time() < USER_EXPIRATION[user_id]:
        return True
    return False

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

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
        "• `/check` : Menu chọn TOÀN BỘ dịch vụ trên Web theo danh mục\n"
        "• `/sodu` : Kiểm tra số dư tài khoản web\n"
        "• `/don` : Tra cứu trạng thái đơn hàng\n"
        "• `/dat` : Đặt đơn tùy chỉnh (`id_dich_vu`, `link`, `so_luong`)\n\n"
        "⚡ **Lệnh đặt nhanh:**\n"
        "• `/fblike` : Tăng Like Facebook (#7376)\n"
        "• `/fbfollow` : Tăng Follow Facebook (#7132)\n"
        "• `/ttlike` : Tăng Like TikTok (#7236)\n"
        "• `/ttview` : Tăng View TikTok (#7240)"
    )
    await interaction.response.send_message(menu_text)

class KeyOptionSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="1 Link - Hạn dùng 30 phút", value="0.5", description="Vượt link nhận key 30 phút", emoji="⚡"),
            discord.SelectOption(label="2 Link - Hạn dùng 1 tiếng", value="1.0", description="Vượt link nhận key 1 tiếng", emoji="⏱️"),
            discord.SelectOption(label="3 Link - Hạn dùng 5 tiếng", value="5.0", description="Vượt link nhận key 5 tiếng", emoji="🚀"),
        ]
        super().__init__(placeholder="👉 Chọn gói vượt link...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        hours = float(self.values[0])
        fixed_link = "https://link4m.net/oWcrW"
        msg = MSGS.get("msg_getkey_success", "").format(minutes=int(hours * 60), short_url=fixed_link, owner_id=OWNER_ID)
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

# ==================== 💰 TỰ ĐỘNG NẠP TẤT CẢ DỊCH VỤ WEB VÀO /CHECK ====================

class CategorySelect(discord.ui.Select):
    def __init__(self, categorized_services):
        self.categorized_services = categorized_services
        options = []
        for cat in categorized_services.keys():
            options.append(discord.SelectOption(
                label=cat[:100],
                description=f"Xem {len(categorized_services[cat])} dịch vụ thuộc nhóm này",
                emoji="📌"
            ))
        super().__init__(placeholder="👉 Chọn danh mục dịch vụ trên Web...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        cat_name = self.values[0]
        services = self.categorized_services.get(cat_name, [])

        msg = f"📂 **DANH MỤC: {cat_name.upper()}**\n\n"
        for s in services[:15]: # Giới hạn hiển thị 15 dịch vụ tiêu biểu để không vượt quá giới hạn tin nhắn
            rate = f"{float(s.get('rate', 0)):,}đ"
            msg += f"• **ID: `{s.get('service')}`** — {s.get('name')} | Giá: `{rate}` | Min: `{s.get('min')}` - Max: `{s.get('max')}`\n"

        msg += f"\n👉 *Dùng lệnh `/dat <id_dich_vu> <link> <so_luong>` để đặt đơn!*"
        await interaction.followup.send(msg)

class CheckMenuView(discord.ui.View):
    def __init__(self, categorized_services):
        super().__init__(timeout=120)
        self.add_item(CategorySelect(categorized_services))

@bot.tree.command(name="check", description="Menu chọn TOÀN BỘ dịch vụ hiện có trên Web theo danh mục")
async def check_menu(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message(MSGS.get("msg_not_authorized", "❌ Bạn chưa có quyền dùng bot!"))
        return

    await interaction.response.defer()
    all_services = fetch_all_services()

    if not all_services or isinstance(all_services, dict) and "error" in all_services:
        await interaction.followup.send("❌ Không thể kết nối lấy danh sách dịch vụ từ Web!")
        return

    # Tự động gom nhóm tất cả dịch vụ theo Category
    categorized = {}
    for s in all_services:
        cat = s.get('category', 'Dịch vụ khác')
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(s)

    await interaction.followup.send(
        f"🌐 **HỆ THỐNG ĐÃ TẢI THÀNH CÔNG {len(all_services)} DỊCH VỤ TỪ WEB**\nVui lòng chọn Danh Mục bạn muốn xem bên dưới:",
        view=CheckMenuView(categorized)
    )

# ==================== 🛠️ CÁC LỆNH SMM PANEL VÀ ĐẶT ĐƠN ====================

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
