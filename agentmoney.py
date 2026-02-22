import os
import time
import secrets
import requests
from typing import Any
from loguru import logger
from dotenv import load_dotenv
from winotify import Notification, audio


class AgentMoney:
    app_name = "AgentMoney"
    app_url = "https://coordinator.agentmoney.net"
    default_wait_seconds = 30
    default_retry_count = 3

    def __init__(
        self,
        bankr_url: str,
        bankr_key: str,
        llm_endpoint: str,
        llm_apikey: str,
        llm_model: str,
    ) -> None:
        self.bankr_url = bankr_url
        self.bankr_key = bankr_key
        self.llm_endpoint = llm_endpoint
        self.llm_apikey = llm_apikey
        self.llm_model = llm_model

        self.app_address = self.bankr_get_address()

    ### 请求方法

    def bankr_get(self, path: str, tag: str) -> dict[str, Any]:
        url = f"{self.bankr_url}{path}"
        hds = {
            "Content-Type": "application/json",
            "X-API-Key": self.bankr_key,
        }
        retry = self.default_retry_count
        wait = self.default_wait_seconds
        while retry:
            resp = requests.get(url, headers=hds)
            code = resp.status_code

            if code == 200:
                return resp.json()
            elif code == 429 or 500 <= code < 600:
                logger.warning(f"Bankr: {tag}异常 <{code}> {resp.text}")
                logger.warning(f"Bankr: 等待{wait}秒后重试...")
                retry -= 1
                time.sleep(wait)
                continue
            else:
                raise Exception(f"Bankr: {tag}异常 <{code}> {resp.text}")
        else:
            raise Exception(f"Bankr: {tag}失败")

    def bankr_post(
        self,
        path: str,
        headers: dict,
        data: dict,
        tag: str,
    ) -> dict[str, Any]:
        url = f"{self.bankr_url}{path}"
        hds = {
            "Content-Type": "application/json",
            "X-API-Key": self.bankr_key,
        }
        hds.update(headers)
        retry = self.default_retry_count
        wait = self.default_wait_seconds
        while retry:
            resp = requests.post(url, headers=hds, json=data)
            code = resp.status_code

            if code == 200:
                return resp.json()
            elif code == 429 or 500 <= code < 600:
                logger.warning(f"{self.app_name}: {tag}异常 <{code}> {resp.text}")
                logger.warning(f"{self.app_name}: 等待{wait}秒后重试...")
                retry -= 1
                time.sleep(wait)
                continue
            else:
                raise Exception(f"{self.app_name}: {tag}异常 <{code}> {resp.text}")
        else:
            raise Exception(f"{self.app_name}: {tag}失败")

    def app_get(self, path: str, headers: dict, tag: str) -> dict[str, Any]:
        url = f"{self.app_url}{path}"
        hds = {
            "Content-type": "Application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
        hds.update(headers)
        retry = self.default_retry_count
        wait = self.default_wait_seconds
        while retry:
            resp = requests.get(url, headers=hds)
            code = resp.status_code

            if code == 200:
                return resp.json()
            elif code == 429 or 500 <= code < 600:
                logger.warning(f"{self.app_name}: {tag}异常 <{code}> {resp.text}")
                logger.warning(f"{self.app_name}: 等待{wait}秒后重试...")
                retry -= 1
                time.sleep(wait)
                continue
            else:
                raise Exception(f"{self.app_name}: {tag}异常 <{code}> {resp.text}")
        else:
            raise Exception(f"{self.app_name}: {tag}失败")

    def app_post(
        self,
        path: str,
        headers: dict,
        data: dict,
        tag: str,
    ) -> dict[str, Any]:
        url = f"{self.app_url}{path}"
        retry = self.default_retry_count
        wait = self.default_wait_seconds
        while retry:
            resp = requests.post(url, headers=headers, json=data)
            code = resp.status_code

            if code == 200:
                return resp.json()
            elif code == 429 or 500 <= code < 600:
                logger.warning(f"{self.app_name}: {tag}异常 <{code}> {resp.text}")
                logger.warning(f"{self.app_name}: 等待{wait}秒后重试...")
                retry -= 1
                time.sleep(wait)
                continue
            else:
                raise Exception(f"{self.app_name}: {tag}异常 <{code}> {resp.text}")
        else:
            raise Exception(f"{self.app_name}: {tag}失败")

    def llm_get(self, path: str) -> dict[str, Any]:
        assert path
        return {}

    def llm_post(
        self,
        path: str,
        headers: dict,
        content: dict,
    ) -> dict[str, Any]:
        url = f"{self.llm_endpoint}{path}"
        hds = {
            "Authorization": f"Bearer {self.llm_apikey}",
            "Content-Type": "application/json",
        }
        hds.update(headers)
        data = {
            "model": self.llm_model,
            "messages": [{"role": "user", "content": content}],
        }
        resp = requests.post(url, headers=hds, json=data)
        code = resp.status_code

        if code == 200:
            return resp.json()
        else:
            raise Exception(f"LLM: 大模型请求异常 <{code}> {resp.text}")

    ### 功能方法

    def bankr_get_address(self) -> str:
        resp = self.bankr_get("/agent/me", "获取evm地址")
        wallets = resp["wallets"]
        evm_wallet = [w for w in wallets if w["chain"] == "evm"][0]
        evm_address = evm_wallet["address"]
        logger.info(f"Bankr: 获取evm地址成功 {evm_address}")
        return evm_address

    def app_get_nonce(self) -> dict[str, Any]:
        data = {"miner": self.app_address}
        resp = self.app_post("/v1/auth/nonce", {}, data, "获取nonce")
        logger.info(f"{self.app_name}: 获取nonce成功 {resp}")
        return resp

    def bankr_sign_and_app_verify(self, message: str) -> dict[str, Any]:
        data = {
            "signatureType": "personal_sign",
            "message": message,
        }
        resp = self.bankr_post("/agent/sign", {}, data, "获取签名")
        logger.info(f"Bankr: 获取签名成功 {resp}")

        data = {
            "miner": self.app_address,
            "message": message,
            "signature": resp["signature"],
        }
        resp = self.app_post("/v1/auth/verify", {}, data, "签名验证")
        logger.info(f"{self.app_name}: 签名验证成功 {resp}")
        return resp

    ### 挖矿

    def mine(self) -> None:
        logger.info(f"{self.app_name}: 开始挖矿...")

        app_nonce = self.app_get_nonce()
        app_sign = self.bankr_sign_and_app_verify(app_nonce["message"])

        nonce = secrets.token_hex(16)
        logger.info(f"{self.app_name}: 生成随机数 {nonce}")

        path = f"/v1/challenge?miner={self.app_address}&nonce={nonce}"
        app_auth = {"Authorization": f"Bearer {app_sign["token"]}"}
        app_challenge = self.app_get(path, app_auth, "获取挑战信息")
        logger.info(f"{self.app_name}: 获取挑战信息成功 {app_challenge["challengeId"]}")

        content = f"""
### DOC

{app_challenge["doc"]}

### Questions
{"\n- ".join(app_challenge["questions"])}


### Constraints
{"\n- ".join(app_challenge["constraints"])}

### Companies
{"\n- ".join(app_challenge["companies"])}

### Solve the Hybrid Challenge

Read the `DOC` carefully and use the `Question` to identify the referenced companies/facts.
Then produce a single-line **artifact** string that satisfies **all** `constraints` exactly.
**Output format (critical):** When you call your LLM, append this instruction to your prompt:
> Your response must be exactly one line — the artifact string and nothing else.
Do NOT output "Q1:", "Looking at", "Let me", "First", "Answer:", or any reasoning.
Do NOT explain your process. Output ONLY the single-line artifact that satisfies all constraints. 
No preamble. No JSON. Just the artifact.

### Contains

- `DOC` — a long prose document about 25 fictional companies
- `Question` — a small set of questions whose answers are exact company names
- `Constraints` — a list of verifiable constraints your artifact must satisfy
- `Companies` — the list of all 25 company names in the document

### SolveInstructions

{app_challenge["solveInstructions"]}
"""

        logger.info(f"LLM: 大模型请求中...")
        data = {
            "model": self.llm_model,
            "messages": [{"role": "user", "content": content}],
        }
        llm_resp = self.llm_post("/v1/chat/completions", {}, data)
        llm_content = llm_resp["choices"][0]["message"]["content"]
        logger.info(f"LLM: 大模型答案 {llm_content}")

        data = {
            "miner": self.app_address,
            "challengeId": app_challenge["challengeId"],
            "artifact": llm_content,
            "nonce": nonce,
        }
        app_result = self.app_post("/v1/submit", app_auth, data, "提交答案")
        if not app_result["pass"]:
            raise Exception(f"{self.app_name}: 答案校验失败 {app_result}")
        logger.info(f"{self.app_name}: 提交答案成功 {app_result}")

        toast = Notification(
            app_id="AgentMoney",
            title="验证通过",
            msg=f"项目方验证结果：{app_result}",
        )
        toast.set_audio(audio.Default, False)
        toast.show()

        data = {
            "transaction": app_result["transaction"],
            "description": "Post BOTCOIN mining receipt",
            "waitForConfirmation": True,
        }
        submit_result = self.bankr_post("/agent/submit", {}, data, "奖励交易广播")
        logger.info(f"Bankr: 奖励交易广播成功 {submit_result}")

    def loop_mine(self) -> int:
        while True:
            try:
                self.mine()
            except KeyboardInterrupt as e:
                logger.info("收到中断信号，程序已停止")
                return 1
            except Exception as e:
                logger.error(e)


if __name__ == "__main__":
    load_dotenv(override=True)

    AgentMoney(
        bankr_key=os.environ["BANKR_KEY"],
        bankr_url=os.environ["BANKR_URL"],
        llm_endpoint=os.environ["LLM_URL"],
        llm_apikey=os.environ["LLM_KEY"],
        llm_model=os.environ["LLM_MODEL"],
    ).loop_mine()
