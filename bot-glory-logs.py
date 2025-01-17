import os
import re
import html
from io import StringIO
from urllib.parse import urlparse
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)
from telegram.constants import ParseMode

# TOKEN DO BOT
telbot = "7962833687:AAGv8E6p9gC2MSjpRHukV7SeMRiCR6xiaRM"

# DIRETÓRIO BASE
dirzao = r"E:\Tailon\Download\Temporários\split-zdg"

# CAMINHO DO BANNER
banner_path = r"E:\Tailon\Documents\Bot DB Filters\GloryLogs - Source\bg\bg.png"

userbot = {}

# ID do administrador
ADMIN_USER_ID = 5486349822  # Substitua pelo ID real do administrador


def parse_search_query(query):
    pattern = r"(?P<operator>inurl:|intext:|site:|filetype:)?(?P<term>\"[^\"]+\"|\S+)"
    criteria = []
    for match in re.finditer(pattern, query):
        op = match.group("operator")
        term = match.group("term")
        if term.startswith('"') and term.endswith('"'):
            term = term.strip('"')
            if not op:
                op = "phrase"
            else:
                op = op[:-1]
        else:
            if op:
                op = op[:-1]
                term = term.strip('"')
            else:
                op = "term"
                term = term.strip('"')
        criteria.append((op.lower(), term))
    return criteria


def extract_domain(url):
    try:
        parsed_url = urlparse(url)
        return parsed_url.netloc
    except Exception:
        return url  # Retorna a URL inteira se falhar ao extrair o domínio


def line_matches_criteria(url, user, password, criteria):
    for op, term in criteria:
        term_lower = term.lower()
        if op == "inurl":
            if term_lower not in url.lower():
                return False
        elif op == "site":
            domain = extract_domain(url).lower()
            if term_lower not in domain:
                return False
        elif op == "filetype":
            if not url.lower().endswith("." + term_lower):
                return False
        elif op == "intext":
            if term_lower not in user.lower() and term_lower not in password.lower():
                return False
        elif op == "phrase":
            if (
                term_lower not in url.lower()
                and term_lower not in user.lower()
                and term_lower not in password.lower()
            ):
                return False
        elif op == "term":
            if (
                term_lower not in url.lower()
                and term_lower not in user.lower()
                and term_lower not in password.lower()
            ):
                return False
        else:
            return False
    return True


def parse_line(linha):
    linha = linha.strip()
    parts = linha.rsplit(":", 2)
    if len(parts) == 3:
        url, user, senha = parts
        return url, user, senha
    else:
        return None

def format_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    p = size_bytes
    while p >= 1024 and i < len(size_name) - 1:
        p /= 1024.0
        i += 1
    return f"{p:.2f} {size_name[i]}"

async def searchlogs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ VOCÊ NÃO TEM PERMISSÃO SUFICIENTE PARA USAR ESSE BOT, FAVOR ENTRAR EM CONTATO COM @Prometheust"
        )
        return

    search_query = " ".join(context.args) if len(context.args) > 0 else None

    if not search_query:
        await update.message.reply_text(
            "✅ Por favor, forneça um termo de pesquisa\nEx: /search youtube"
        )
        return

    criteria = parse_search_query(search_query)
    resultados = []

    for root, dirs, files in os.walk(dirzao):
        for file in files:
            if file.endswith(".txt"):
                caminhone = os.path.join(root, file)

                try:
                    with open(caminhone, "r", encoding="utf-8") as f:
                        conteudo = f.read()
                except UnicodeDecodeError:
                    try:
                        with open(caminhone, "r", encoding="latin-1") as f:
                            conteudo = f.read()
                    except UnicodeDecodeError:
                        continue

                linhas = conteudo.splitlines()
                for linha in linhas:
                    partes = parse_line(linha)
                    if partes:
                        url, user, senha = partes
                        if line_matches_criteria(url, user, senha, criteria):
                            resultados.append(linha)
                    else:
                        continue

    total = len(resultados)

    if total > 0:
        userbot[user_id] = {
            "termo": search_query,
            "offset": 0,
            "resultados": resultados,
            "message_id": None,
            "chat_id": update.effective_chat.id,
        }
        await enviar_pagina(update, context, user_id)
    else:
        resposta = f"❌ Nenhum resultado encontrado para: {search_query}"
        await update.message.reply_text(resposta)


async def enviar_pagina(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> None:
    estado = userbot[user_id]
    resultados = estado["resultados"]
    offset = estado["offset"]
    termo = estado["termo"]
    total = len(resultados)

    total_pages = (total + 29) // 30
    current_page = offset // 30 + 1
    fim = min(offset + 30, total)
    resultados_mostrados = resultados[offset:fim]

    resposta = f"<i>🔎 | SUA PESQUISA RETORNOU {total} RESULTADOS TOTAIS, EXIBINDO ({current_page}/{total_pages}):</i>\n\n"

    for linha in resultados_mostrados:
        partes = parse_line(linha)
        if partes:
            url, user, senha = partes
            url = html.escape(url)
            user = html.escape(user)
            senha = html.escape(senha)
            resposta += f"🧭: <code>{url}</code>\n👤: <code>{user}</code>\n🔑: <code>{senha}</code>\n-\n"
        else:
            linha = html.escape(linha)
            resposta += f"{linha}\n-\n"

    # Cria os botões de navegação
    keyboard = []
    if current_page > 1:
        keyboard.append(InlineKeyboardButton("⬅ --- ᴘʀᴇᴠ", callback_data="prev"))
    if current_page < total_pages:
        keyboard.append(InlineKeyboardButton("ᴘʀᴏx --- ➡", callback_data="next"))
    
    # Adiciona o botão de download
    keyboard.append(InlineKeyboardButton("⏬🗂️", callback_data="download"))

    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None

    if estado["message_id"] is None:
        mensagem = await context.bot.send_message(
            chat_id=estado["chat_id"],
            text=resposta,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
        estado["message_id"] = mensagem.message_id
    else:
        await context.bot.edit_message_text(
            chat_id=estado["chat_id"],
            message_id=estado["message_id"],
            text=resposta,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )


async def callback_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    if user_id != ADMIN_USER_ID:
        await query.answer("Você não tem permissão para usar este bot.")
        return

    if user_id not in userbot:
        await query.answer("Nenhuma pesquisa em andamento.")
        return

    estado = userbot[user_id]
    data = query.data

    if data == "next":
        estado["offset"] += 30
    elif data == "prev":
        estado["offset"] -= 30
    elif data == "download":
        await gerar_arquivo_resultados(update, context, user_id)
    await enviar_pagina(update, context, user_id)
    await query.answer()


async def gerar_arquivo_resultados(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    estado = userbot[user_id]
    resultados = estado["resultados"]
    termo = estado["termo"]
    user_name = update.effective_user.username or update.effective_user.first_name

    # Criação do conteúdo do arquivo
    content = f"        ##########################\n        ##########################\n   #####################################\n #########################################\n####      ######################       ####\n###       ######################        ###\n##        ######################        ###\n###     ##########################      ###\n###    ############################    ####\n ###   ### #################### ###    ###\n ####   ### ################## ####  ####\n   ####  ######################### #####\n    ######## ################ #########\n      ######  ##############   ######\n               ############\n                 ########\n                   ####\n                   ####\n                   ####\n                   ####\n############\n            ##################\n            ##################\n            ###            ###\n            ###            ###\n            ###            ###\n            ##################\n            ##################\n          ######################\n         ########################\n\n\nResultados obtidos para ~{termo}~, pelo bot https://t.me/GloryLogsBot \n ---------- by t.me/Prometheust\n\n"


    content += f"Usuário que fez a busca: @{user_name}\n\n"
    content += "-" * 50 + "\n"
    
    for linha in resultados:
        partes = parse_line(linha)
        if partes:
            url, user, senha = partes
            content += f"{url}\n{user}\n{senha}\n-\n"

    content += "-" * 50 + "\n"
    content += "Fim da consulta, continue em t.me/GloryLogsBot\n"

    # Criação do arquivo em memória (StringIO)
    file_obj = StringIO()
    file_obj.write(content)
    file_obj.seek(0)  # Retornar ao início do arquivo

    # Envio do arquivo ao usuário
    await context.bot.send_document(
        chat_id=estado["chat_id"], 
        document=InputFile(file_obj, filename="glory-results.txt")
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ VOCÊ NÃO TEM PERMISSÃO SUFICIENTE PARA USAR ESSE BOT, ENTRE EM CONTATO COM @Prometheust"
        )
        return

    user_name = update.effective_user.username
    if not user_name:
        user_name = update.effective_user.first_name

    mensagem = (
        f"Olá {user_name}, seja bem-vindo!\n\n"
        "<pre>Sou o Bot de consultas 𝐆𝐋𝐎𝐑𝐘 𝐋𝐎𝐆𝐒 👁‍🗨!</pre>\n <i><b>by</b> @Prometheust</i>\n\n"
        "🔍 Para realizar uma consulta, utilize o comando:\n"
        "<b>/search &lt;sua_busca&gt;</b>\n\n"
        "ℹ️ Utilize os operadores de busca avançada para refinar seus resultados:\n\n"
        "<code>inurl:</code> Busca na URL\n"
        "<code>intext:</code> Busca no usuário e senha\n"
        "<code>site:</code> Busca pelo domínio\n"
        "<code>filetype:</code> Busca por extensão de arquivo\n\n"
        "📌 Exemplo: <code>/search intext:facebook inurl:login site:example.com</code>\n\n"
        "<pre>➡️ Use as setas de navegação para ver mais resultados.</pre>\n\n"
        "❓ Para ver todos os comandos disponíveis, digite /help\n\n"
        "👤 Qualquer dúvida, entre em contato com @Prometheust"
    )

    with open(banner_path, "rb") as photo_file:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo_file,
            caption=mensagem,
            parse_mode=ParseMode.HTML,
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text(
            "<pre>❌ VOCÊ NÃO TEM PERMISSÃO SUFICIENTE PARA USAR ESSE BOT, ENTRE EM CONTATO COM @Prometheust</pre>"
        )
        return

    mensagem = (
        "🎯 <b>Comandos Disponíveis:</b>\n\n"
        "🔎 <b>/search &lt;sua_busca&gt;</b> - Realiza uma pesquisa nos logs.\n"
        "ℹ️ <b>/info</b> - Exibe informações sobre a base de dados.\n\n"
        "📄 <b>Operadores de Busca Avançada:</b>\n"
        "<code>inurl:</code> Busca na URL\n"
        "<code>intext:</code> Busca no usuário e senha\n"
        "<code>site:</code> Busca pelo domínio\n"
        "<code>filetype:</code> Busca por extensão de arquivo\n\n"
        "📝 <b>Exemplo:</b> <code>/search intext:\"admin\" site:example.com</code>\n\n"
        "<pre>➡️ Use as setas de navegação para ver mais resultados durante a pesquisa.</pre>\n\n"
        "<pre>⏬🗂️ Faça download do resultado completo da busca.</pre>\n\n"
        "<i>👤 Qualquer dúvida, entre em contato com @Prometheust</i>"
    )

    with open(banner_path, "rb") as photo_file:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo_file,
            caption=mensagem,
            parse_mode=ParseMode.HTML,
        )


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text(
            "<pre>❌ VOCÊ NÃO TEM PERMISSÃO SUFICIENTE PARA USAR ESSE BOT, ENTRE EM CONTATO COM @Prometheust</pre>"
        )
        return

    total_files = 0
    total_lines = 0
    total_valid_entries = 0
    total_size = 0
    last_file_time = None
    last_file_name = None

    for root, dirs, files in os.walk(dirzao):
        for file in files:
            if file.endswith(".txt"):
                total_files += 1
                caminhone = os.path.join(root, file)

                try:
                    with open(caminhone, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                except UnicodeDecodeError:
                    try:
                        with open(caminhone, "r", encoding="latin-1") as f:
                            lines = f.readlines()
                    except UnicodeDecodeError:
                        continue

                total_lines += len(lines)

                for linha in lines:
                    if parse_line(linha):
                        total_valid_entries += 1

                total_size += os.path.getsize(caminhone)

                file_mtime = os.path.getmtime(caminhone)
                if last_file_time is None or file_mtime > last_file_time:
                    last_file_time = file_mtime
                    last_file_name = file

    if last_file_time:
        last_file_date = datetime.fromtimestamp(last_file_time).strftime('%d/%m/%Y %H:%M:%S')
    else:
        last_file_date = "N/A"

    total_size_formatted = format_size(total_size)

    mensagem = (
        f"📊 <b>Informações da Base de Dados:</b>\n\n"
        f"🗂️ Total de arquivos: <b>{total_files}</b>\n"
        f"📄 Total de linhas: <b>{total_lines}</b>\n"
        f"✅ Entradas válidas (URL, USER, PASS): <b>{total_valid_entries}</b>\n"
        f"💾 Tamanho aproximado da base de dados: <b>{total_size_formatted}</b>\n"
        f"📥 Último arquivo adicionado: <b>{last_file_name}</b>\n"
        f"🕒 Data de entrada: <b>{last_file_date}</b>\n"
    )

    await update.message.reply_text(mensagem, parse_mode=ParseMode.HTML)


def main() -> None:
    application = ApplicationBuilder().token(telbot).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", searchlogs))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CallbackQueryHandler(callback_query_handler))

    application.run_polling()


if __name__ == "__main__":
    main()
