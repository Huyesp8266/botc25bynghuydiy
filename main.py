import os
import discord
from discord.ext import commands
import requests
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
API_KEY = os.getenv('API_KEY') # API Key lấy trên trang web dichvu.c25tool.net
API_URL = "https://dichvu.c25tool.net/api/v2" # Hoặc đường dẫn API đầy đủ hiển thị trong ảnh

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Hàm gửi Request chuẩn SMM Panel v2
def smm_api_request(data):
    data['key'] = API_KEY
    try:
        response = requests.post(API_URL, data=data, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@bot.event
async def on_ready():
    print(f'Bot đã kết nối thành công: {bot.user}')

# 1. Lệnh kiểm tra số dư
@bot.command(name='balance')
async def check_balance(ctx):
    """Kiểm tra số dư tài khoản trên web"""
    payload = {'action': 'balance'}
    result = smm_api_request(payload)
    
    if 'balance' in result:
        await ctx.send(f"💰 **Số dư tài khoản:** {result['balance']} {result.get('currency', '')}")
    else:
        await ctx.send(f"❌ **Lỗi:** {result.get('error', 'Không thể lấy thông tin số dư.')}")

# 2. Lệnh xem danh sách dịch vụ
@bot.command(name='services')
async def get_services(ctx):
    """Lấy danh sách các dịch vụ trên web"""
    payload = {'action': 'services'}
    result = smm_api_request(payload)
    
    if isinstance(result, list):
        # Hiển thị 5 dịch vụ đầu tiên làm ví dụ
        msg = "**Danh sách dịch vụ tiêu biểu:**\n"
        for item in result[:5]:
            msg += f"• **ID {item.get('service')}**: {item.get('name')} - Giá: {item.get('rate')}\n"
        await ctx.send(msg)
    else:
        await ctx.send("❌ Không thể lấy danh sách dịch vụ.")

# 3. Lệnh tạo đơn hàng (Ví dụ: !order <id_dịch_vụ> <link> <số_lượng>)
@bot.command(name='order')
async def create_order(ctx, service_id: str, link: str, quantity: int):
    """Tạo đơn hàng mới: !order <service_id> <link> <quantity>"""
    payload = {
        'action': 'add',
        'service': service_id,
        'link': link,
        'quantity': quantity
    }
    result = smm_api_request(payload)
    
    if 'order' in result:
        await ctx.send(f"✅ **Tạo đơn thành công!** Mã đơn hàng (Order ID): `{result['order']}`")
    else:
        await ctx.send(f"❌ **Tạo đơn thất bại:** {result.get('error', 'Lỗi không xác định')}")

# 4. Lệnh kiểm tra trạng thái đơn hàng
@bot.command(name='status')
async def check_status(ctx, order_id: str):
    """Kiểm tra trạng thái đơn hàng: !status <order_id>"""
    payload = {
        'action': 'status',
        'order': order_id
    }
    result = smm_api_request(payload)
    
    if 'status' in result:
        await ctx.send(f"📋 **Trạng thái đơn `{order_id}`:** {result['status']} | Đã chạy: {result.get('remains', 'N/A')}")
    else:
        await ctx.send(f"❌ Không tìm thấy thông tin đơn hàng.")

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
