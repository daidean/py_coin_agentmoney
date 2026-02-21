import os
import time
import requests
from typing import Any
from pprint import pprint
from dotenv import load_dotenv


class Bankr:
    """
    Bankr API 客户端 - AI 驱动的加密货币交易代理

    支持功能：
    - 查询余额和投资组合
    - 查看代币价格
    - 加密货币交易（买入/卖出/兑换）
    - 转账
    - NFT 操作
    - 杠杆交易
    - Polymarket 投注
    - 代币部署
    - 自动化交易（DCA、限价单、止损）

    支持链：Base、Ethereum、Polygon、Solana、Unichain
    """

    def __init__(
        self,
        api_key: str,
        api_url: str,
    ) -> None:
        """
        初始化 Bankr 客户端

        Args:
            api_key: Bankr API Key (格式: bk_...)
            api_url: Bankr API 基础 URL
        """
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.last_thread_id: str | None = None

    def get_headers(self) -> dict:
        """获取 Bankr API 请求头"""
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def submit_prompt(self, prompt: str, thread_id: str | None = None) -> dict:
        """
        提交提示词（异步，返回 job ID）

        Args:
            prompt: 自然语言提示词
            thread_id: 对话线程 ID（可选，用于多轮对话）

        Returns:
            包含 jobId 和 threadId 的字典
        """
        url = f"{self.api_url}/agent/prompt"
        data = {"prompt": prompt}
        if thread_id:
            data["threadId"] = thread_id

        response = requests.post(url, headers=self.get_headers(), json=data)
        response.raise_for_status()
        result = response.json()

        # 保存 threadId 用于后续对话
        if "threadId" in result:
            self.last_thread_id = result["threadId"]

        return result

    def get_job_status(self, job_id: str) -> dict:
        """
        查询任务状态

        Args:
            job_id: 任务 ID

        Returns:
            任务状态和结果
        """
        url = f"{self.api_url}/agent/job/{job_id}"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def cancel_job(self, job_id: str) -> dict:
        """
        取消正在运行的任务

        Args:
            job_id: 任务 ID

        Returns:
            取消结果
        """
        url = f"{self.api_url}/agent/job/{job_id}/cancel"
        response = requests.post(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def prompt(
        self,
        text: str,
        thread_id: str | None = None,
        poll_interval: float = 2.0,
        timeout: float | None = None,
    ) -> str:
        """
        发送提示词并等待完成（同步阻塞）

        Args:
            text: 自然语言提示词
            thread_id: 对话线程 ID（可选，不传则开启新对话）
            poll_interval: 轮询间隔（秒）
            timeout: 超时时间（秒，可选）

        Returns:
            代理的响应文本
        """
        # 提交提示词
        submit_result = self.submit_prompt(text, thread_id)
        job_id = submit_result["jobId"]

        # 轮询直到完成
        start_time = time.time()
        while True:
            status_result = self.get_job_status(job_id)
            status = status_result.get("status")

            if status in ("completed", "failed", "cancelled"):
                if status == "completed":
                    return status_result.get("response", "")
                elif status == "failed":
                    error = status_result.get("error", "Unknown error")
                    raise RuntimeError(f"Job failed: {error}")
                else:
                    raise RuntimeError("Job was cancelled")

            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Job timed out after {timeout} seconds")

            time.sleep(poll_interval)

    def prompt_continue(self, text: str, **kwargs) -> str:
        """
        继续上一次的对话线程

        Args:
            text: 自然语言提示词
            **kwargs: 传递给 prompt() 的其他参数

        Returns:
            代理的响应文本
        """
        if not self.last_thread_id:
            raise RuntimeError(
                "No previous thread to continue. Start a new conversation first."
            )
        return self.prompt(text, thread_id=self.last_thread_id, **kwargs)

    def sign(
        self,
        signature_type: str,
        message: str | None = None,
        typed_data: dict[str, str] | None = None,
        transaction: dict[str, str] | None = None,
    ) -> dict:
        """
        签名消息/交易（同步）

        Args:
            signature_type: 签名类型 (personal_sign, eth_signTypedData_v4, eth_signTransaction)
            message: 普通文本消息（用于 personal_sign）
            typed_data: EIP-712 类型数据（用于 eth_signTypedData_v4）
            transaction: 交易对象（用于 eth_signTransaction）

        Returns:
            签名结果
        """
        url = f"{self.api_url}/agent/sign"
        data: dict[str, Any] = {"signatureType": signature_type}

        if message:
            data["message"] = message
        if typed_data:
            data["typedData"] = typed_data
        if transaction:
            data["transaction"] = transaction

        response = requests.post(url, headers=self.get_headers(), json=data)
        response.raise_for_status()
        return response.json()

    def submit_transaction(
        self,
        transaction: dict,
        description: str,
        wait_for_confirmation: bool = True,
    ) -> dict:
        """
        提交原始交易（同步）

        Args:
            transaction: 交易对象 {to, data, value, chainId, ...}
            wait_for_confirmation: 是否等待链上确认

        Returns:
            交易结果
        """
        url = f"{self.api_url}/agent/submit"
        data = {
            "transaction": transaction,
            "description": description,
            "waitForConfirmation": wait_for_confirmation,
        }

        response = requests.post(url, headers=self.get_headers(), json=data)
        response.raise_for_status()
        return response.json()

    def get_user_info(self) -> dict:
        """
        查询用户信息

        Returns:
            用户信息
        """
        url = f"{self.api_url}/agent/me"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    # ==================== 便捷方法 ====================

    def get_balance(self, chain: str | None = None) -> str:
        """
        查询余额

        Args:
            chain: 指定链（可选，如 "Base", "Ethereum", "Solana" 等）

        Returns:
            余额信息
        """
        prompt = "What is my balance?"
        if chain:
            prompt = f"What is my balance on {chain}?"
        return self.prompt(prompt)

    def get_portfolio(self) -> str:
        """
        查询完整投资组合

        Returns:
            投资组合信息
        """
        return self.prompt("Show my complete portfolio")

    def get_price(self, token: str) -> str:
        """
        查询代币价格

        Args:
            token: 代币符号或名称

        Returns:
            价格信息
        """
        return self.prompt(f"What's the price of {token}?")

    def buy(self, token: str, amount: str, chain: str = "Base") -> str:
        """
        买入代币

        Args:
            token: 代币符号
            amount: 金额（如 "$50", "0.1 ETH"）
            chain: 链名称

        Returns:
            交易结果
        """
        return self.prompt(f"Buy {amount} of {token} on {chain}")

    def sell(self, token: str, amount: str, chain: str | None = None) -> str:
        """
        卖出代币

        Args:
            token: 代币符号
            amount: 金额（如 "50%", "100 USDC"）
            chain: 链名称（可选）

        Returns:
            交易结果
        """
        prompt = f"Sell {amount} of {token}"
        if chain:
            prompt += f" on {chain}"
        return self.prompt(prompt)

    def swap(
        self, from_token: str, to_token: str, amount: str, chain: str | None = None
    ) -> str:
        """
        兑换代币

        Args:
            from_token: 源代币
            to_token: 目标代币
            amount: 金额
            chain: 链名称（可选）

        Returns:
            交易结果
        """
        prompt = f"Swap {amount} {from_token} for {to_token}"
        if chain:
            prompt += f" on {chain}"
        return self.prompt(prompt)

    def transfer(
        self, token: str, amount: str, recipient: str, chain: str | None = None
    ) -> str:
        """
        转账

        Args:
            token: 代币符号
            amount: 金额
            recipient: 接收地址、ENS 或社交账号（如 "vitalik.eth", "@friend"）
            chain: 链名称（可选）

        Returns:
            交易结果
        """
        prompt = f"Send {amount} {token} to {recipient}"
        if chain:
            prompt += f" on {chain}"
        return self.prompt(prompt)

    def bridge(self, token: str, amount: str, from_chain: str, to_chain: str) -> str:
        """
        跨链桥接

        Args:
            token: 代币符号
            amount: 金额
            from_chain: 源链
            to_chain: 目标链

        Returns:
            交易结果
        """
        return self.prompt(f"Bridge {amount} {token} from {from_chain} to {to_chain}")

    def set_limit_order(
        self, token: str, target_price: str, amount: str, side: str = "buy"
    ) -> str:
        """
        设置限价单

        Args:
            token: 代币符号
            target_price: 目标价格
            amount: 金额
            side: buy 或 sell

        Returns:
            订单结果
        """
        action = "Buy" if side == "buy" else "Sell"
        return self.prompt(
            f"Set limit order to {action.lower()} {amount} {token} at {target_price}"
        )

    def set_stop_loss(self, token: str, stop_price: str) -> str:
        """
        设置止损

        Args:
            token: 代币符号
            stop_price: 止损价格

        Returns:
            订单结果
        """
        return self.prompt(f"Set stop loss for {token} at {stop_price}")

    def set_dca(self, token: str, amount: str, frequency: str) -> str:
        """
        设置 DCA（定投）策略

        Args:
            token: 代币符号
            amount: 每次投入金额
            frequency: 频率（如 "weekly", "daily"）

        Returns:
            策略结果
        """
        return self.prompt(f"DCA {amount} into {token} every {frequency}")

    def open_leverage_position(
        self, token: str, side: str, leverage: int, amount: str
    ) -> str:
        """
        开仓杠杆交易

        Args:
            token: 代币符号
            side: long 或 short
            leverage: 杠杆倍数（最高 50x 加密货币，100x 外汇/商品）
            amount: 金额

        Returns:
            交易结果
        """
        return self.prompt(f"Open {leverage}x {side} on {token} with {amount}")

    def place_polymarket_bet(self, market: str, outcome: str, amount: str) -> str:
        """
        在 Polymarket 下注

        Args:
            market: 市场名称或描述
            outcome: 下注结果（如 "Yes", "No"）
            amount: 金额

        Returns:
            下注结果
        """
        return self.prompt(f"Bet {amount} on {outcome} for {market}")

    def deploy_token(self, name: str, symbol: str, chain: str = "Base") -> str:
        """
        部署代币

        Args:
            name: 代币名称
            symbol: 代币符号
            chain: 链名称（Base 或 Solana）

        Returns:
            部署结果
        """
        return self.prompt(
            f"Deploy a token called {name} with symbol {symbol} on {chain}"
        )


if __name__ == "__main__":
    load_dotenv(override=True)

    bankr = Bankr(
        api_key=os.environ["BANKR_KEY"],
        api_url=os.environ["BANKR_URL"],
    )

    pprint(bankr.get_user_info())
