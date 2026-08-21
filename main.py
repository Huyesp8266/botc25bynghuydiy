import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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
# DANH SÁCH USER ID ĐƯỢC PHÉP DÙNG BOT (ADMIN)
# Điền Discord User ID vào đây. Ví dụ: ADMIN_IDS = [123456789012345678]
# Nếu danh sách trống [], TẤT CẢ mọi người đều có quyền dùng.
# -------------------------------------------------------------
ADMIN_IDS = []

# ==================== 1. WEB SERVER GIẢ LẬP ĐỂ RENDER GIỮ BOT 24/7 ====================

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        response_text = "Bot Discord đang hoạt động 24/7!"
        self.wfile.write(response_text.encode('utf-8'))

    def log_message(self, format, *args):
        return

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    print(f"Đã mở Web Server giả lập thành công trên port {port}")
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()

# ==================== 2. KHỞI TẠO DISCORD BOT ====================

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
    if not ADMIN_IDS:
        return True
    return user_id in ADMIN_IDS

@bot.event
async def on_ready():
    print(f'Bot đã kết nối thành công: {bot.user}')

# ==================== 3. LỆNH CÔNG KHAI (AI CŨNG DÙNG ĐƯỢC) ====================

@bot.tree.command(name="id", description="Xem Discord User ID của bạn")
async def get_my_id(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"🆔 **ID Discord của bạn là:** `{interaction.user.id}`", 
        ephemeral=True
    )

@bot.tree.command(name="checkquyen", description="Kiểm tra bản thân có quyền dùng Bot hay không")
async def check_my_permission(interaction: discord.Interaction):
    if is_authorized(interaction.user.id):
        await interaction.response.send_message(
            f"✅ **{interaction.user.name}**, bạn **ĐƯỢC PHÉP** sử dụng Bot!", 
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ **{interaction.user.name}**, bạn **KHÔNG CÓ QUYỀN** sử dụng Bot!", 
            ephemeral=True
        )

@bot.tree.command(name="list", description="Hiển thị danh sách tất cả các lệnh của Bot")
async def list_commands(interaction: discord.Interaction):
    help_text = (
        "📜 **DANH SÁCH LỆNH CỦA BOT**\n\n"
        "🟢 **Lệnh công khai:**\n"
        "• `/id` : Xem Discord User ID của bạn\n"
        "• `/checkquyen` : Kiểm tra bản thân có quyền dùng bot không\n"
        "• `/list` : Xem danh sách các lệnh\n\n"
        "🔑 **Lệnh quản lý quyền:**\n"
        "• `/danhsachquyen` : Xem danh sách ID có quyền dùng bot\n"
        "• `/themquyen` : Cấp quyền dùng bot cho User ID\n"
        "• `/goquyen` : Gỡ quyền dùng bot của User ID\n\n"
        "💰 **Lệnh Dịch vụ:**\n"
        "• `/sodu` : Kiểm tra số dư tài khoản web\n"
        "• `/don` : Tra cứu trạng thái đơn hàng\n"
        "• `/dat` : Đặt đơn tùy chỉnh (`id_dich_vu`, `link`, `so_luong`)\n\n"
        "⚡ **Lệnh đặt nhanh:**\n"
        "• `/fblike` : Tăng Like Facebook (#7376)\n"
        "• `/fbfollow` : Tăng Follow Facebook (#7132)\n"
        "• `/ttlike` : Tăng Like TikTok (#7236)\n"
        "• `/ttview` : Tăng View TikTok (#7240)"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

# ==================== 4. LỆNH QUẢN LÝ QUYỀN (ADMIN ONLY) ====================

@bot.tree.command(name="danhsachquyen", description="Xem danh sách User ID được phép dùng Bot")
async def list_authorized_users(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return

    if not ADMIN_IDS:
        msg = "🔓 **Chế độ công khai:** Tất cả mọi người đều có thể sử dụng Bot!"
    else:
        msg = "📋 **DANH SÁCH USER ID ĐƯỢC PHÉP DÙNG BOT:**\n"
        for uid in ADMIN_IDS:
            msg += f"• `<@{uid}>` (ID: `{uid}`)\n"
            
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="themquyen", description="Thêm quyền dùng Bot cho một Discord User ID")
@app_commands.describe(user_id="Nhập Discord User ID cần cấp quyền")
async def add_permission(interaction: discord.Interaction, user_id: str):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return

    try:
        uid = int(user_id)
        if uid in ADMIN_IDS:
            await interaction.response.send_message(f"⚠️ User ID `{uid}` đã có quyền từ trước!", ephemeral=True)
        else:
            ADMIN_IDS.append(uid)
            await interaction.response.send_message(f"✅ Đã cấp quyền sử dụng Bot thành công cho User ID: `{uid}`", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("❌ User ID phải là chuỗi các chữ số!", ephemeral=True)

@bot.tree.command(name="goquyen", description="Gỡ quyền dùng Bot của một Discord User ID")
@app_commands.describe(user_id="Nhập Discord User ID cần gỡ quyền")
async def remove_permission(interaction: discord.Interaction, user_id: str):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return

    try:
        uid = int(user_id)
        if uid in ADMIN_IDS:
            ADMIN_IDS.remove(uid)
            await interaction.response.send_message(f"🗑️ Đã gỡ quyền sử dụng Bot của User ID: `{uid}`", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ User ID `{uid}` không có trong danh sách được phép!", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("❌ User ID phải là chuỗi các chữ số!", ephemeral=True)

# ==================== 5. LỆNH DỊCH VỤ (ADMIN ONLY) ====================

@bot.tree.command(name="sodu", description="Kiểm tra số dư tài khoản web")
async def check_balance(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return

    await interaction.response.defer()
    result = smm_api_request({'action': 'balance'})
    
    if 'balance' in result:
        raw_balance = float(result['balance'])
        formatted_balance = f"{raw_balance:,.3f}".rstrip('0').rstrip('.').replace(",", "X").replace(".", ",").replace("X", ".")
        await interaction.followup.send(f"💰 Số dư tài khoản hiện tại: **{formatted_balance} nghìn đồng**")
    else:
        await interaction.followup.send("❌ Không thể tra cứu số dư.")

@bot.tree.command(name="dat", description="Đặt đơn cho bất kỳ dịch vụ phụ nào")
@app_commands.describe(id_dich_vu="Mã ID dịch vụ", link="Đường dẫn bài viết/kênh", so_luong="Số lượng cần tăng")
async def place_order(interaction: discord.Interaction, id_dich_vu: str, link: str, so_luong: int):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return

    await interaction.response.defer()
    payload = {
        'action': 'add',
        'service': id_dich_vu,
        'link': link,
        'quantity': so_luong
    }
    result = smm_api_request(payload)
    
    if 'order' in result:
        await interaction.followup.send(
            f"✅ **ĐẶT ĐƠN THÀNH CÔNG!**\n"
            f"• Mã Dịch Vụ: `{id_dich_vu}`\n"
            f"• Mã Đơn Hàng: `{result['order']}`\n"
            f"• Số lượng: `{so_luong}`"
        )
    else:
        await interaction.followup.send(f"❌ **Lỗi tạo đơn:** {result.get('error', 'Lỗi không xác định.')}")

@bot.tree.command(name="fblike", description="Tăng Like Facebook nhanh (#7376)")
async def fb_like(interaction: discord.Interaction, link: str, so_luong: int = 50):
    await place_order(interaction, "7376", link, so_luong)

@bot.tree.command(name="fbfollow", description="Tăng Follow Facebook nhanh (#7132)")
async def fb_follow(interaction: discord.Interaction, link: str, so_luong: int = 50):
    await place_order(interaction, "7132", link, so_luong)

@bot.tree.command(name="ttlike", description="Tăng Like TikTok nhanh (#7236)")
async def tt_like(interaction: discord.Interaction, link: str, so_luong: int = 50):
    await place_order(interaction, "7236", link, so_luong)

@bot.tree.command(name="ttview", description="Tăng View TikTok nhanh (#7240)")
async def tt_view(interaction: discord.Interaction, link: str, so_luong: int = 1000):
    await place_order(interaction, "7240", link, so_luong)

@bot.tree.command(name="don", description="Tra cứu trạng thái đơn hàng")
@app_commands.describe(order_id="Mã đơn hàng cần kiểm tra")
async def check_status(interaction: discord.Interaction, order_id: str):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return

    await interaction.response.defer()
    result = smm_api_request({'action': 'status', 'order': order_id})
    if 'status' in result:
        await interaction.followup.send(f"📊 Trạng thái đơn `{order_id}`: **{result['status']}** | Còn lại: `{result.get('remains', 'N/A')}`")
    else:
        await interaction.followup.send("❌ Không tìm thấy thông tin đơn hàng này.")

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
