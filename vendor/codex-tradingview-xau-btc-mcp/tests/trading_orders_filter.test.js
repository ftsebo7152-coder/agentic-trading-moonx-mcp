import test from 'node:test';
import assert from 'node:assert/strict';
import { isTerminalOrderRow } from '../src/core/trading.js';

test('terminal filled order rows are filtered from active orders', () => {
  assert.equal(isTerminalOrderRow(['BINANCE:BTCUSDT', 'Buy', 'Market', 'filled']), true);
});

test('terminal cancelled bracket rows are filtered from active orders', () => {
  assert.equal(isTerminalOrderRow(['BINANCE:BTCUSDT', 'Sell', 'Stop Loss', 'cancelled']), true);
});

test('working order rows remain active', () => {
  assert.equal(isTerminalOrderRow(['BINANCE:BTCUSDT', 'Sell', 'Limit', 'working']), false);
});

test('executed market rows without explicit filled status are filtered', () => {
  assert.equal(isTerminalOrderRow(['BINANCE:BTCUSDT', 'Buy', 'Market', '0.0034', '74,278.81']), true);
});

test('working stop-loss rows remain active', () => {
  assert.equal(isTerminalOrderRow(['BINANCE:BTCUSDT', 'Sell', 'Stop Loss', '0.0068', '73,334.85']), false);
});
