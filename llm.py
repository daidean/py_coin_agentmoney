import os
from pprint import pprint
import requests
from typing import Any
from dotenv import load_dotenv


class LLM:
    def __init__(self, llm_url: str, llm_key: str, llm_model: str) -> None:
        self.llm_url = llm_url
        self.llm_key = llm_key
        self.llm_model = llm_model

    def get_headers(self) -> dict:
        """获取 LLM API 请求头"""
        return {
            "Authorization": f"Bearer {self.llm_key}",
            "Content-Type": "application/json",
        }

    def completions(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        url = f"{self.llm_url}/v1/chat/completions"
        data = {"model": self.llm_model, "messages": messages}

        resp = requests.post(url, headers=self.get_headers(), json=data)
        if resp.status_code != 200:
            raise Exception(f"<{resp.status_code}> {resp.text}")
        return resp.json()

    def chat(self, message) -> str:
        messages = [{"role": "user", "content": message}]
        resp = self.completions(messages)
        return resp["choices"][0]["message"]["content"]


if __name__ == "__main__":
    load_dotenv(override=True)

    llm = LLM(
        llm_url=os.environ["LLM_URL"],
        llm_key=os.environ["LLM_KEY"],
        llm_model=os.environ["LLM_MODEL"],
    )

    pprint(llm.completions([{"role": "user", "content": "你好"}]))
    pprint(llm.chat("你好"))
