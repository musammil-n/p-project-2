from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
from config import MONGO_DB_URI, OWNER

# MongoDB setup
mongo_client = MongoClient(MONGO_DB_URI)
db = mongo_client["auto_forward_bot"]
user_chats = db["user_chats"]

class TEXT:
    SETCHAT_HELP = """
**To set forwarding chats:**
`/setchat channel_id1 channel_id2 channel_id3`

Example:
`/setchat -10012345678 -10087654321 -10011223344`
"""
    SEND_HELP = """
**To forward a message:**
1. Reply to any message
2. Send `/send`
"""
    NO_CHATS_SET = "You haven't set any chats to forward to. Use /setchat first."
    CHATS_SET_SUCCESS = "Successfully set {count} chat(s) for forwarding!"
    INVALID_CHAT_ID = "Invalid chat ID format. Please provide numeric chat IDs."
    FORWARD_REPORT = "Forwarded message to {success_count} chat(s)."
    FORWARD_FAILED = "\nFailed to forward to: {failed_chats}"
    MY_CHATS_HEADER = "Your configured chats:\n{chat_list}"

@Client.on_message(filters.command("setchat") & filters.private)
async def set_chats(client: Client, message: Message):
    args = message.command[1:]
    
    if not args:
        await message.reply_text(TEXT.SETCHAT_HELP)
        return
    
    try:
        chat_ids = [int(arg) for arg in args]
        user_id = message.from_user.id
        
        user_chats.update_one(
            {"user_id": user_id},
            {"$set": {"chat_ids": chat_ids}},
            upsert=True
        )
        
        await message.reply_text(TEXT.CHATS_SET_SUCCESS.format(count=len(chat_ids)))
        
        # Notify owner
        mention = message.from_user.first_name or "User"
        await client.send_message(
            chat_id=OWNER.ID,
            text=f"⚡ User <a href='tg://user?id={user_id}'>{mention}</a> set {len(chat_ids)} forwarding chats.\n🆔 User ID: <code>{user_id}</code>",
            parse_mode="html"
        )
    except ValueError:
        await message.reply_text(TEXT.INVALID_CHAT_ID)

@Client.on_message(filters.command("send") & filters.private & filters.reply)
async def forward_message(client: Client, message: Message):
    user_id = message.from_user.id
    user_config = user_chats.find_one({"user_id": user_id})
    
    if not user_config or "chat_ids" not in user_config:
        await message.reply_text(TEXT.NO_CHATS_SET)
        return
    
    target_chats = user_config["chat_ids"]
    replied_message = message.reply_to_message
    
    success_count = 0
    failed_chats = []
    
    for chat_id in target_chats:
        try:
            await replied_message.forward(chat_id)
            success_count += 1
        except Exception as e:
            print(f"Failed to forward to {chat_id}: {e}")
            failed_chats.append(str(chat_id))
    
    report = TEXT.FORWARD_REPORT.format(success_count=success_count)
    if failed_chats:
        report += TEXT.FORWARD_FAILED.format(failed_chats=", ".join(failed_chats))
    
    await message.reply_text(report)

@Client.on_message(filters.command("mychats") & filters.private)
async def show_chats(client: Client, message: Message):
    user_id = message.from_user.id
    user_config = user_chats.find_one({"user_id": user_id})
    
    if not user_config or "chat_ids" not in user_config:
        await message.reply_text(TEXT.NO_CHATS_SET)
        return
    
    chat_list = "\n".join([f"• `{chat_id}`" for chat_id in user_config["chat_ids"]])
    await message.reply_text(TEXT.MY_CHATS_HEADER.format(chat_list=chat_list))
