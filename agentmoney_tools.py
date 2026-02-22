import os
import time
import secrets
import requests
from typing import Any, Callable
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
    ) -> None:
        self.bankr_url = bankr_url
        self.bankr_key = bankr_key

    ### 请求方法

    def requests_retry(
        self,
        app: str,
        tag: str,
        requests_fn: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        retry = self.default_retry_count
        wait = self.default_wait_seconds
        while retry:
            retry -= 1
            resp: requests.Response = requests_fn(*args, **kwargs)
            code = resp.status_code

            if code == 200:
                return resp.json()
            elif code == 429:
                if "retryAfterSeconds" in resp.text:
                    wait = max(int(resp.json()["retryAfterSeconds"]), wait)
                logger.warning(f"{app}: {tag}请求频率过高 等待{wait}秒后重试...")
                time.sleep(wait)
                continue
            elif code == 403:
                if "retryAfterSeconds" in resp.text:
                    wait = max(int(resp.json()["retryAfterSeconds"]), wait)
                logger.warning(f"{app}: {tag}请求受限于余额不足 等待{wait}秒后重试...")
                time.sleep(wait)
                continue
            elif 500 <= code < 600:
                logger.warning(f"{app}: {tag}异常 <{code}> {resp.text}")
                logger.warning(f"{app}: 等待{wait}秒后重试...")
                time.sleep(wait)
                continue
            else:
                raise Exception(f"{app}: {tag}异常 <{code}> {resp.text}")
        else:
            raise Exception(f"{app}: {tag}失败")

    def bankr_get(self, path: str, headers: dict, tag: str) -> dict[str, Any]:
        url = f"{self.bankr_url}{path}"
        hds = {
            "Content-Type": "application/json",
            "X-API-Key": self.bankr_key,
        }
        hds.update(headers)
        return self.requests_retry(
            "Bankr",
            tag,
            requests.get,
            url,
            headers=hds,
        )

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
        return self.requests_retry(
            "Bankr",
            tag,
            requests.post,
            url,
            headers=hds,
            json=data,
        )

    def app_get(self, path: str, headers: dict, tag: str) -> dict[str, Any]:
        url = f"{self.app_url}{path}"
        hds = {
            "Content-type": "Application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
        hds.update(headers)
        return self.requests_retry(
            f"{self.app_name}",
            tag,
            requests.get,
            url,
            headers=hds,
        )

    def app_post(
        self,
        path: str,
        headers: dict,
        data: dict,
        tag: str,
    ) -> dict[str, Any]:
        url = f"{self.app_url}{path}"
        hds = {
            "Content-type": "Application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
        hds.update(headers)
        return self.requests_retry(
            f"{self.app_name}",
            tag,
            requests.post,
            url,
            headers=headers,
            json=data,
        )

    ### 功能方法

    def claim(self) -> None:
        epoch = self.app_get("/v1/epoch", {}, "获取Epoch信息")
        logger.info(f"Epoch信息：{epoch}")

        if "prevEpochSecretRevealed" not in epoch:
            logger.warning("上一轮Epoch的秘密未揭晓")
            return

        prev_epoch_id = epoch["prevEpochId"]
        claim_url = f"/v1/claim-calldata?epochs={prev_epoch_id}"
        claim = self.app_get(claim_url, {}, "获取Claim信息")
        logger.info(f"Claim信息：{claim}")

        data = {
            "transaction": claim["transaction"],
            "description": "Claim BOTCOIN mining rewards",
            "waitForConfirmation": True,
        }
        claim_result = self.bankr_post("/agent/submit", {}, data, "Claim交易广播")
        logger.info(f"Claim广播结果：{claim_result}")

    def main(self) -> None:
        try:
            self.claim()
        except Exception as e:
            logger.error(f"{repr(e)}")


if __name__ == "__main__":
    load_dotenv(override=True)

    AgentMoney(
        bankr_key=os.environ["BANKR_KEY"],
        bankr_url=os.environ["BANKR_URL"],
    ).main()
