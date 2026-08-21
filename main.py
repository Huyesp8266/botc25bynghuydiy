import os
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
# DẠNH SÁCH USER ID ĐƯỢC PHÉP DÙNG BOT (Điền Discord User ID vào đây)
# Ví dụ: ADMIN_IDS = [123456789012345678, 987654321098765432]
# -------------------------------------------------------------
ADMIN_IDS = [
    # Nhập User ID của bạn vào đây (dạng số, không để trong dấu ngoặc đơn/kép)
]

class SMMBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
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

# Hàm kiểm tra quyền truy cập
def is_authorized(user_id: int) -> bool:
    if not ADMIN_IDS:
        return True # Nếu chưa điền ID nào trong ADMIN_IDS thì mặc định cho phép dùng
    return user_id in ADMIN_IDS

@bot.event
async def on_ready():
    print(f'Bot đã kết nối: {bot.user}')

# ==================== LỆNH MIỄN PHÍ (AI CŨNG DÙNG ĐƯỢC) ====================

@bot.tree.command(name="id", description="Xem Discord User ID của bạn")
async def get_my_id(interaction: discord.Interaction):
    """Lệnh tra cứu ID công khai"""
    await interaction.response.send_message(
        f"🆔 **ID Discord của bạn là:** `{interaction.user.id}`", 
        ephemeral=True # Chỉ người gửi lệnh mới nhìn thấy
    )

# ==================== LỆNH CẦN CẤP QUYỀN (ADMIN ONLY) ====================

@bot.tree.command(name="sodu", description="Kiểm tra số dư tài khoản web (VNĐ)")
async def check_balance(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return

    await interaction.response.defer()
    result = smm_api_request({'action': 'balance'})
    
    if 'balance' in result:
        # Chuyển đổi từ đơn vị k (nghìn đồng) sang VNĐ đầy đủ
        raw_balance = float(result['balance'])
        real_balance = int(raw_balance * 1000)
        formatted_balance = "{:,}".format(real_balance).replace(",", ".")
        
        await interaction.followup.send(f"💰 Số dư tài khoản hiện tại: **{formatted_balance} VNĐ**")
    else:
        await interaction.followup.send("❌ Không thể tra cứu số dư.")

@bot.tree.command(name="list", description="Xem danh sách dịch vụ theo nền tảng")
@app_commands.choices(nen_tang=[
    app_commands.Choice(name="Facebook", value="facebook"),
    app_commands.Choice(name="TikTok", value="tiktok")
])
async def list_services(interaction: discord.Interaction, nen_tang: app_commands.Choice[str]):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return

    await interaction.response.defer()
    keyword = nen_tang.value
    services = smm_api_request({'action': 'services'})
    
    if not isinstance(services, list):
        await interaction.followup.send("❌ Không thể lấy danh sách dịch vụ.")
        return

    filtered = [s for s in services if keyword in s.get('category', '').lower() or keyword in s.get('name', '').lower()]

    if not filtered:
        await interaction.followup.send(f"❌ Không tìm thấy dịch vụ cho {nen_tang.name}.")
        return

    msg = f"📋 **DANH SÁCH DỊCH VỤ {nen_tang.name.upper()} (15 dịch vụ đầu):**\n"
    for item in filtered[:15]:
        msg += f"• **ID `{item.get('service')}`**: {item.get('name')} | Giá: **{item.get('rate')} đ**\n"
    
    await interaction.followup.send(msg)

@bot.tree.command(name="dat", description="Đặt đơn cho bất kỳ dịch vụ phụ nào")
@app_commands.describe(id_dich_vu="Mã ID dịch vụ", link="Đường dẫn", so_luong="Số lượng")
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
