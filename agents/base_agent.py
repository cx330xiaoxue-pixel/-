"""
Agent 基类 — 所有管线 Agent 的抽象基类

功能:
  - 统一 LLM 调用接口 (call_llm)
  - 日志记录与状态持久化 (log, save_state, load_state)
  - 执行超时与重试控制
  - Provider 无关 (DeepSeek / OpenAI / Custom)
  - 抽象方法 execute() 供子类实现

使用方式:
  class NovelAnalyzer(BaseAgent):
      def execute(self, title, author, state_manager, **kwargs):
          # 实现分析逻辑
          pass
"""

import json
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from openai import OpenAI


class BaseAgent(ABC):
    """所有管线 Agent 的抽象基类"""

    # Agent 元信息（子类应覆盖）
    agent_name: str = "base"
    agent_display_name: str = "Base Agent"
    agent_description: str = ""
    agent_version: str = "2.0"
    phase: str = ""  # 所属管线阶段

    def __init__(
        self,
        config: dict = None,
        state_manager=None,
        llm_client: OpenAI = None,
        llm_model: str = None,
        light_client: OpenAI = None,
        light_model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        max_retries: int = 3,
        timeout: float = 300.0,
    ):
        """
        初始化 Agent 基类。

        Args:
            config: 全局配置字典（config.yaml 内容）
            state_manager: AgentStateManager 实例
            llm_client: OpenAI 客户端实例
            llm_model: LLM 模型名称
            light_client: 轻量 LLM 客户端（用于简单任务）
            light_model: 轻量 LLM 模型
            temperature: 温度参数
            max_tokens: 最大 token 数
            max_retries: LLM 调用最大重试次数
            timeout: LLM 调用超时时间（秒）
        """
        self.config = config or {}
        self.state_manager = state_manager

        # LLM 配置
        llm_cfg = self.config.get("llm", {})
        light_cfg = self.config.get("llm_light", llm_cfg)

        self.llm_client = llm_client or OpenAI(
            api_key=llm_cfg.get("api_key", ""),
            base_url=llm_cfg.get("base_url", ""),
        )
        self.llm_model = llm_model or llm_cfg.get("model", "deepseek-chat")
        self.llm_temperature = temperature or llm_cfg.get("temperature", 0.7)
        self.llm_max_tokens = max_tokens or llm_cfg.get("max_tokens", 8192)

        self.light_client = light_client or OpenAI(
            api_key=light_cfg.get("api_key", llm_cfg.get("api_key", "")),
            base_url=light_cfg.get("base_url", llm_cfg.get("base_url", "")),
        )
        self.light_model = light_model or light_cfg.get("model", self.llm_model)

        self.max_retries = max_retries
        self.timeout = timeout

        # 执行统计
        self.execution_count: int = 0
        self.total_duration: float = 0.0
        self.total_tokens: int = 0

    # ═══════════════════════════════════════════════════════════
    # 抽象方法
    # ═══════════════════════════════════════════════════════════

    @abstractmethod
    def execute(self, **kwargs) -> dict:
        """
        执行 Agent 核心逻辑（子类必须实现）。

        Returns:
            包含执行结果的字典，通常包含:
              - status: 'completed' | 'failed' | 'partial'
              - 阶段特定字段
        """
        pass

    # ═══════════════════════════════════════════════════════════
    # LLM 调用
    # ═══════════════════════════════════════════════════════════

    def call_llm(
        self,
        prompt: str,
        system_prompt: str = None,
        use_light: bool = False,
        expect_json: bool = True,
        json_schema: str = None,
        temperature: float = None,
        max_tokens: int = None,
        extra_messages: list = None,
    ) -> list | str:
        """
        统一的 LLM 调用接口，带重试、JSON 解析容错、日志记录。

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            use_light: 是否使用轻量模型
            expect_json: 是否期望返回 JSON 数组
            json_schema: 期望的 JSON Schema 描述（注入 system prompt）
            temperature: 温度（覆盖实例默认值）
            max_tokens: 最大 token（覆盖实例默认值）
            extra_messages: 额外消息列表

        Returns:
            JSON 解析后的 list（expect_json=True），
            或原始文本字符串（expect_json=False）
        """
        client = self.light_client if use_light else self.llm_client
        model = self.light_model if use_light else self.llm_model
        temp = temperature if temperature is not None else (
            0.3 if use_light else self.llm_temperature
        )
        tokens = max_tokens or (2048 if use_light else self.llm_max_tokens)

        # 构建 system prompt
        if system_prompt is None:
            system_prompt = (
                f"你是 {self.agent_display_name}，{self.agent_description}。"
            )
        if json_schema:
            system_prompt += f"\n\n输出格式要求：\n{json_schema}"
        if expect_json:
            system_prompt += "\n请严格输出 JSON 格式，用 ```json ``` 代码块包裹。"

        messages = [{"role": "system", "content": system_prompt}]
        if extra_messages:
            messages.extend(extra_messages)
        messages.append({"role": "user", "content": prompt})

        for attempt in range(self.max_retries):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=tokens,
                    stream=False,
                    timeout=self.timeout,
                )
                raw = resp.choices[0].message.content

                # 记录 token 使用
                if resp.usage:
                    self.total_tokens += resp.usage.total_tokens

                if not expect_json:
                    return raw.strip()

                # JSON 解析
                parsed = self._parse_json(raw)
                if parsed is not None:
                    return parsed

                self.log(
                    f"JSON 解析失败 (attempt {attempt + 1}/{self.max_retries}): "
                    f"{raw[:200]}...",
                    level="warning",
                )

                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

            except Exception as e:
                self.log(
                    f"LLM 调用失败 (attempt {attempt + 1}/{self.max_retries}): {e}",
                    level="error",
                )
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

        return [] if expect_json else ""

    def call_llm_structured(
        self,
        prompt: str,
        output_schema: dict,
        system_prompt: str = None,
        use_light: bool = False,
    ) -> dict:
        """
        使用结构化输出调用 LLM（带 Schema 约束）。

        Args:
            prompt: 用户提示词
            output_schema: JSON Schema 定义
            system_prompt: 系统提示词
            use_light: 是否使用轻量模型

        Returns:
            符合 Schema 的字典
        """
        schema_desc = json.dumps(output_schema, ensure_ascii=False, indent=2)
        json_schema = f"请按照以下 JSON Schema 输出：\n```json\n{schema_desc}\n```"
        result = self.call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            use_light=use_light,
            expect_json=True,
            json_schema=json_schema,
        )
        return result

    # ═══════════════════════════════════════════════════════════
    # JSON 解析（多层容错）
    # ═══════════════════════════════════════════════════════════

    def _parse_json(self, raw: str) -> Optional[Any]:
        """多层 JSON 解析策略"""
        # 策略1: ```json ``` 代码块
        m = re.search(r"```json\s*([\[\{][\s\S]*?[\]\}])\s*```", raw)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 策略2: 直接 JSON
        stripped = raw.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass

        # 策略3: 正则提取 JSON 数组或对象
        m2 = re.search(r"[\[\{][\s\S]*[\]\}]", raw)
        if m2:
            try:
                return json.loads(m2.group(0))
            except json.JSONDecodeError:
                pass

        # 策略4: 修复常见错误（尾逗号、单引号）
        if m2:
            try:
                fixed = m2.group(0)
                fixed = re.sub(r",\s*\]", "]", fixed)
                fixed = re.sub(r",\s*\}", "}", fixed)
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

        return None

    # ═══════════════════════════════════════════════════════════
    # 便捷 LLM 方法
    # ═══════════════════════════════════════════════════════════

    def ask_llm(self, prompt: str, system_prompt: str = None) -> str:
        """
        向 LLM 提问，返回纯文本回答（不期望 JSON）。

        Args:
            prompt: 问题
            system_prompt: 系统提示词

        Returns:
            LLM 的文本回答
        """
        return self.call_llm(prompt, system_prompt, expect_json=False)

    def classify(
        self, text: str, categories: list[str], context: str = ""
    ) -> dict:
        """
        对文本进行分类。

        Args:
            text: 待分类文本
            categories: 分类标签列表
            context: 上下文信息

        Returns:
            {category, confidence, reasoning}
        """
        prompt = f"""
请将以下文本分类到以下类别之一：

类别: {', '.join(categories)}

上下文: {context or '无'}

文本:
{text[:2000]}

请输出 JSON:
{{"category": "选中的类别", "confidence": 0.0-1.0, "reasoning": "分类理由"}}
"""
        return self.call_llm(prompt, use_light=True, expect_json=True)

    def summarize(
        self, text: str, max_length: int = 200, focus: str = ""
    ) -> str:
        """
        对文本进行摘要。

        Args:
            text: 待摘要文本
            max_length: 最大长度（字符数）
            focus: 摘要侧重点

        Returns:
            摘要文本
        """
        focus_hint = f"\n请重点关注: {focus}" if focus else ""
        prompt = f"""
请对以下文本进行摘要，不超过 {max_length} 字。{focus_hint}

文本:
{text[:4000]}
"""
        return self.call_llm(prompt, use_light=True, expect_json=False)

    def extract_keywords(self, text: str, top_n: int = 10) -> list[str]:
        """
        提取关键词。

        Args:
            text: 文本
            top_n: 返回前 N 个关键词

        Returns:
            关键词列表
        """
        prompt = f"""
请从以下文本中提取 {top_n} 个最重要的关键词或短语。

文本:
{text[:3000]}

输出 JSON 数组: ["关键词1", "关键词2", ...]
"""
        return self.call_llm(prompt, use_light=True, expect_json=True)

    # ═══════════════════════════════════════════════════════════
    # 日志与状态
    # ═══════════════════════════════════════════════════════════

    def log(self, message: str, level: str = "info", **extra):
        """
        记录执行日志。

        Args:
            message: 日志消息
            level: 日志级别 (info | warning | error | debug)
            **extra: 额外上下文
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        level_icon = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "debug": "🔍",
        }.get(level, "📝")

        print(f"{level_icon} [{timestamp}] [{self.agent_name}] {message}")

    def save_state(self, key: str, value: Any):
        """
        保存 Agent 的持久化状态（写入 .agent-state.json 中的 agents 命名空间）。

        Args:
            key: 状态键
            value: 状态值
        """
        if self.state_manager:
            # 在 state 中创建 agents 命名空间
            if "agents" not in self.state_manager.state:
                self.state_manager.state["agents"] = {}
            if self.agent_name not in self.state_manager.state["agents"]:
                self.state_manager.state["agents"][self.agent_name] = {}
            self.state_manager.state["agents"][self.agent_name][key] = value
            self.state_manager._save()

    def load_state(self, key: str, default: Any = None) -> Any:
        """
        加载 Agent 的持久化状态。

        Args:
            key: 状态键
            default: 默认值

        Returns:
            状态值
        """
        if self.state_manager:
            agents_ns = self.state_manager.state.get("agents", {})
            agent_ns = agents_ns.get(self.agent_name, {})
            return agent_ns.get(key, default)
        return default

    def record_execution(
        self,
        status: str = "success",
        input_summary: str = "",
        output_summary: str = "",
        duration_seconds: float = 0.0,
        error_message: str = "",
    ):
        """
        记录一次 Agent 执行到 StateManager。

        Args:
            status: success | failed | skipped
            input_summary: 输入摘要
            output_summary: 输出摘要
            duration_seconds: 耗时
            error_message: 错误信息
        """
        if self.state_manager:
            self.state_manager.log_agent_execution(
                agent_name=self.agent_name,
                phase=self.phase,
                episode=None,  # 子类可覆盖
                input_summary=input_summary,
                output_summary=output_summary,
                duration_seconds=duration_seconds,
                status=status,
                error_message=error_message,
                token_usage={"total_tokens": self.total_tokens},
            )

    # ═══════════════════════════════════════════════════════════
    # 执行包装器
    # ═══════════════════════════════════════════════════════════

    def run(self, **kwargs) -> dict:
        """
        执行 Agent 并自动记录日志和状态。

        这是 execute() 的包装器，提供了:
          - 计时
          - 自动日志记录
          - 错误处理
          - 状态持久化

        Returns:
            {status, result, duration_seconds, ...}
        """
        start_time = time.time()
        self.execution_count += 1

        self.log(f"开始执行 (第{self.execution_count}次)",
                 phase=kwargs.get("phase", self.phase))

        try:
            result = self.execute(**kwargs)
            duration = time.time() - start_time
            self.total_duration += duration

            status = result.get("status", "completed")
            self.record_execution(
                status=status,
                input_summary=str(kwargs.get("input_summary", ""))[:500],
                output_summary=str(result.get("message", ""))[:500],
                duration_seconds=duration,
            )

            self.log(
                f"执行完成 ({duration:.1f}s, status={status})",
                level="info",
            )
            result["duration_seconds"] = round(duration, 1)
            result["agent_name"] = self.agent_name
            return result

        except Exception as e:
            duration = time.time() - start_time
            self.total_duration += duration

            self.log(f"执行失败: {e}", level="error")
            self.record_execution(
                status="failed",
                input_summary=str(kwargs.get("input_summary", ""))[:500],
                duration_seconds=duration,
                error_message=str(e)[:500],
            )

            return {
                "status": "failed",
                "error": str(e),
                "duration_seconds": round(duration, 1),
                "agent_name": self.agent_name,
            }

    # ═══════════════════════════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════════════════════════

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        从全局配置中获取值（支持嵌套键，用 . 分隔）。

        Args:
            key: 配置键，如 'llm.model' 或 'processing.window_size'
            default: 默认值
        """
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value

    @property
    def info(self) -> dict:
        """Agent 信息摘要"""
        return {
            "name": self.agent_name,
            "display_name": self.agent_display_name,
            "description": self.agent_description,
            "version": self.agent_version,
            "phase": self.phase,
            "execution_count": self.execution_count,
            "total_duration": round(self.total_duration, 1),
            "total_tokens": self.total_tokens,
        }

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}("
            f"name={self.agent_name}, "
            f"executions={self.execution_count}, "
            f"tokens={self.total_tokens})>"
        )
