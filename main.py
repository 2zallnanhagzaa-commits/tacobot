# main.py — Discord 자동 역할 부여 봇 (Slash 전용, 한국어)
# 요구 패키지: discord.py, python-dotenv
# Python 3.13 사용 시: py -m pip install audioop-lts

import os
import json
from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

DATA_FILE = "data.json"


# ---------- 저장소 ----------
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"guilds": {}}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------- 기본 설정 ----------
load_dotenv()
TOKEN = os.getenv("TOKEN")
GUILD_ID = os.getenv("GUILD_ID")  # 선택(길드 동기화 즉시 반영용)

intents = discord.Intents.default()
intents.members = True  # on_member_join용
bot = commands.Bot(command_prefix="!", intents=intents)
store = load_data()


def get_guild_settings(guild_id: int) -> dict:
    return store["guilds"].setdefault(str(guild_id), {})


# ---------- 선택 메뉴 UI ----------
class RoleSelect(discord.ui.Select):
    def __init__(self, roles: List[discord.Role]):
        options = [
            discord.SelectOption(label=r.name[:100], value=str(r.id), description=f"역할: {r.name}"[:100])
            for r in roles
        ]
        super().__init__(
            placeholder="역할을 선택하세요 (중복 선택 가능)",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id="role_select",
        )
        self.role_ids = [str(r.id) for r in roles]

    async def callback(self, interaction: discord.Interaction):
        try:
            member = interaction.guild.get_member(interaction.user.id) or await interaction.guild.fetch_member(interaction.user.id)
            me = interaction.guild.me

            added, removed = [], []
            selected = set(self.values)

            for role_id in self.role_ids:
                role = interaction.guild.get_role(int(role_id)) or await interaction.guild.fetch_role(int(role_id))
                if role is None:
                    continue
                if not (me.guild_permissions.manage_roles and role < me.top_role):
                    continue

                has_role = any(r.id == role.id for r in member.roles)
                should_have = role_id in selected

                if should_have and not has_role:
                    await member.add_roles(role, reason="역할 메뉴 선택 추가")
                    added.append(role.name)
                elif not should_have and has_role:
                    await member.remove_roles(role, reason="역할 메뉴 선택 제거")
                    removed.append(role.name)

            summary = []
            if added:
                summary.append(f"추가: {', '.join(added)}")
            if removed:
                summary.append(f"제거: {', '.join(removed)}")
            await interaction.response.send_message(" | ".join(summary) if summary else "변경 사항 없음.", ephemeral=True)
        except Exception:
            try:
                await interaction.response.send_message("오류가 발생했습니다. 권한/역할 위치를 확인해 주세요.", ephemeral=True)
            except Exception:
                pass


class RoleMenuView(discord.ui.View):
    def __init__(self, roles: List[discord.Role]):
        super().__init__(timeout=None)
        self.add_item(RoleSelect(roles))


# ---------- Slash 명령 ----------
@app_commands.command(name="rolemenu", description="역할 선택 메뉴 메시지를 생성합니다 (최대 5개 역할).")
@app_commands.describe(
    title="메시지 제목",
    role1="역할 #1 (필수)",
    role2="역할 #2 (선택)",
    role3="역할 #3 (선택)",
    role4="역할 #4 (선택)",
    role5="역할 #5 (선택)",
)
@app_commands.default_permissions(administrator=True)
async def rolemenu(
    interaction: discord.Interaction,
    title: str,
    role1: discord.Role,
    role2: Optional[discord.Role] = None,
    role3: Optional[discord.Role] = None,
    role4: Optional[discord.Role] = None,
    role5: Optional[discord.Role] = None,
):
    try:
        perms = interaction.user.guild_permissions
        if not (perms.administrator or perms.manage_guild or perms.manage_roles):
            return await interaction.response.send_message("권한 부족: 관리자/서버관리/역할관리 필요", ephemeral=True)

        roles = [r for r in [role1, role2, role3, role4, role5] if r]
        if not roles:
            return await interaction.response.send_message("최소 1개 이상의 역할을 선택해야 합니다.", ephemeral=True)

        me = interaction.guild.me
        for role in roles:
            if not me.guild_permissions.manage_roles or role >= me.top_role:
                return await interaction.response.send_message(
                    f'봇 역할이 **{role.name}** 보다 위에 있어야 하고, "역할 관리" 권한이 필요합니다.',
                    ephemeral=True,
                )

        embed = discord.Embed(
            title=title,
            description="아래 선택 메뉴에서 역할을 선택/해제하면 자동으로 부여/제거됩니다.",
            color=0x5865F2,
        )
        await interaction.response.send_message(embed=embed, view=RoleMenuView(roles))
    except Exception:
        try:
            await interaction.response.send_message("오류가 발생했습니다.", ephemeral=True)
        except Exception:
            pass


class AutoRoleGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="autorole", description="신규 유저 기본 역할 자동 부여 설정")

    @app_commands.command(name="set-default", description="기본 역할을 설정합니다.")
    @app_commands.describe(role="부여할 기본 역할")
    async def set_default(self, interaction: discord.Interaction, role: discord.Role):
        try:
            perms = interaction.user.guild_permissions
            if not (perms.administrator or perms.manage_guild or perms.manage_roles):
                return await interaction.response.send_message("권한 부족: 관리자/서버관리/역할관리 필요", ephemeral=True)

            me = interaction.guild.me
            if not me.guild_permissions.manage_roles or role >= me.top_role:
                return await interaction.response.send_message(
                    f'봇 역할이 **{role.name}** 보다 위에 있어야 하고, "역할 관리" 권한이 필요합니다.',
                    ephemeral=True,
                )

            g = get_guild_settings(interaction.guild_id)
            g["defaultRoleId"] = str(role.id)
            save_data(store)
            await interaction.response.send_message(f"기본 역할이 **{role.name}** 로 설정되었습니다.", ephemeral=True)
        except Exception:
            try:
                await interaction.response.send_message("오류가 발생했습니다.", ephemeral=True)
            except Exception:
                pass

    @app_commands.command(name="clear-default", description="기본 역할 설정을 해제합니다.")
    async def clear_default(self, interaction: discord.Interaction):
        try:
            g = get_guild_settings(interaction.guild_id)
            g.pop("defaultRoleId", None)
            save_data(store)
            await interaction.response.send_message("기본 역할 설정이 해제되었습니다.", ephemeral=True)
        except Exception:
            try:
                await interaction.response.send_message("오류가 발생했습니다.", ephemeral=True)
            except Exception:
                pass

    @app_commands.command(name="show", description="현재 기본 역할 설정을 확인합니다.")
    async def show(self, interaction: discord.Interaction):
        try:
            g = get_guild_settings(interaction.guild_id)
            rid = g.get("defaultRoleId")
            if rid:
                role = interaction.guild.get_role(int(rid)) or await interaction.guild.fetch_role(int(rid))
                name = role.name if role else "알 수 없음"
                await interaction.response.send_message(f"현재 기본 역할: **{name}**", ephemeral=True)
            else:
                await interaction.response.send_message("현재 기본 역할이 설정되어 있지 않습니다.", ephemeral=True)
        except Exception:
            try:
                await interaction.response.send_message("오류가 발생했습니다.", ephemeral=True)
            except Exception:
                pass


# ---------- 이벤트 ----------
@bot.event
async def on_ready():
    print(f"✅ 로그인 완료: {bot.user}")
    try:
        print("🔎 봇이 들어가 있는 길드:", [(g.name, g.id) for g in bot.guilds])

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            # 초기화 → 재등록 → 동기화(길드 전용)
            bot.tree.clear_commands(guild=guild)
            bot.tree.add_command(rolemenu, guild=guild)
            bot.tree.add_command(AutoRoleGroup(), guild=guild)
            out = await bot.tree.sync(guild=guild)
            print(f"✅ 길드({GUILD_ID}) 슬래시 명령 동기화 완료")
            print("📋 등록된 길드 커맨드:", [c.name for c in out])
        else:
            # 전역 초기화 → 재등록 → 동기화(전역)
            bot.tree.clear_commands()
            bot.tree.add_command(rolemenu)
            bot.tree.add_command(AutoRoleGroup())
            out = await bot.tree.sync()
            print("✅ 전역 슬래시 명령 동기화 완료")
            print("📋 등록된 전역 커맨드:", [c.name for c in out])
    except Exception as e:
        print("슬래시 명령 동기화 실패:", e)


@bot.event
async def on_member_join(member: discord.Member):
    """서버 입장 시 기본 역할 자동 부여"""
    try:
        g = get_guild_settings(member.guild.id)
        rid = g.get("defaultRoleId")
        if not rid:
            return

        role = member.guild.get_role(int(rid)) or await member.guild.fetch_role(int(rid))
        if not role:
            return

        me = member.guild.me
        if not me.guild_permissions.manage_roles or role >= me.top_role:
            print(f"[{member.guild.name}] 기본 역할 부여 실패: 권한/역할 위치 부족")
            return

        await member.add_roles(role, reason="자동 기본 역할 부여")
        print(f"[{member.guild.name}] {member}에게 기본 역할 '{role.name}' 자동 부여")
    except Exception as e:
        print("기본 역할 자동 부여 중 오류:", e)


# ---------- 시작 ----------
if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("환경변수 TOKEN 이 필요합니다. .env를 설정하세요.")
    bot.run(TOKEN)
