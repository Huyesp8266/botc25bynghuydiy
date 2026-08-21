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
# CẤU HÌNH QUYỀN VÀ CHỦ BOT (OWNER)
# -------------------------------------------------------------
OWNER_ID = 0  # <--- THAY ID DISCORD CỦA BẠN VÀO ĐÂY

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

def is_authorized(user_id: int) -> bool:
    if not ADMIN_IDS and OWNER_ID == 0:
        return True
    return user_id == OWNER_ID or user_id in ADMIN_IDS

def is_owner(user_id: int) -> bool:
    if OWNER_ID == 0:
        return True
    return user_id == 1530913781515812925

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
    if is_owner(interaction.user.id):
        await interaction.response.send_message(
            f"👑 **{interaction.user.name}**, bạn là **CHỦ BOT (OWNER)**!", 
            ephemeral=True
        )
    elif is_authorized(interaction.user.id):
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
        "• `/list` : Xem danh sách tất cả các lệnh\n\n"
        "👑 **Lệnh Chủ Bot (Owner Only):**\n"
        "• `/danhsachquyen` : Xem chi tiết danh sách người dùng được cấp quyền\n"
        "• `/themquyen` : Cấp quyền dùng bot cho User ID\n"
        "• `/goquyen` : Gỡ quyền dùng bot của User ID\n\n"
        "💰 **Lệnh Dịch vụ:**\n"
        "• `/sodu` : Kiểm tra số dư tài khoản web\n"
        "• `/don` : Tra cứu trạng thái đơn hàng\n"
        "• `/dat` : Đặt đơn tùy chỉnh (`id_dich_vu`, `link`, `so_luong`)\n\n"
        "⚡ **Lệnh đặt nhanh (Tối thiểu 50):**\n"
        "• `/fblike` : Tăng Like Facebook (#7376)\n"
        "• `/fbfollow` : Tăng Follow Facebook (#7132)\n"
        "• `/ttlike` : Tăng Like TikTok (#7236)\n"
        "• `/ttview` : Tăng View TikTok (#7240 - Tối thiểu 1000)"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

# ==================== 4. LỆNH QUẢN LÝ QUYỀN (CHỈ CHỦ BOT DÙNG ĐƯỢC) ====================

@bot.tree.command(name="danhsachquyen", description="Xem danh sách chi tiết người dùng được phép sử dụng Bot")
async def list_authorized_users(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    msg = "📋 **DANH SÁCH NGƯỜI DÙNG ĐƯỢC PHÉP SỬ DỤNG BOT**\n\n"
    
    if OWNER_ID != 0:
        try:
            owner_user = await bot.fetch_user(OWNER_ID)
            msg += f"👑 **Chủ Bot (Owner):**\n• Tên: **{owner_user.name}** (`{owner_user}`)\n• ID: `{OWNER_ID}`\n\n"
        except Exception:
            msg += f"👑 **Chủ Bot (Owner):** ID `{OWNER_ID}`\n\n"
    
    if not ADMIN_IDS:
        msg += "🔓 **Chế độ:** Chưa có Admin nào được thêm."
    else:
        msg += "👥 **Danh sách Admin/Người dùng được cấp quyền:**\n"
        for idx, uid in enumerate(ADMIN_IDS, start=1):
            try:
                user = await bot.fetch_user(uid)
                msg += f"{idx}. **{user.global_name or user.name}** (@{user.name})\n   └── 🆔 ID: `{uid}`\n"
            except Exception:
                msg += f"{idx}. User ID: `{uid}` (Không thể lấy thông tin chi tiết)\n"

    await interaction.followup.send(msg)

@bot.tree.command(name="themquyen", description="[Chủ bot] Thêm quyền dùng Bot cho một Discord User ID")
@app_commands.describe(user_id="Nhập Discord User ID cần cấp quyền")
async def add_permission(interaction: discord.Interaction, user_id: str):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Chỉ **Chủ Bot (Owner)** mới có quyền thêm người dùng!", ephemeral=True)
        return

    try:
        uid = int(user_id)
        if uid in ADMIN_IDS:
            await interaction.response.send_message(f"⚠️ User ID `{uid}` đã có trong danh sách từ trước!", ephemeral=True)
        else:
            ADMIN_IDS.append(uid)
            try:
                user = await bot.fetch_user(uid)
                info = f"**{user.name}** (`{uid}`)"
            except Exception:
                info = f"`{uid}`"
            await interaction.response.send_message(f"✅ Đã cấp quyền sử dụng Bot thành công cho: {info}", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("❌ User ID phải là chuỗi các chữ số!", ephemeral=True)

@bot.tree.command(name="goquyen", description="[Chủ bot] Gỡ quyền dùng Bot của một Discord User ID")
@app_commands.describe(user_id="Nhập Discord User ID cần gỡ quyền")
async def remove_permission(interaction: discord.Interaction, user_id: str):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Chỉ **Chủ Bot (Owner)** mới có quyền gỡ người dùng!", ephemeral=True)
        return

    try:
        uid = int(user_id)
        if uid in ADMIN_IDS:
            ADMIN_IDS.remove(uid)
            await interaction.response.send_message(f"🗑️ Đã gỡ quyền sử dụng Bot của User ID: `{uid}`", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ User ID `{uid}` không có trong danh sách được cấp quyền!", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("❌ User ID phải là chuỗi các chữ số!", ephemeral=True)

# ==================== 5. LỆNH DỊCH VỤ & ĐẶT ĐƠN ====================

@bot.tree.command(name="sodu", description="Kiểm tra số dư tài khoản web")
async def check_balance(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return

    await interaction.response.defer()
    result = smm_api_request({'action': 'balance'})
    
    if 'balance' in result:
        raw_balance = int(float(result['balance']))
        formatted_balance = f"{raw_balance:,}".replace(",", ".")
        await interaction.followup.send(f"💰 Số dư tài khoản hiện tại: **{formatted_balance} nghìn đồng**")
    else:
        await interaction.followup.send("❌ Không thể tra cứu số dư.")

@bot.tree.command(name="dat", description="Đặt đơn cho bất kỳ dịch vụ phụ nào")
@app_commands.describe(id_dich_vu="Mã ID dịch vụ", link="Đường dẫn bài viết/kênh", so_luong="Số lượng cần tăng (tối thiểu 50)")
async def place_order(interaction: discord.Interaction, id_dich_vu: str, link: str, so_luong: int):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return

    if so_luong < 50:
        await interaction.response.send_message("⚠️ Số lượng đặt tối thiểu là **50**!", ephemeral=True)
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

# ==================== 6. LỆNH ĐẶT NHANH ====================

@bot.tree.command(name="fblike", description="Tăng Like Facebook nhanh (#7376 - Tối thiểu 50)")
@app_commands.describe(link="Đường dẫn bài viết Facebook", so_luong="Số lượng cần tăng (tối thiểu 50)")
async def fb_like(interaction: discord.Interaction, link: str, so_luong: int = 50):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return
    if so_luong < 50:
        await interaction.response.send_message("⚠️ Số lượng đặt tối thiểu là **50**!", ephemeral=True)
        return
    await interaction.response.defer()
    payload = {'action': 'add', 'service': "7376", 'link': link, 'quantity': so_luong}
    result = smm_api_request(payload)
    if 'order' in result:
        await interaction.followup.send(f"✅ **ĐẶT LIKE FB THÀNH CÔNG!**\n• Mã Đơn: `{result['order']}`\n• Số lượng: `{so_luong}`")
    else:
        await interaction.followup.send(f"❌ **Lỗi:** {result.get('error', 'Lỗi tạo đơn.')}")

@bot.tree.command(name="fbfollow", description="Tăng Follow Facebook nhanh (#7132 - Tối thiểu 50)")
@app_commands.describe(link="Đường dẫn trang/trang cá nhân FB", so_luong="Số lượng cần tăng (tối thiểu 50)")
async def fb_follow(interaction: discord.Interaction, link: str, so_luong: int = 50):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return
    if so_luong < 50:
        await interaction.response.send_message("⚠️ Số lượng đặt tối thiểu là **50**!", ephemeral=True)
        return
    await interaction.response.defer()
    payload = {'action': 'add', 'service': "7132", 'link': link, 'quantity': so_luong}
    result = smm_api_request(payload)
    if 'order' in result:
        await interaction.followup.send(f"✅ **ĐẶT FOLLOW FB THÀNH CÔNG!**\n• Mã Đơn: `{result['order']}`\n• Số lượng: `{so_luong}`")
    else:
        await interaction.followup.send(f"❌ **Lỗi:** {result.get('error', 'Lỗi tạo đơn.')}")

@bot.tree.command(name="ttlike", description="Tăng Like TikTok nhanh (#7236 - Tối thiểu 50)")
@app_commands.describe(link="Đường dẫn video TikTok", so_luong="Số lượng cần tăng (tối thiểu 50)")
async def tt_like(interaction: discord.Interaction, link: str, so_luong: int = 50):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return
    if so_luong < 50:
        await interaction.response.send_message("⚠️ Số lượng đặt tối thiểu là **50**!", ephemeral=True)
        return
    await interaction.response.defer()
    payload = {'action': 'add', 'service': "7236", 'link': link, 'quantity': so_luong}
    result = smm_api_request(payload)
    if 'order' in result:
        await interaction.followup.send(f"✅ **ĐẶT LIKE TIKTOK THÀNH CÔNG!**\n• Mã Đơn: `{result['order']}`\n• Số lượng: `{so_luong}`")
    else:
        await interaction.followup.send(f"❌ **Lỗi:** {result.get('error', 'Lỗi tạo đơn.')}")

@bot.tree.command(name="ttview", description="Tăng View TikTok nhanh (#7240 - Tối thiểu 1000)")
@app_commands.describe(link="Đường dẫn video TikTok", so_luong="Số lượng cần tăng (tối thiểu 1000)")
async def tt_view(interaction: discord.Interaction, link: str, so_luong: int = 1000):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return
    if so_luong < 1000:
        await interaction.response.send_message("⚠️ Số lượng view TikTok đặt tối thiểu là **1000**!", ephemeral=True)
        return
    await interaction.response.defer()
    payload = {'action': 'add', 'service': "7240", 'link': link, 'quantity': so_luong}
    result = smm_api_request(payload)
    if 'order' in result:
        await interaction.followup.send(f"✅ **ĐẶT VIEW TIKTOK THÀNH CÔNG!**\n• Mã Đơn: `{result['order']}`\n• Số lượng: `{so_luong}`")
    else:
        await interaction.followup.send(f"❌ **Lỗi:** {result.get('error', 'Lỗi tạo đơn.')}")

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
