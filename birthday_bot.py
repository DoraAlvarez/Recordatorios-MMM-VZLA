"""
Bot de cumpleaños — corre una vez al día desde GitHub Actions.
Lee birthdays.yml, calcula si hoy le toca a alguien (en la zona horaria
configurada) y envía mensaje + multimedia al grupo de Telegram.
"""

import asyncio
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo   # built-in en Python 3.9+

import yaml
from telegram import Bot
from telegram.error import TelegramError


def cargar_config(ruta="birthdays.yml"):
    """Lee y valida el archivo de configuración."""
    with open(ruta, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def parsear_fecha(fecha_str):
    """
    Acepta 'YYYY-MM-DD' o 'MM-DD' y devuelve (mes, día).
    Si recibe 1985-03-14 -> (3, 14). Si recibe 03-14 -> (3, 14).
    """
    partes = str(fecha_str).split("-")
    if len(partes) == 3:
        _, mes, dia = partes
    elif len(partes) == 2:
        mes, dia = partes
    else:
        raise ValueError(f"Formato de fecha inválido: {fecha_str}")
    return int(mes), int(dia)


def calcular_edad(fecha_str, hoy):
    """Si la fecha incluye año, devuelve la edad que cumple hoy. Si no, None."""
    partes = str(fecha_str).split("-")
    if len(partes) != 3:
        return None
    año, mes, dia = map(int, partes)
    edad = hoy.year - año
    return edad


async def enviar_evento(bot, chat_id, evento, edad):
    """Envía el mensaje con su multimedia adjunta (si la tiene)."""
    caption = evento["message"]
    if edad is not None and edad > 0:
        caption = f"🎂 {evento['name']} cumple {edad} hoy.\n\n{caption}"

    media_type = evento.get("media_type", "none")
    media_id = evento.get("media_id")

    try:
        if media_type == "video" and media_id:
            await bot.send_video(chat_id=chat_id, video=media_id, caption=caption)
        elif media_type == "photo" and media_id:
            await bot.send_photo(chat_id=chat_id, photo=media_id, caption=caption)
        elif media_type == "animation" and media_id:
            await bot.send_animation(chat_id=chat_id, animation=media_id, caption=caption)
        else:
            await bot.send_message(chat_id=chat_id, text=caption)
        print(f"✅ Enviado: {evento['name']}")
    except TelegramError as e:
        print(f"❌ Error enviando {evento['name']}: {e}", file=sys.stderr)
        # Si falla la multimedia, intenta enviar al menos el texto
        try:
            await bot.send_message(chat_id=chat_id, text=caption)
            print(f"   (texto enviado como fallback)")
        except TelegramError as e2:
            print(f"   También falló el fallback: {e2}", file=sys.stderr)


async def main():
    # Credenciales: NUNCA en el código. Vienen de GitHub Secrets.
    token = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    config = cargar_config()
    tz = ZoneInfo(config["timezone"])
    hoy = datetime.now(tz).date()
    print(f"Hoy es {hoy.isoformat()} en {config['timezone']}")

    bot = Bot(token=token)

    coincidencias = []
    for evento in config["events"]:
        mes, dia = parsear_fecha(evento["date"])
        # Caso especial 29 de febrero: en años no bisiestos, lo movemos al 28.
        if mes == 2 and dia == 29:
            try:
                fecha_evento = hoy.replace(month=2, day=29)
            except ValueError:
                fecha_evento = hoy.replace(month=2, day=28)
            if hoy == fecha_evento:
                coincidencias.append(evento)
                continue
        if hoy.month == mes and hoy.day == dia:
            coincidencias.append(evento)

    if not coincidencias:
        print("No hay cumpleaños hoy. Saliendo.")
        return

    print(f"Cumpleaños hoy: {[e['name'] for e in coincidencias]}")
    for evento in coincidencias:
        edad = calcular_edad(evento["date"], hoy)
        await enviar_evento(bot, chat_id, evento, edad)


if __name__ == "__main__":
    asyncio.run(main())
