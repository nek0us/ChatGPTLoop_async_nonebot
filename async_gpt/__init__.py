from pyChatGPTLoop.pyChatGPTLoop import ChatGPT
import nonebot
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Event,Bot,Message,MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
import threading
import queue
import asyncio
import redis

config = nonebot.get_driver().config



class loop_chat(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.msg_id:int = 0
        
        self.redis = redis.Redis(host=config.redis_host, port=config.redis_port,password=config.redis_pass,decode_responses=True, charset='UTF-8', encoding='UTF-8',db=9)
        self.token = self.redis.get("token")
        #如未使用redis请注释这两句
        
        self.send_queue = queue.Queue()
        self.rec = []
        
        self.chat = ChatGPT(session_token=self.token,driver_path=config.driver_path , proxy=config.proxy, moderation=False , conversation_id=config.conversation_id) # type: ignore
        #可不使用redis，修改为个人配置
        
        new_loop = asyncio.get_event_loop()
        t = threading.Thread(target=self.run,args=(new_loop,))
        t.start()
        asyncio.run_coroutine_threadsafe(self.gpt(),new_loop)
        
    async def gpt(self) :
        while 1:
            if not self.send_queue.empty():
                msg_send = self.send_queue.get()
                if msg_send["type"] == "msg":
                    msg_rec = self.chat.send_message(msg_send["msg_send"])
                    if msg_rec:
                        msg_send["msg_rec"] = msg_rec
                    else:
                        msg_send["msg_rec"] = "error"
                elif msg_send["type"] == "loop":
                    msg_send["msg_rec"] = self.chat.backtrack_chat(msg_send["msg_send"])
                elif msg_send["type"] == "init":
                    msg_send["msg_rec"] = self.chat.init_personality()
                    
                #self.rec_queue.put(msg_send)
                self.rec.append(msg_send)
                
    async def get_id(self) -> int:
        self.msg_id += 1
        return self.msg_id
    
    def run(self,new_loop):
        asyncio.set_event_loop(new_loop)
        new_loop.run_forever()
        

chat_initial = loop_chat()

#正常聊天
chat = on_command(cmd="",rule=to_me(),priority=30,block=True)
@chat.handle()
async def _(bot:Bot,m:Matcher,event:Event,args: Message=CommandArg()):
    msg_id = await chat_initial.get_id()
    msg_dict = {
        "id":msg_id, #我是傻叉
        "type":"msg",
        "num":event.get_user_id(),
        "msg_send":args.extract_plain_text(),
        
    }
    chat_initial.send_queue.put(msg_dict)
    rec_lock = False
    msg :str = ""
    while 1:
        #循环获取消息准备情况
        for x in chat_initial.rec:
            if x["id"] == msg_dict["id"]:
                rec_lock = True
                msg = x["msg_rec"]
                chat_initial.rec.remove(x)
                break
        if rec_lock:
            break
        await asyncio.sleep(2)
    
    await m.finish(msg["message"])# type: ignore
 
#时空回溯执行    
backloop = on_command(cmd="回到过去",aliases={"back","loop"},permission=SUPERUSER,priority=25,block=True)
@backloop.handle()
async def _(bot:Bot,m:Matcher,event:Event,args: Message=CommandArg()):
    msg_id = await chat_initial.get_id()
    msg_dict = {
        "id":msg_id, #我是傻叉
        "type":"loop",
        "num":event.get_user_id(),
        "msg_send":args.extract_plain_text(),
        
    }
    chat_initial.send_queue.put(msg_dict)
    rec_lock = False
    msg :bool = False
    while 1:
        #循环获取消息准备情况
        for x in chat_initial.rec:
            if x["id"] == msg_dict["id"]:
                rec_lock = True
                msg = x["msg_rec"]
                chat_initial.rec.remove(x)
                break
        if rec_lock:
            break
        await asyncio.sleep(2)
    if msg:
        await m.finish("成功了喵~")
    else:
        await m.finish("失败了喵...")

#初始化人格执行    
init = on_command(cmd="初始化人格",aliases={"init"},permission=SUPERUSER,priority=25,block=True)
@init.handle()
async def _(bot:Bot,m:Matcher,event:Event,args: Message=CommandArg()):
    msg_id = await chat_initial.get_id()
    msg_dict = {
        "id":msg_id, #我是傻叉
        "type":"init",
        "num":event.get_user_id(),
        "msg_send":args.extract_plain_text(),
        
    }
    chat_initial.send_queue.put(msg_dict)
    rec_lock = False
    msg :str = ""
    while 1:
        #循环获取消息准备情况
        for x in chat_initial.rec:
            if x["id"] == msg_dict["id"]:
                rec_lock = True
                msg = x["msg_rec"]
                chat_initial.rec.remove(x)
                break
        if rec_lock:
            break
        await asyncio.sleep(2)
    if msg["status"]:# type: ignore
        await m.finish("初始化完美完成，conversation_id为 "+msg['conversation_id'])# type: ignore
    else:
        await m.finish("初始化不太成功，conversation_id为 "+msg['conversation_id'])# type: ignore