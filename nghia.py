import discord
from discord.ext import commands
from discord import app_commands
import time

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Bộ nhớ tạm phục vụ chống spam và nuke
spam_tracking = {}
nuke_channel_tracker = {}
nuke_role_tracker = {}

@bot.event
async def on_ready():
    # Đồng bộ lệnh gạch chéo (Slash Commands) với Discord khi bot online
    try:
        synced = await bot.tree.sync()
        print(f"Đã đồng bộ thành công {len(synced)} lệnh gạch chéo.")
    except Exception as e:
        print(f"Lỗi đồng bộ lệnh: {e}")
    print(f"Bot đã đăng nhập thành công với tên: {bot.user}")

# ==================== 1. HỆ THỐNG AUTO-MOD & CHỐNG SPAM ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Danh sách từ khóa cấm (có thể tùy chỉnh)
    bad_words = ["tục_tĩu_1", "link_lua_dao.com", "hack_robux_mien_phi"]
    content_lower = message.content.lower()

    # Kiểm tra từ ngữ / link độc
    if any(word in content_lower for word in bad_words):
        try:
            await message.delete()
            warning = await message.channel.send(f"⚠️ {message.mention}, tin nhắn của bạn đã bị xóa vì vi phạm quy tắc server!")
            await warning.delete(delay=5)
            return
        except discord.Forbidden:
            pass

    # Kiểm tra chống spam (Gửi > 5 tin nhắn trong vòng 4 giây)
    user_id = message.author.id
    current_time = time.time()
    
    if user_id not in spam_tracking:
        spam_tracking[user_id] = []
    
    spam_tracking[user_id] = [t for t in spam_tracking[user_id] if current_time - t < 4]
    spam_tracking[user_id].append(current_time)

    if len(spam_tracking[user_id]) > 5:
        try:
            await message.delete()
            await message.author.timeout(discord.utils.utcnow() + discord.timedelta(seconds=60), reason="Spam tin nhắn quá nhanh")
            alert = await message.channel.send(f"🔇 {message.mention} đã bị cấm chat 60 giây vì tội spam!")
            await alert.delete(delay=5)
            return
        except discord.Forbidden:
            pass

    await bot.process_commands(message)

# ==================== 2. HỆ THỐNG CHỐNG NUKE (CHỐNG PHÁ SERVER) ====================

@bot.event
async def on_guild_channel_delete(channel):
    guild = channel.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        deleter = entry.user
        if deleter.bot or deleter.id == guild.owner_id:
            return
        
        current_time = time.time()
        if deleter.id not in nuke_channel_tracker:
            nuke_channel_tracker[deleter.id] = []
        
        nuke_channel_tracker[deleter.id].append(current_time)
        recent = [t for t in nuke_channel_tracker[deleter.id] if current_time - t < 10]
        
        if len(recent) > 2:
            try:
                member = guild.get_member(deleter.id)
                if member:
                    await member.ban(reason="Anti-Nuke: Xóa hàng loạt kênh")
                    print(f"[BẢO MẬT] Đã ban khẩn cấp {member.name} vì hành vi xóa kênh phá server!")
            except discord.Forbidden:
                print("Bot thiếu quyền Admin để thực hiện lệnh ban bảo vệ server!")

@bot.event
async def on_guild_role_delete(role):
    guild = role.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        deleter = entry.user
        if deleter.bot or deleter.id == guild.owner_id:
            return
        
        current_time = time.time()
        if deleter.id not in nuke_role_tracker:
            nuke_role_tracker[deleter.id] = []
        
        nuke_role_tracker[deleter.id].append(current_time)
        recent = [t for t in nuke_role_tracker[deleter.id] if current_time - t < 10]
        
        if len(recent) > 2:
            try:
                member = guild.get_member(deleter.id)
                if member:
                    await member.ban(reason="Anti-Nuke: Xóa hàng loạt Role")
                    print(f"[BẢO MẬT] Đã ban khẩn cấp {member.name} vì hành vi xóa role phá server!")
            except discord.Forbidden:
                print("Bot thiếu quyền Admin để thực hiện lệnh ban!")

# ==================== 3. CÁC LỆNH GẠCH XÉO (SLASH COMMANDS) ====================

@bot.tree.command(name="ping", description="Kiểm tra độ trễ của bot")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Độ trễ của bot là `{latency}ms`.")

@bot.tree.command(name="clear", description="Xóa số lượng tin nhắn chỉ định trong kênh")
@app_commands.describe(amount="Số lượng tin nhắn cần xóa (mặc định 5)")
async def clear(interaction: discord.Interaction, amount: int = 5):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Đã xóa thành công `{len(deleted)}` tin nhắn.", ephemeral=True)

@bot.tree.command(name="kick", description="Kick một thành viên ra khỏi server")
@app_commands.describe(member="Thành viên cần kick", reason="Lý do kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return
    
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 Đã kick **{member.name}** khỏi server. Lý do: {reason}")

@bot.tree.command(name="ban", description="Ban vĩnh viễn một thành viên khỏi server")
@app_commands.describe(member="Thành viên cần ban", reason="Lý do ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này!", ephemeral=True)
        return
    
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 Đã ban vĩnh viễn **{member.name}**. Lý do: {reason}")

# Chạy bot (Thay thế 'YOUR_BOT_TOKEN' bằng token mới của bạn)
bot.run("MTUzMzQ4NDY4OTgxNjU1MTQ4NA.G09Piv.mQPjHbm8cBuNg-kw0oImuhXf61ixesxlHRK5LQ")