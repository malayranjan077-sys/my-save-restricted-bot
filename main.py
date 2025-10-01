import os
     import asyncio
     from pyrogram import Client, filters
     from pyrogram.types import Message
     from decouple import config
     from aiohttp import web

     # Load environment variables
     API_ID = config("API_ID", cast=int)
     API_HASH = config("API_HASH")
     BOT_TOKEN = config("BOT_TOKEN")
     AUTH = config("AUTH", cast=int)
     SOURCE_CHANNEL = -1002809564012  # Ashwani sir
     TARGET_CHANNEL = -1003106111102  # Ashwaaaani sir my savings

     # Initialize bot
     app = Client("save_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

     # Progress callback
     async def progress_callback(current, total, action, msg_id):
         percentage = (current / total) * 100
         print(f"{action} progress for message {msg_id}: {percentage:.1f}%")
         if int(percentage) % 10 == 0:  # Update every 10%
             await app.send_message(TARGET_CHANNEL, f"{action} for message {msg_id}: {percentage:.1f}%")

     # Process a message
     async def process_message(message, msg_id):
         try:
             if message.document or message.video or message.photo:
                 size_mb = (message.document.file_size if message.document else message.video.file_size if message.video else message.photo[-1].file_size) / (1024 * 1024)
                 print(f"Message {msg_id} size: {size_mb:.1f} MB")
                 await app.send_message(TARGET_CHANNEL, f"Downloading message {msg_id} ({size_mb:.1f} MB)...")
                 file_path = await message.download(
                     progress=progress_callback,
                     progress_args=("Download", msg_id)
                 )
                 if file_path and os.path.exists(file_path):
                     file_size = os.path.getsize(file_path) / (1024 * 1024)
                     print(f"Uploading {file_path} ({file_size:.1f} MB)...")
                     if message.document:
                         await app.send_document(
                             TARGET_CHANNEL,
                             file_path,
                             caption=f"From message {msg_id}: {message.caption or ''}",
                             progress=progress_callback,
                             progress_args=("Upload", msg_id)
                         )
                     elif message.video:
                         await app.send_video(
                             TARGET_CHANNEL,
                             file_path,
                             caption=f"From message {msg_id}: {message.caption or ''}",
                             progress=progress_callback,
                             progress_args=("Upload", msg_id)
                         )
                     elif message.photo:
                         await app.send_photo(
                             TARGET_CHANNEL,
                             file_path,
                             caption=f"From message {msg_id}: {message.caption or ''}",
                             progress=progress_callback,
                             progress_args=("Upload", msg_id)
                         )
                     os.remove(file_path)
                 else:
                     await app.send_message(TARGET_CHANNEL, f"Failed to download message {msg_id}")
             elif message.text:
                 print(f"Sending text from message {msg_id}: {message.text[:50]}...")
                 await app.send_message(TARGET_CHANNEL, f"From message {msg_id}: {message.text}")
         except Exception as e:
             print(f"Error with message {msg_id}: {str(e)}")
             await app.send_message(TARGET_CHANNEL, f"Error with message {msg_id}: {str(e)[:100]}")

     # Start command
     @app.on_message(filters.command("start") & filters.user(AUTH))
     async def start(client, message: Message):
         await message.reply(
             "Welcome to your Save Restricted Bot!\n"
             "Commands:\n"
             "/batch <N> - Fetch last N messages\n"
             "/fetch_id <ID> - Fetch message by ID\n"
             "/fetch_range <start_id> <end_id> - Fetch range\n"
             "Or send a message link (e.g., https://t.me/c/2809564012/55)"
         )

     # Batch command
     @app.on_message(filters.command("batch") & filters.user(AUTH))
     async def batch(client, message: Message):
         try:
             n = int(message.command[1])
             if n > 50:
                 await message.reply(f"Fetching {n} messages may take time.")
             print(f"Fetching last {n} messages...")
             count = 0
             async for msg in app.get_chat_history(SOURCE_CHANNEL, limit=n):
                 await process_message(msg, msg.id)
                 count += 1
                 print(f"Processed {count}/{n}...")
                 await asyncio.sleep(5)  # Avoid rate limits
             await message.reply(f"Fetched {count} messages.")
         except Exception as e:
             await message.reply(f"Error: {str(e)[:100]}")

     # Fetch ID command
     @app.on_message(filters.command("fetch_id") & filters.user(AUTH))
     async def fetch_id(client, message: Message):
         try:
             msg_id = int(message.command[1])
             print(f"Fetching message {msg_id}...")
             msg = await app.get_messages(SOURCE_CHANNEL, msg_id)
             if msg:
                 await process_message(msg, msg_id)
                 await message.reply(f"Fetched message {msg_id}.")
             else:
                 await message.reply(f"Message {msg_id} not found.")
         except Exception as e:
             await message.reply(f"Error: {str(e)[:100]}")

     # Fetch range command
     @app.on_message(filters.command("fetch_range") & filters.user(AUTH))
     async def fetch_range(client, message: Message):
         try:
             start_id, end_id = map(int, message.command[1:3])
             min_id, max_id = min(start_id, end_id), max(start_id, end_id)
             total = max_id - min_id + 1
             if total > 50:
                 await message.reply(f"Fetching {total} messages may take time.")
             print(f"Fetching messages {min_id} to {max_id}...")
             count = 0
             async for msg in app.get_chat_history(SOURCE_CHANNEL, limit=total, offset_id=max_id + 1):
                 if min_id <= msg.id <= max_id:
                     await process_message(msg, msg.id)
                     count += 1
                     print(f"Processed {count}/{total}...")
                     await asyncio.sleep(5)
             await message.reply(f"Fetched {count} messages.")
         except Exception as e:
             await message.reply(f"Error: {str(e)[:100]}")

     # Message link handler
     @app.on_message(filters.regex(r"https://t\.me/c/(\d+)/(\d+)") & filters.user(AUTH))
     async def link_handler(client, message: Message):
         try:
             chat_id = -int(message.matches[0].group(1))
             msg_id = int(message.matches[0].group(2))
             if chat_id != SOURCE_CHANNEL:
                 await message.reply("Link must be from the source channel.")
                 return
             print(f"Fetching message {msg_id} from link...")
             msg = await app.get_messages(chat_id, msg_id)
             if msg:
                 await process_message(msg, msg_id)
                 await message.reply(f"Fetched message {msg_id}.")
             else:
                 await message.reply(f"Message {msg_id} not found.")
         except Exception as e:
             await message.reply(f"Error: {str(e)[:100]}")

     # Dummy HTTP server for Render
     async def start_http_server():
         http_app = web.Application()
         http_app.router.add_get('/', lambda _: web.Response(text="Bot is running"))
         runner = web.AppRunner(http_app)
         await runner.setup()
         site = web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 8000)))
         await site.start()
         print("HTTP server started on port", os.getenv('PORT', 8000))

     # Run bot and HTTP server
     async def main():
         print("Starting bot and HTTP server...")
         await asyncio.gather(app.start(), start_http_server())
         print("Bot is running! Send commands to @YourBotName.")

     if __name__ == "__main__":
         loop = asyncio.get_event_loop()
         loop.run_until_complete(main())
