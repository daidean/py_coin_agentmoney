import os
import sys
import time
import secrets
import requests
from typing import Any
from datetime import datetime, timezone
from dotenv import load_dotenv
from bankr import Bankr
from llm import LLM
from notify import windows_notify


class AgentMoney:
    def __init__(self, agentmoney_url: str, bankr: Bankr, llm: LLM) -> None:
        self.agentmoney_url = agentmoney_url
        self.bankr = bankr
        self.llm = llm

        self.miner_address = ""
        self.miner_nonce = {}
        self.miner_sig = ""

    def get_address(self) -> str:
        if self.miner_address:
            return self.miner_address

        userinfo = self.bankr.get_user_info()
        wallets = userinfo["wallets"]
        evm_wallet = [w for w in wallets if w["chain"] == "evm"]

        assert evm_wallet
        assert len(evm_wallet) == 1

        evm_wallet = evm_wallet[0]
        self.miner_address = evm_wallet["address"]
        return self.miner_address

    def get_nonce(self) -> dict[str, Any]:
        now_time = datetime.now(timezone.utc)
        if (
            self.miner_nonce
            and datetime.fromisoformat(self.miner_nonce["expiresAt"]) > now_time
        ):
            return self.miner_nonce

        url = f"{self.agentmoney_url}/v1/auth/nonce"
        data = {"miner": self.get_address()}

        resp = requests.post(url, json=data)
        self.miner_nonce = resp.json()
        return self.miner_nonce

    def sign_and_verify(self) -> dict[str, Any]:
        nonce = self.get_nonce()
        message = nonce["message"]

        sign = self.bankr.sign("personal_sign", message=message)

        url = f"{self.agentmoney_url}/v1/auth/verify"
        data = {
            "miner": self.get_address(),
            "message": message,
            "signature": sign["signature"],
        }
        resp = requests.post(url, json=data)
        return resp.json()

    def get_proxys(self) -> dict[str, str]:
        return {
            "http": "http://127.0.0.1:10808",
            "https": "http://127.0.0.1:10808",
        }

    def get_headers(self) -> dict[str, str]:
        return {
            "Content-type": "Application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            + "AppleWebKit/537.36 (KHTML, like Gecko) "
            + "Chrome/91.0.4472.124 Safari/537.36",
        }

    def mine(self) -> int:
        print("开始挖矿...")
        token = self.sign_and_verify()["token"]
        print(f"获取Token：{token}")
        header = self.get_headers() | {"Authorization": f"Bearer {token}"}
        nonce = secrets.token_hex(16)
        print(f"获取随机数：{nonce}")

        retry = 3
        url = f"{self.agentmoney_url}/v1/challenge?miner={self.get_address()}&nonce={nonce}"
        while retry:
            resp = requests.get(url, headers=header)
            if resp.status_code != 200:
                retry -= 1
                print(f"请求异常: 状态为{resp.status_code}, 重试中...{3-retry}")
                time.sleep(1)
                continue

            # print(resp.text)  # DEBUG
            resp_json = resp.json()
            if "error" in resp_json:
                retry -= 1
                print(f"响应异常: {resp_json["error"]}")
                time.sleep(resp_json.get("retryAfterSeconds", 1))
                continue

            challenge_id = resp_json["challengeId"]
            print(f"获取挑战ID：{challenge_id}")
            break
        else:
            print("重试超时: 请求异常且重试后依然异常")
            return 1

        content = f"""
### DOC

{resp_json["doc"]}

### Questions
{"\n- ".join(resp_json["questions"])}


### Constraints
{"\n- ".join(resp_json["constraints"])}

### Companies
{"\n- ".join(resp_json["companies"])}

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

{resp_json["solveInstructions"]}
"""

        print(f"AI请求中...{datetime.now()}")
        llm_content = self.llm.chat(content)
        print(f"AI响应结束...{datetime.now()}")
        print(f"AI答案为：{llm_content}")

        url = f"{self.agentmoney_url}/v1/submit"
        data = {
            "miner": self.get_address(),
            "challengeId": challenge_id,
            "artifact": llm_content,
            "nonce": nonce,
        }
        resp = requests.post(url, headers=header, json=data)
        resp.raise_for_status()
        resp_json = resp.json()
        print(f"项目方验证结果：{resp_json}")

        if "pass" not in resp_json or resp_json["pass"] == False:
            print(f"项目方验证结果：未通过")
            return 1

        print(f"项目方验证结果：通过，正在提交奖励交易")
        windows_notify(f"项目方验证结果：{resp_json}", "验证通过", "AgentMoney")
        subbit_resp = self.bankr.submit_transaction(resp_json["transaction"])
        print(f"项目方奖励提交结果：{subbit_resp}")
        return 0


if __name__ == "__main__":
    load_dotenv(override=True)

    bankr = Bankr(
        api_key=os.environ["BANKR_KEY"],
        api_url=os.environ["BANKR_URL"],
    )

    llm = LLM(
        llm_url=os.environ["LLM_URL"],
        llm_key=os.environ["LLM_KEY"],
        llm_model=os.environ["LLM_MODEL"],
    )

    agent = AgentMoney(os.environ["AGENTMONEY_URL"], bankr, llm)
    while True:
        try:
            agent.mine()
        except:
            print("挖矿异常，正在重试...")
