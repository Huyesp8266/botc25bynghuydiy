import os
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

USER_EXPIRATION = {}
SERVICES_CACHE = []

# ==================== 1. FLASK WEB SERVER ====================
app = Flask(__name__)
app.secret_key = 'secret_key_nghuydiy'

@app.route('/')
def home():
    return "Bot Discord đang hoạt động 24/7!"

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
        print("Đã đồng bộ Slash Commands!")

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

# ==================== 🟢 LỆNH CÔNG KHAI ====================

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
        await interaction.response.send_message("❌ Bạn chưa được cấp quyền dùng bot!")

@bot.tree.command(name="list", description="Xem danh sách tất cả các lệnh")
async def list_commands(interaction: discord.Interaction):
    menu_text = (
        "📜 **DANH SÁCH LỆNH CỦA BOT**\n\n"
        "🟢 **Lệnh công khai:**\n"
        "• `/id` : Xem Discord User ID của bạn\n"
        "• `/checkquyen` : Kiểm tra bản thân có quyền dùng bot không\n"
        "• `/list` : Xem danh sách tất cả các lệnh\n\n"
        "👑 **Lệnh Chủ Bot (Owner Only):**\n"
        "• `/danhsachquyen` : Xem chi tiết danh sách người dùng được cấp quyền\n"
        "• `/themquyen` : Cấp quyền dùng bot cho User ID\n"
        "• `/goquyen` : Gỡ quyền dùng bot của User ID\n\n"
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

# ==================== 👑 LỆNH CHỦ BOT (OWNER ONLY) ====================

@bot.tree.command(name="danhsachquyen", description="Xem chi tiết danh sách người dùng được cấp quyền")
async def list_permissions(interaction: discord.Interaction):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Chỉ **Chủ Bot** mới có quyền dùng lệnh này!")
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
        await interaction.response.send_message("❌ Chỉ **Chủ Bot** mới có quyền dùng lệnh này!")
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
        await interaction.response.send_message("❌ Chỉ **Chủ Bot** mới có quyền dùng lệnh này!")
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

# ==================== 💰 LỆNH DỊCH VỤ ====================

@bot.tree.command(name="check", description="Menu chọn dịch vụ Facebook / TikTok đa cấp độ")
async def check_menu(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn chưa có quyền dùng bot!")
        return
    await interaction.response.send_message(
        "📌 **MENU DỊCH VỤ ĐA CẤP ĐỘ:**\n"
        "1. Facebook Like (#7376)\n"
        "2. Facebook Follow (#7132)\n"
        "3. TikTok Like (#7236)\n"
        "4. TikTok View (#7240)\n\n"
        "👉 Sử dụng các lệnh đặt nhanh bên dưới để chạy đơn tức thì!"
    )

@bot.tree.command(name="sodu", description="Kiểm tra số dư tài khoản web")
async def check_balance(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn chưa có quyền dùng bot!")
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
        await interaction.response.send_message("❌ Bạn chưa có quyền dùng bot!")
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
        await interaction.response.send_message("❌ Bạn chưa có quyền dùng bot!")
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
        await interaction.response.send_message("❌ Bạn chưa có quyền dùng bot!")
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
