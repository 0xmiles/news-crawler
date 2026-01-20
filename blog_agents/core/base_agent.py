"""Base agent class for all blog agents."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from anthropic import Anthropic, AsyncAnthropic
from blog_agents.config.agent_config import Config
from blog_agents.utils.retry import async_retry, RetryableError
from blog_agents.core.communication import AgentMessage, AgentStatus

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, config: Config, agent_name: str):
        """Initialize base agent.

        Args:
            config: System configuration
            agent_name: Name of this agent
        """
        self.config = config
        self.agent_name = agent_name

        # Initialize Anthropic client
        self.client = AsyncAnthropic(api_key=config.ai.api_key)
        self.sync_client = Anthropic(api_key=config.ai.api_key)

        # Agent configuration
        self.model = config.ai.model
        self.max_tokens = config.ai.max_tokens
        self.temperature = config.ai.temperature
        self.max_retries = config.blog_agents.max_retries

        logger.info(f"Initialized {self.agent_name}")

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent's main task.

        Args:
            input_data: Input data for the agent

        Returns:
            Output data from agent execution

        Raises:
            Exception: If execution fails
        """
        pass

    @async_retry(max_attempts=3)
    async def call_claude(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Call Claude API with retry logic.

        Args:
            system_prompt: System prompt for Claude
            user_message: User message
            temperature: Temperature override
            max_tokens: Max tokens override

        Returns:
            Claude's response text

        Raises:
            RetryableError: If API call fails
        """
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature if temperature is not None else self.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            # Extract text from response
            if response.content and len(response.content) > 0:
                return response.content[0].text

            raise RetryableError("Empty response from Claude API")

        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise RetryableError(f"Claude API error: {e}")

    async def create_message(
        self,
        status: AgentStatus,
        data: Dict[str, Any],
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentMessage:
        """Create agent message.

        Args:
            status: Agent status
            data: Output data
            error: Error message if any
            metadata: Additional metadata

        Returns:
            Agent message
        """
        return AgentMessage(
            agent_name=self.agent_name,
            status=status,
            data=data,
            error=error,
            metadata=metadata or {}
        )

    def log_execution_start(self, input_data: Dict[str, Any]):
        """Log execution start.

        Args:
            input_data: Input data
        """
        logger.info(f"[{self.agent_name}] Starting execution")
        logger.debug(f"[{self.agent_name}] Input: {input_data}")

    def log_execution_complete(self, output_data: Dict[str, Any]):
        """Log execution completion.

        Args:
            output_data: Output data
        """
        logger.info(f"[{self.agent_name}] Execution completed")
        logger.debug(f"[{self.agent_name}] Output: {output_data}")

    def log_execution_error(self, error: Exception):
        """Log execution error.

        Args:
            error: Exception that occurred
        """
        logger.error(f"[{self.agent_name}] Execution failed: {error}")

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data.

        Args:
            input_data: Input data to validate

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        # Base validation - subclasses can override
        if not isinstance(input_data, dict):
            raise ValueError("Input data must be a dictionary")
        return True

    async def validate_output(self, output_data: Dict[str, Any]) -> bool:
        """Validate output data.

        Args:
            output_data: Output data to validate

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        # Base validation - subclasses can override
        if not isinstance(output_data, dict):
            raise ValueError("Output data must be a dictionary")
        return True

    async def run(self, input_data: Dict[str, Any]) -> AgentMessage:
        """Run agent with full error handling and logging.

        Args:
            input_data: Input data

        Returns:
            Agent message with results

        Raises:
            Exception: If execution fails after retries
        """
        try:
            # Validate input
            await self.validate_input(input_data)

            # Log start
            self.log_execution_start(input_data)

            # Execute
            output_data = await self.execute(input_data)

            # Validate output
            await self.validate_output(output_data)

            # Log completion
            self.log_execution_complete(output_data)

            # Create success message
            return await self.create_message(
                status=AgentStatus.COMPLETED,
                data=output_data
            )

        except Exception as e:
            # Log error
            self.log_execution_error(e)

            # Create error message
            return await self.create_message(
                status=AgentStatus.FAILED,
                data={},
                error=str(e)
            )
