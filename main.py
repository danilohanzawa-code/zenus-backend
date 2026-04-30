"""
🪐 ZENUS — Backend (Bot + API)
Requer: pip install python-telegram-bot==20.7 fastapi uvicorn
"""

import json, os, logging, hashlib, hmac, time
from datetime import datetime, date
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio, threading, uvicorn

# =============================================
#   ⚙️ CONFIGURAÇÕES — EDITE AQUI
# =============================================

BOT_TOKEN    = "8367291634:AAHArFOPmFAWab6QRDG2t5aSBsvw8XsTxCI"
BOT_USERNAME = "ZenusOfficial_bot"
WEBAPP_URL   = "https://zenus-frontend.vercel.app"  # ✅ URL correta do Vercel

REDES_SOCIAIS = {
    "youtube":   {"nome": "YouTube",   "url": "https://youtube.com/@seucanal",     "moedas": 500, "emoji": "▶️"},
    "tiktok":    {"nome": "TikTok",    "url": "https://tiktok.com/@seuperfil",     "moedas": 400, "emoji": "🎵"},
    "instagram": {"nome": "Instagram", "url": "https://instagram.com/danilo.hanm", "moedas": 400, "emoji": "📸"},
    "twitter":   {"nome": "Twitter/X", "url": "https://x.com/seuperfil",           "moedas": 300, "emoji": "🐦"},
}

VIDEOS = [
    {"id": "v1", "titulo": "O que é ZENUS?",     "url": "https://youtu.be/SEU_LINK1", "codigo": "ZEN1", "moedas": 300},
    {"id": "v2", "titulo": "Como ganhar cripto",  "url": "https://youtu.be/SEU_LINK2", "codigo": "ZEN2", "moedas": 300},
]

MISSOES = [
    {"id": "m1", "titulo": "Check-in diário",         "moedas": 50},
    {"id": "m2", "titulo": "Compartilhe o ZENUS",     "moedas": 100},
    {"id": "m3", "titulo": "Visite nosso canal hoje", "moedas": 75},
]

MOEDAS_INICIO    = 100
MOEDAS_REFERRAL  = 200
MOEDAS_CONVIDADO = 100
ARQUIVO          = "zenus_dados.json"

# =============================================
#   💾 DADOS
# =============================================

def carregar():
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar(d):
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

def get_user(d, uid):
    uid = str(uid)
    if uid not in d:
        d[uid] = {
            "nome": "", "moedas": 0,
            "redes_seguidas": [], "videos_assistidos": [],
            "missoes_data": "", "missoes_feitas": [],
            "referral_by": None, "referrals": [],
            "entrou_em": datetime.now().isoformat(),
        }
    return d[uid]

# =============================================
#   🌐 API FASTAPI
# =============================================

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def root():
    return {"status": "ZENUS API online 🪐"}

@app.get("/api/user/{uid}")
async def api_get_user(uid: str):
    d = carregar()
    # ✅ Cria o usuário automaticamente se não existir
    u = get_user(d, uid)
    if not u["nome"]:
        u["nome"] = f"Usuário {uid[:6]}"
        u["moedas"] += MOEDAS_INICIO
        salvar(d)

    hoje = date.today().isoformat()
    missoes_hoje = u["missoes_feitas"] if u["missoes_data"] == hoje else []
    return {
        "uid": uid,
        "nome": u["nome"],
        "moedas": u["moedas"],
        "redes_seguidas": u["redes_seguidas"],
        "videos_assistidos": u["videos_assistidos"],
        "missoes_feitas_hoje": missoes_hoje,
        "referrals": len(u["referrals"]),
        "referral_link": f"https://t.me/{BOT_USERNAME}?start={uid}",
        "redes": REDES_SOCIAIS,
        "videos": VIDEOS,
        "missoes": MISSOES,
    }

@app.post("/api/seguir/{uid}/{rede_id}")
async def api_seguir(uid: str, rede_id: str):
    d = carregar()
    u = get_user(d, uid)
    if rede_id in u["redes_seguidas"]:
        return {"ok": False, "msg": "Você já seguiu essa rede!"}
    rede = REDES_SOCIAIS.get(rede_id)
    if not rede:
        raise HTTPException(404, "Rede não encontrada")
    u["redes_seguidas"].append(rede_id)
    u["moedas"] += rede["moedas"]
    salvar(d)
    return {"ok": True, "moedas": u["moedas"], "ganhou": rede["moedas"]}

@app.post("/api/video/{uid}/{video_id}")
async def api_video(uid: str, video_id: str, request: Request):
    body = await request.json()
    codigo = body.get("codigo", "").strip().upper()
    d = carregar()
    u = get_user(d, uid)
    if video_id in u["videos_assistidos"]:
        return {"ok": False, "msg": "Vídeo já assistido!"}
    video = next((v for v in VIDEOS if v["id"] == video_id), None)
    if not video:
        raise HTTPException(404)
    if codigo != video["codigo"].upper():
        return {"ok": False, "msg": "Código incorreto! Assista até o final."}
    u["videos_assistidos"].append(video_id)
    u["moedas"] += video["moedas"]
    salvar(d)
    return {"ok": True, "moedas": u["moedas"], "ganhou": video["moedas"]}

@app.post("/api/missao/{uid}/{missao_id}")
async def api_missao(uid: str, missao_id: str):
    d = carregar()
    u = get_user(d, uid)
    hoje = date.today().isoformat()
    if u["missoes_data"] != hoje:
        u["missoes_data"] = hoje
        u["missoes_feitas"] = []
    if missao_id in u["missoes_feitas"]:
        return {"ok": False, "msg": "Missão já feita hoje!"}
    missao = next((m for m in MISSOES if m["id"] == missao_id), None)
    if not missao:
        raise HTTPException(404)
    u["missoes_feitas"].append(missao_id)
    u["moedas"] += missao["moedas"]
    salvar(d)
    return {"ok": True, "moedas": u["moedas"], "ganhou": missao["moedas"]}

@app.get("/api/ranking")
async def api_ranking():
    d = carregar()
    lista = sorted(d.items(), key=lambda x: x[1].get("moedas", 0), reverse=True)
    return [{"pos": i+1, "nome": u.get("nome","?"), "moedas": u.get("moedas",0)} for i,(uid,u) in enumerate(lista[:20])]

# =============================================
#   🤖 BOT TELEGRAM
# =============================================

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = carregar()
    user = update.effective_user
    uid = str(user.id)
    novo = uid not in d
    u = get_user(d, uid)
    u["nome"] = user.first_name or "Explorador"

    args = ctx.args
    if args and novo:
        ref_id = args[0]
        if ref_id != uid and ref_id in d:
            u["referral_by"] = ref_id
            d[ref_id]["moedas"] += MOEDAS_REFERRAL
            d[ref_id]["referrals"].append(uid)
            u["moedas"] += MOEDAS_CONVIDADO
            try:
                await ctx.bot.send_message(ref_id,
                    f"🎉 *+{MOEDAS_REFERRAL} ZENUS!*\nSeu convite foi aceito por *{u['nome']}*!",
                    parse_mode="Markdown")
            except:
                pass

    if novo and not u.get("referral_by"):
        u["moedas"] += MOEDAS_INICIO

    salvar(d)

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🪐 Abrir ZENUS",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?uid={uid}")
        )
    ]])

    await update.message.reply_text(
        f"🪐 *Bem-vindo ao ZENUS, {u['nome']}!*\n\n"
        f"Complete missões e acumule ZENUS antes do lançamento oficial!\n\n"
        f"💰 Saldo: *{u['moedas']} ZENUS*",
        parse_mode="Markdown",
        reply_markup=kb
    )

# =============================================
#   🚀 INICIAR TUDO
# =============================================

def run_bot():
    """✅ Bot roda em thread separada com event loop próprio"""
    async def _start_bot():
        bot_app = Application.builder().token(BOT_TOKEN).build()
        bot_app.add_handler(CommandHandler("start", start))
        await bot_app.initialize()
        await bot_app.start()
        # ✅ drop_pending_updates evita erro 409 ao reiniciar
        await bot_app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        await asyncio.Event().wait()

    asyncio.run(_start_bot())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # ✅ Bot em thread separada com daemon=True
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()

    # ✅ Aguarda 2s para o bot iniciar sem conflito
    time.sleep(2)

    # ✅ Usa a variável PORT do Railway automaticamente
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
