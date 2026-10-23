import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeQuantityForSymbol, scoreOrderSubmitCandidate, isPositionsTabText } from '../src/core/tradingExec.js';

test('normalizes BTCUSDT quantity to TradingView paper step', () => {
  const result = normalizeQuantityForSymbol(0.000781, 'BINANCE:BTCUSDT');

  assert.equal(result.quantity, 0.0008);
  assert.equal(result.step, 0.0001);
  assert.equal(result.adjusted, true);
});

test('keeps already-valid BTCUSDT quantity unchanged', () => {
  const result = normalizeQuantityForSymbol(0.0008, 'BTCUSDT');

  assert.equal(result.quantity, 0.0008);
  assert.equal(result.adjusted, false);
});

test('leaves unknown symbols untouched', () => {
  const result = normalizeQuantityForSymbol(12.34567, 'EURUSD');

  assert.equal(result.quantity, 12.34567);
  assert.equal(result.step, null);
  assert.equal(result.adjusted, false);
});

test('rejects quote price buttons as order submit candidates', () => {
  const result = scoreOrderSubmitCandidate({
    text: 'Sell76,497.13',
    side: 'buy',
    orderType: 'market',
    symbol: 'BINANCE:BTCUSDT',
  });

  assert.equal(result.score, -1);
  assert.equal(result.reason, 'quote_price_button');
});

test('scores the real TradingView order-ticket submit button above quote buttons', () => {
  const quote = scoreOrderSubmitCandidate({
    text: 'Sell76,497.13',
    side: 'buy',
    orderType: 'market',
    symbol: 'BINANCE:BTCUSDT',
    y: 210,
  });
  const submit = scoreOrderSubmitCandidate({
    text: 'Buy 0.0006 BTCUSDT MARKET',
    dataName: 'submit-button',
    side: 'buy',
    orderType: 'market',
    symbol: 'BINANCE:BTCUSDT',
    y: 707,
  });

  assert.equal(quote.score, -1);
  assert.ok(submit.score > 100);
});

test('rejects opposite-side order-ticket submit buttons', () => {
  const result = scoreOrderSubmitCandidate({
    text: 'Sell 0.0007 BTCUSDT MARKET',
    dataName: 'place-and-modify-button',
    side: 'buy',
    orderType: 'market',
    symbol: 'BINANCE:BTCUSDT',
    y: 688,
  });

  assert.equal(result.score, -1);
  assert.equal(result.reason, 'opposite_side_submit_button');
});

test('recognizes TradingView positions tab with count suffix', () => {
  assert.equal(isPositionsTabText('Positions'), true);
  assert.equal(isPositionsTabText('Positions 1'), true);
  assert.equal(isPositionsTabText('Positions 12'), true);
  assert.equal(isPositionsTabText('Orders 1'), false);
  assert.equal(isPositionsTabText('Order history'), false);
});
