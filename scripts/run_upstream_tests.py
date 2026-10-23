"""Run vendored offline suites only. Never start TradingView or a broker."""
from pathlib import Path
import os,subprocess,sys,shutil

root=Path(__file__).resolve().parents[1]
tmp=root/'test-results/tmp';tmp.mkdir(parents=True,exist_ok=True)
env={**os.environ,'TMP':str(tmp),'TEMP':str(tmp)}
commands=[([sys.executable,'-m','unittest','discover','-s','tests','-q'],root/'vendor/day-trader-fr')]
node=shutil.which('node')
if node:
    js=root/'vendor/codex-tradingview-xau-btc-mcp'
    if (js/'node_modules').exists():
        commands.append(([node,'--test','tests/pine_analyze.test.js','tests/cli.test.js','tests/launch.test.js','tests/sanitization.test.js','tests/trading_exec.test.js','tests/trading_orders_filter.test.js'],js))
    else:print('TradingView suite skipped: install its locked dependencies with npm ci --ignore-scripts.')
for command,cwd in commands:
    print('Running offline suite:',cwd.name,flush=True)
    subprocess.run(command,cwd=cwd,env=env,check=True)
