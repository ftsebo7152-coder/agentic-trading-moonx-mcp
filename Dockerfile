FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir '.[cloud,mcp]' && useradd --uid 10001 --create-home trader
COPY configs ./configs
COPY examples ./examples
RUN mkdir /app/state && chown trader:trader /app/state
USER trader
ENV TRADING_DATABASE_URL=/app/state/trading.sqlite
CMD ["python", "-m", "agentic_trading.cli", "worker", "--config", "configs/paper.json", "--bundle", "examples/synthetic-market.json"]
