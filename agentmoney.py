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

        self.app_address = self.get_bankr_address()

    def get_bankr_address(self) -> str:
        url = f"{self.bankr_url}/agent/me"
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
                wallets = resp.json()["wallets"]
                evm_wallet = [w for w in wallets if w["chain"] == "evm"][0]
                evm_address = evm_wallet["address"]
                logger.info(f"Bankr: 获取evm地址成功 {evm_address}")
                return evm_address
            elif code == 429 or 500 <= code < 600:
                logger.warning(f"Bankr: 获取evm地址异常 <{code}> {resp.text}")
                logger.warning(f"Bankr: 等待{wait}秒后重试...")
                retry -= 1
                time.sleep(wait)
                continue
            else:
                raise Exception(f"Bankr: 获取evm地址异常 <{code}> {resp.text}")
        else:
            raise Exception(f"Bankr: 获取evm地址失败")

    def get_app_nonce(self) -> dict[str, Any]:
        url = f"{self.app_url}/v1/auth/nonce"
        data = {"miner": self.app_address}

        retry = self.default_retry_count
        wait = self.default_wait_seconds
        while retry:
            resp = requests.post(url, json=data)
            code = resp.status_code

            if code == 200:
                resp_json = resp.json()
                logger.info(f"{self.app_name}: 获取nonce成功 {resp_json}")
                return resp_json
            elif code == 429 or 500 <= code < 600:
                logger.warning(f"{self.app_name}: 获取nonce异常 <{code}> {resp.text}")
                logger.warning(f"{self.app_name}: 等待{wait}秒后重试...")
                retry -= 1
                time.sleep(wait)
                continue
            else:
                raise Exception(f"{self.app_name}: 获取nonce异常 <{code}> {resp.text}")
        else:
            raise Exception(f"{self.app_name}: 获取nonce失败")

    def sign_and_verify(self, message: str) -> dict[str, Any]:
        url = f"{self.bankr_url}/agent/sign"
        hds = {
            "Content-Type": "application/json",
            "X-API-Key": self.bankr_key,
        }
        data = {"signatureType": "personal_sign", "message": message}
        retry = self.default_retry_count
        wait = self.default_wait_seconds
        while retry:
            resp = requests.post(url, headers=hds, json=data)
            code = resp.status_code

            if code == 200:
                app_sign = resp.json()
                logger.info(f"{self.app_name}: 获取签名成功 {app_sign}")
                break
            elif code == 429 or 500 <= code < 600:
                logger.warning(f"{self.app_name}: 获取签名异常 <{code}> {resp.text}")
                logger.warning(f"{self.app_name}: 等待{wait}秒后重试...")
                retry -= 1
                time.sleep(wait)
                continue
            else:
                raise Exception(f"{self.app_name}: 获取签名异常 <{code}> {resp.text}")
        else:
            raise Exception(f"{self.app_name}: 获取签名失败")

        url = f"{self.app_url}/v1/auth/verify"
        data = {
            "miner": self.app_address,
            "message": message,
            "signature": app_sign["signature"],
        }
        retry = self.default_retry_count
        wait = self.default_wait_seconds
        while retry:
            resp = requests.post(url, headers=hds, json=data)
            code = resp.status_code

            if code == 200:
                resp_json = resp.json()
                logger.info(f"{self.app_name}: 签名验证成功 {resp_json}")
                return resp_json
            elif code == 429 or 500 <= code < 600:
                logger.warning(f"{self.app_name}: 签名验证异常 <{code}> {resp.text}")
                logger.warning(f"{self.app_name}: 等待{wait}秒后重试...")
                retry -= 1
                time.sleep(wait)
                continue
            else:
                raise Exception(f"{self.app_name}: 签名验证异常 <{code}> {resp.text}")
        else:
            raise Exception(f"{self.app_name}: 签名验证失败")

    def get_headers(self) -> dict[str, str]:
        return {
            "Content-type": "Application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            + "AppleWebKit/537.36 (KHTML, like Gecko) "
            + "Chrome/91.0.4472.124 Safari/537.36",
        }

    def mine(self) -> None:
        logger.info(f"{self.app_name}: 开始挖矿...")
        app_nonce = self.get_app_nonce()
        app_sign = self.sign_and_verify(app_nonce["message"])
        logger.info(f"{self.app_name}: 获取Token {app_sign["token"]}")

        nonce = secrets.token_hex(16)
        url = f"{self.app_url}/v1/challenge?miner={self.app_address}&nonce={nonce}"
        hds = {
            "Content-type": "Application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Authorization": f"Bearer {app_sign["token"]}",
        }
        retry = self.default_retry_count
        wait = self.default_wait_seconds
        while retry:
            resp = requests.get(url, headers=hds)
            code = resp.status_code

            if code == 200:
                app_challenge = resp.json()
                logger.info(
                    f"{self.app_name}: 获取挑战信息成功 {app_challenge["challengeId"]}"
                )
                break
            elif code == 429 or 500 <= code < 600:
                logger.warning(
                    f"{self.app_name}: 获取挑战信息异常 <{code}> {resp.text}"
                )
                logger.warning(f"{self.app_name}: 等待{wait}秒后重试...")
                retry -= 1
                time.sleep(wait)
                continue
            else:
                raise Exception(
                    f"{self.app_name}: 获取挑战信息异常 <{code}> {resp.text}"
                )
        else:
            raise Exception(f"{self.app_name}: 获取挑战信息失败")

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
        url = f"{self.llm_endpoint}/v1/chat/completions"
        hds = {
            "Authorization": f"Bearer {self.llm_apikey}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.llm_model,
            "messages": [{"role": "user", "content": content}],
        }
        wait = self.default_wait_seconds
        resp = requests.post(url, headers=hds, json=data)
        code = resp.status_code

        if code == 200:
            llm_resp = resp.json()
            llm_content = llm_resp["choices"][0]["message"]["content"]
            logger.info(f"LLM: 大模型答案 {llm_content}")
        else:
            raise Exception(f"LLM: 大模型请求异常 <{code}> {resp.text}")

        url = f"{self.app_url}/v1/submit"
        hds = {
            "Content-type": "Application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Authorization": f"Bearer {app_sign["token"]}",
        }
        data = {
            "miner": self.app_address,
            "challengeId": app_challenge["challengeId"],
            "artifact": llm_content,
            "nonce": nonce,
        }
        retry = self.default_retry_count
        wait = self.default_wait_seconds
        while retry:
            resp = requests.post(url, headers=hds, json=data)
            code = resp.status_code

            if code == 200:
                app_result = resp.json()
                if app_result["pass"]:
                    logger.info(f"{self.app_name}: 提交答案成功 {app_result}")
                    break
                else:
                    raise Exception(f"{self.app_name}: 答案校验失败 {app_result}")
            elif code == 429 or 500 <= code < 600:
                logger.warning(f"{self.app_name}: 提交答案异常 <{code}> {resp.text}")
                logger.warning(f"{self.app_name}: 等待{wait}秒后重试...")
                retry -= 1
                time.sleep(wait)
                continue
            else:
                raise Exception(f"{self.app_name}: 提交答案异常 <{code}> {resp.text}")
        else:
            raise Exception(f"{self.app_name}: 提交答案失败")

        toast = Notification(
            app_id="AgentMoney",
            title="验证通过",
            msg=f"项目方验证结果：{app_result}",
        )
        toast.set_audio(audio.Default, False)
        toast.show()

        url = f"{self.bankr_url}/agent/submit"
        hds = {
            "Content-Type": "application/json",
            "X-API-Key": self.bankr_key,
        }
        data = {
            "transaction": app_result["transaction"],
            "description": "Post BOTCOIN mining receipt",
            "waitForConfirmation": True,
        }
        retry = self.default_retry_count
        wait = self.default_wait_seconds
        while retry:
            resp = requests.post(url, headers=hds, json=data)
            code = resp.status_code

            if code == 200:
                submit_result = resp.json()
                logger.info(f"Bankr: 奖励交易广播成功 {submit_result}")
                break
            elif code == 429 or 500 <= code < 600:
                logger.warning(f"Bankr: 奖励交易广播异常 <{code}> {resp.text}")
                logger.warning(f"Bankr: 等待{wait}秒后重试...")
                retry -= 1
                time.sleep(wait)
                continue
            else:
                raise Exception(f"Bankr: 奖励交易广播异常 <{code}> {resp.text}")
        else:
            raise Exception(f"Bankr: 奖励交易广播失败")

    def loop_mine(self) -> int:
        while True:
            try:
                self.mine()
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
