import requests
import json
import re


class RAGFlowClient:
    def __init__(self, api_key, base_url="http://localhost:9380/api/v1"):
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.chat_id = None
        self.session_id = None

    def init_chat(self, chat_name=None):
        """获取对话助手并创建会话"""
        # 1. 获取 Chat ID
        resp = requests.get(f"{self.base_url}/chats", headers=self.headers)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0 or not data.get("data"):
            raise Exception(f"获取对话助手失败: {data.get('message')}")

        # 如果指定了名称则按名称查找，否则取第一个
        chat_list = data["data"]
        if chat_name:
            target = next((c for c in chat_list if c["name"] == chat_name), None)
            if not target: raise Exception(f"未找到名为 {chat_name} 的助手")
            self.chat_id = target["id"]
        else:
            self.chat_id = chat_list[0]["id"]

        # 2. 创建 Session
        session_resp = requests.post(
            f"{self.base_url}/chats/{self.chat_id}/sessions",
            headers=self.headers, json={"name": "Auto-Session"}
        )
        session_data = session_resp.json()
        if session_data.get("code") != 0:
            raise Exception(f"创建Session失败: {session_data.get('message')}")

        self.session_id = session_data["data"]["id"]
        print(f"✅ 初始化成功! 助手ID: {self.chat_id}, 会话ID: {self.session_id}")

    def ask(self, question):
        """发起流式问答并实时打印"""
        if not self.chat_id or not self.session_id:
            raise Exception("请先调用 init_chat() 初始化会话")

        payload = {
            "question": question,
            "session_id": self.session_id,
            "stream": True
        }

        full_answer = ""
        print("\nAI: ", end="", flush=True)

        try:
            with requests.post(
                    f"{self.base_url}/chats/{self.chat_id}/completions",
                    headers=self.headers, json=payload, stream=True, timeout=60
            ) as r:
                r.raise_for_status()
                for line in r.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    try:
                        chunk = json.loads(line[5:].strip())
                        if chunk.get("code") == 0 and isinstance(chunk.get("data"), dict):
                            ans = chunk["data"].get("answer", "")
                            # 计算增量部分
                            delta = ans[len(full_answer):]
                            # 过滤掉  标签内容
                            clean_delta = re.sub(r'<think>.*?</think>', '', delta, flags=re.DOTALL)
                            if clean_delta:
                                print(clean_delta, end="", flush=True)
                            full_answer = ans
                    except json.JSONDecodeError:
                        continue
            print("\n✅ 回复结束\n")
            return full_answer
        except Exception as e:
            print(f"\n❌ 请求异常: {e}")
            return ""



# client = RAGFlowClient(api_key="ragflow-Y2NzYyNmRjNjAyMzExZjFhY2I1ODJmNG")
# def l_ai():
#
#     try:
#         # 初始化对话（可传入助手名称，不传则默认第一个）
#         client.init_chat()
#         client.ask("你能帮我处理什么类型的工作？")
#
#     except Exception as e:
#         print(f"程序运行出错: {e}")
#
# l_ai()