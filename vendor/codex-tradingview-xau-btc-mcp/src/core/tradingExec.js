/**
 * Trade execution — gated by explicit user consent.
 *
 * ┌──────────────────────────────────────────────────────────────────┐
 * │  CONSENT MODEL                                                    │
 * │                                                                   │
 * │  Every function in this module REQUIRES `consent === true` as an  │
 * │  argument. Without it, the function throws before touching CDP.   │
 * │                                                                   │
 * │  This is a deliberate architectural choice — it makes it          │
 * │  impossible to accidentally trigger an order from an AI tool, a   │
 * │  script, or a chained tool call without the caller explicitly     │
 * │  stating "yes, I know this places/cancels/closes a real order".   │
 * │                                                                   │
 * │  The same consent gate applies to paper trading and live broker   │
 * │  trading. The function reports which mode is active in the result │
 * │  so downstream code can react accordingly.                        │
 * └──────────────────────────────────────────────────────────────────┘
 *
 * Implementation strategy:
 *   TradingView does not expose a programmatic broker API via its
 *   public chart widget. All execution goes through DOM automation of
 *   the Trading Panel + Order Dialog, using data-name attributes and
 *   keyboard shortcuts as fallbacks.
 */
import { evaluate, getClient } from '../connection.js';
import { sleep, waitForCondition } from '../await.js';
import { escapeJsString, validateNumber } from '../sanitize.js';
import { ErrorCodes } from '../errors.js';

const QUANTITY_RULES = [
  { pattern: /BTC(USD|USDT)?/i, step: 0.0001, decimals: 4 },
  { pattern: /ETH(USD|USDT)?/i, step: 0.001, decimals: 3 },
  { pattern: /XAU(USD)?|GOLD/i, step: 0.01, decimals: 2 },
];

/**
 * Refuses to proceed unless the caller has explicitly asserted consent.
 * Exported so tool wrappers can share the exact same gate.
 */
export function requireConsent(consent, operation) {
  if (consent !== true) {
    const err = new Error(
      `Explicit consent required to ${operation}. Pass { consent: true } to acknowledge this will affect real orders (or paper-trading simulated orders). This gate exists to prevent accidental execution by AI tools or scripts.`,
    );
    err.code = ErrorCodes.INVALID_INPUT;
    throw err;
  }
}

async function getActiveTradingSymbol() {
  const result = await evaluate(`
    (function() {
      try {
        var symbol = '';
        try {
          var chart = window.tvWidget?.activeChart?.()
            || window.TradingViewApi?.activeChart?.()
            || window.tvWidget?.chart?.();
          if (chart) {
            try { symbol = chart.symbol(); } catch(e) {}
            if (!symbol && chart.symbolExt) {
              try { symbol = chart.symbolExt().symbol || ''; } catch(e2) {}
            }
          }
        } catch(e3) {}
        if (!symbol) {
          var title = document.querySelector('[data-symbol-full], [data-name="legend-source-title"], [aria-label*="/"]');
          symbol = title?.getAttribute?.('data-symbol-full') || title?.textContent || '';
        }
        return String(symbol || '').trim();
      } catch(e) { return ''; }
    })()
  `);
  return result || '';
}

function getQuantityRule(symbol = '') {
  return QUANTITY_RULES.find((rule) => rule.pattern.test(symbol)) || null;
}

export function normalizeQuantityForSymbol(quantity, symbol = '') {
  const qty = validateNumber(quantity, 'quantity');
  const rule = getQuantityRule(symbol);
  if (!rule) {
    return {
      quantity: qty,
      requested_quantity: qty,
      adjusted: false,
      symbol,
      step: null,
      decimals: null,
    };
  }

  // Round to the nearest valid step. If rounding would become zero, round up
  // to one step so tiny paper-trading tests do not create a disabled ticket.
  let rounded = Math.round(qty / rule.step) * rule.step;
  if (rounded <= 0) rounded = rule.step;
  rounded = Number(rounded.toFixed(rule.decimals));

  return {
    quantity: rounded,
    requested_quantity: qty,
    adjusted: Math.abs(rounded - qty) > Number.EPSILON,
    symbol,
    step: rule.step,
    decimals: rule.decimals,
  };
}

export function scoreOrderSubmitCandidate({ text = '', dataName = '', side = '', orderType = '', symbol = '', y = 0 } = {}) {
  const txt = String(text || '').replace(/\s+/g, ' ').trim();
  const dn = String(dataName || '');
  const lower = txt.toLowerCase();
  const sideWord = side === 'sell' ? 'sell' : 'buy';
  const oppositeSideWord = sideWord === 'buy' ? 'sell' : 'buy';
  const symbolBase = String(symbol || '').split(':').pop().toLowerCase();
  const symbolRoot = symbolBase.replace(/[^a-z0-9]/g, '');

  if (!txt && !dn) return { score: -1, reason: 'empty' };
  if (/^(sell|buy)\s*[\d.,]+$/i.test(txt)) {
    return { score: -1, reason: 'quote_price_button' };
  }
  if (/\b(strong\s+buy|strong\s+sell|technical|seasonal|more)\b/i.test(txt)) {
    return { score: -1, reason: 'non_trading_widget_button' };
  }
  if (new RegExp('^' + oppositeSideWord + '\\b', 'i').test(txt)) {
    return { score: -1, reason: 'opposite_side_submit_button' };
  }
  if (/\b(market|limit|stop)\b/i.test(txt) && new RegExp('\\b' + oppositeSideWord + '\\b', 'i').test(txt)) {
    return { score: -1, reason: 'opposite_side_order_ticket_button' };
  }

  let score = 0;
  if (dn === 'submit' || dn === 'submit-button') score += 40;
  if (lower.includes(sideWord)) score += 35;
  if (orderType && lower.includes(orderType)) score += 25;
  if (symbolRoot && lower.replace(/[^a-z0-9]/g, '').includes(symbolRoot)) score += 25;
  if (/\b(place|create|submit|send|comprar|vender|crear|enviar)\b/i.test(txt)) score += 20;
  if (/\d/.test(txt) && /\b(market|limit|stop)\b/i.test(txt)) score += 15;
  score += Math.min(20, Math.max(0, Number(y) || 0) / 80);

  return { score, reason: 'candidate' };
}

function normalizeUiText(text = '') {
  return String(text || '').replace(/\s+/g, ' ').trim();
}

export function isPositionsTabText(text = '') {
  const normalized = normalizeUiText(text).toLowerCase();
  return /^positions(?:\s+\d+)?$/.test(normalized) || /^positions\b/.test(normalized);
}

async function getOrderDialogInfo() {
  return evaluate(`
    (function() {
      try {
        var dialog = document.querySelector('[data-name="order-dialog"]')
          || document.querySelector('[data-name="order-dialog-popup"]')
          || document.querySelector('[data-dialog-name*="order"]')
          || document.querySelector('[class*="orderDialog"]');
        if (!dialog || dialog.offsetParent === null) return { open: false };
        var text = (dialog.textContent || '').replace(/\\s+/g, ' ').trim();
        var buttons = Array.prototype.slice.call(dialog.querySelectorAll('button, [role="button"]'));
        var submit = buttons
          .map(function(btn) { return (btn.textContent || '').replace(/\\s+/g, ' ').trim(); })
          .filter(function(txt) { return /\\b(buy|sell)\\b/i.test(txt) && /\\b(market|limit|stop)\\b/i.test(txt); })
          .pop() || '';
        return {
          open: true,
          data_name: dialog.getAttribute('data-name') || null,
          text: text.substring(0, 700),
          submit_text: submit.substring(0, 120),
          has_buy: /\\bbuy\\b/i.test(text),
          has_sell: /\\bsell\\b/i.test(text),
          submit_is_buy: /^buy\\b/i.test(submit),
          submit_is_sell: /^sell\\b/i.test(submit)
        };
      } catch(e) { return { open: false, error: e.message }; }
    })()
  `);
}

async function closeOrderDialogIfOpen({ side } = {}) {
  const info = await getOrderDialogInfo();
  if (!info?.open) return { closed: false, reason: 'not_open' };

  const lowerSide = side === 'buy' || side === 'sell' ? side : null;
  const opposingSide =
    lowerSide === 'buy'
      ? info.submit_is_sell || (info.has_sell && !info.has_buy)
      : lowerSide === 'sell'
        ? info.submit_is_buy || (info.has_buy && !info.has_sell)
        : true;

  if (!opposingSide) {
    return { closed: false, reason: 'reuse_existing_dialog', info };
  }

  const clicked = await evaluate(`
    (function() {
      try {
        var dialog = document.querySelector('[data-name="order-dialog"]')
          || document.querySelector('[data-name="order-dialog-popup"]')
          || document.querySelector('[class*="orderDialog"]');
        if (!dialog) return { ok: false, error: 'dialog not found' };
        var buttons = dialog.querySelectorAll('button, [role="button"]');
        for (var i = 0; i < buttons.length; i++) {
          var aria = buttons[i].getAttribute('aria-label') || '';
          var title = buttons[i].getAttribute('title') || '';
          if (/close/i.test(aria) || /close/i.test(title)) {
            buttons[i].click();
            return { ok: true, method: 'close_button' };
          }
        }
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', bubbles: true }));
        return { ok: true, method: 'escape' };
      } catch(e) { return { ok: false, error: e.message }; }
    })()
  `);
  await sleep(250);
  return { closed: !!clicked?.ok, reason: 'opposing_side_dialog', info, clicked };
}

/**
 * Detect whether the active Trading Panel is paper trading or a real
 * broker. Returns one of: "paper", "broker", "unknown", "not_connected".
 *
 * TradingView exposes this in the header of the trading panel — the
 * broker name text. "Paper Trading" or localized equivalent indicates
 * simulation mode.
 */
export async function detectTradingMode() {
  const mode = await evaluate(`
    (function() {
      try {
        var panel = document.querySelector('[data-name="trading-panel"]')
          || document.querySelector('[class*="trading-panel"]')
          || document.querySelector('[class*="tradingPanel"]');
        if (!panel) {
          var bottomArea = document.querySelector('[class*="layout__area--bottom"]');
          if (bottomArea) {
            var tabs = bottomArea.querySelectorAll('[role="tab"], [data-name*="tab"]');
            for (var t = 0; t < tabs.length; t++) {
              var txt = (tabs[t].textContent || '').toLowerCase();
              if (/paper|demo|simulation|simulaci/.test(txt)) return { mode: 'paper', source: 'tab_text' };
              if (/broker|live|real/.test(txt) && !/paper/.test(txt)) return { mode: 'broker', source: 'tab_text' };
            }
          }
          return { mode: 'not_connected', source: 'panel_not_found' };
        }
        var header = panel.querySelector('[class*="header"], [class*="broker-name"], [data-name*="broker"]');
        var headerText = header ? (header.textContent || '').toLowerCase() : '';
        if (/paper|demo|simulation|simulaci/.test(headerText)) return { mode: 'paper', source: 'header', text: headerText.substring(0, 60) };
        if (/connect|conectar/.test(headerText)) return { mode: 'not_connected', source: 'header', text: headerText.substring(0, 60) };
        if (headerText) return { mode: 'broker', source: 'header', text: headerText.substring(0, 60) };
        return { mode: 'unknown', source: 'empty_header' };
      } catch(e) { return { mode: 'unknown', source: 'error', error: e.message }; }
    })()
  `);
  return mode || { mode: 'unknown', source: 'evaluate_null' };
}

/**
 * Make sure the Trading Panel is open. Returns true if it's open after
 * this call, false if we couldn't open it.
 */
async function ensureTradingPanelOpen() {
  const isOpen = await evaluate(`
    (function() {
      var dialog = document.querySelector('[data-name="order-dialog"]')
        || document.querySelector('[data-name="order-dialog-popup"]')
        || document.querySelector('[class*="orderDialog"]');
      if (dialog && dialog.offsetParent !== null) return true;
      var bottom = document.querySelector('[class*="layout__area--bottom"]');
      if (!bottom) {
        bottom = Array.prototype.slice.call(document.querySelectorAll('div, section')).find(function(el) {
          return el.offsetHeight > 80 && /paper trading|positions|orders/i.test(el.textContent || '');
        });
      }
      if (!bottom) return false;
      if (bottom.offsetHeight < 80) return false;
      var selectors = [
        '[data-name="trading-panel"]',
        '[class*="accountManager"]',
        '[class*="account-manager"]',
        '[data-name$=".positions-table"]',
        '[data-name$=".orders-table"]',
        '[class*="trading-panel"]'
      ];
      for (var i = 0; i < selectors.length; i++) {
        var tp = document.querySelector(selectors[i]);
        if (tp && tp.offsetHeight > 50) return true;
      }
      if (/paper trading|positions|orders/i.test(bottom.textContent || '')) return true;
      return false;
    })()
  `);
  if (isOpen) return true;

  // Click the trading panel tab or button
  await evaluate(`
    (function() {
      var btn = document.querySelector('[data-name="trading-button"]')
        || document.querySelector('[aria-label*="Trading"]')
        || document.querySelector('[data-name="tab-trading"]');
      if (btn) btn.click();
    })()
  `);

  const waited = await waitForCondition(
    async () => {
      return evaluate(`
        (function() {
          var dialog = document.querySelector('[data-name="order-dialog"]')
            || document.querySelector('[data-name="order-dialog-popup"]')
            || document.querySelector('[class*="orderDialog"]');
          if (dialog && dialog.offsetParent !== null) return true;
          var selectors = [
            '[data-name="trading-panel"]',
            '[class*="accountManager"]',
            '[class*="account-manager"]',
            '[data-name$=".positions-table"]',
            '[data-name$=".orders-table"]',
            '[class*="trading-panel"]'
          ];
          for (var i = 0; i < selectors.length; i++) {
            var tp = document.querySelector(selectors[i]);
            if (tp && tp.offsetHeight > 50) return true;
          }
          var areas = document.querySelectorAll('div, section');
          for (var j = 0; j < areas.length; j++) {
            if (areas[j].offsetHeight > 80 && /paper trading|positions|orders/i.test(areas[j].textContent || '')) return true;
          }
          return false;
        })()
      `);
    },
    { timeout: 3000, pollMin: 150, pollMax: 400, label: 'tradingPanel' },
  );
  return waited.ok;
}

/**
 * Open the Order Dialog — the full form with quantity, limit/stop price,
 * take profit, stop loss, etc. This is safer than the one-click
 * buy/sell buttons because nothing is submitted until we fill and click
 * "Place Order".
 *
 * Tries in order:
 *   1. Shift+T keyboard shortcut (TradingView's default for Order Dialog)
 *   2. Click the buy/sell-order-button which opens the dialog
 */
async function openOrderDialog({ side }) {
  const existing = await getOrderDialogInfo();
  if (existing?.open) {
    const rightSide =
      side === 'buy'
        ? existing.submit_is_buy || (existing.has_buy && !existing.submit_is_sell)
        : existing.submit_is_sell || (existing.has_sell && !existing.submit_is_buy);
    if (rightSide) return { method: 'existing_dialog', existing };
  }

  // Strategy 1: keyboard shortcut (doesn't work on all builds, but try first)
  const client = await getClient();
  try {
    await client.Input.dispatchKeyEvent({ type: 'keyDown', modifiers: 8, key: 'T', code: 'KeyT', windowsVirtualKeyCode: 84 });
    await client.Input.dispatchKeyEvent({ type: 'keyUp', modifiers: 8, key: 'T', code: 'KeyT' });
  } catch {}

  const dialogOpened = await waitForCondition(
    async () => {
      return evaluate(`
        (function() {
          var d = document.querySelector('[data-name="order-dialog"]')
            || document.querySelector('[data-name="order-dialog-popup"]')
            || document.querySelector('[data-dialog-name*="order"]')
            || document.querySelector('[class*="orderDialog"]');
          return !!(d && d.offsetParent !== null);
        })()
      `);
    },
    { timeout: 1200, pollMin: 100, pollMax: 300 },
  );
  if (dialogOpened.ok) {
    const keyboardDialog = await getOrderDialogInfo();
    const rightSide =
      side === 'buy'
        ? keyboardDialog.submit_is_buy || (keyboardDialog.has_buy && !keyboardDialog.submit_is_sell)
        : keyboardDialog.submit_is_sell || (keyboardDialog.has_sell && !keyboardDialog.submit_is_buy);
    if (rightSide) return { method: 'keyboard', existing: keyboardDialog };
    await closeOrderDialogIfOpen({ side });
  }

  // Strategy 2: click the buy/sell order button — these open a confirm
  // dialog in most broker integrations.
  const sideButton = side === 'buy' ? 'buy-order-button' : 'sell-order-button';
  const clicked = await evaluate(`
    (function() {
      var btn = document.querySelector('[data-name="${sideButton}"]');
      if (!btn) {
        var sideText = '${side}' === 'buy' ? /\\bbuy\\b/i : /\\bsell\\b/i;
        var candidates = Array.prototype.slice.call(document.querySelectorAll('button, [role="button"], [data-name*="button"]'));
        btn = candidates.find(function(candidate) {
          if (candidate.offsetParent === null) return false;
          var txt = candidate.textContent || candidate.getAttribute('aria-label') || '';
          return sideText.test(txt) && !/strong|technical|seasonal|more/i.test(txt);
        });
      }
      if (!btn) return false;
      btn.click();
      return true;
    })()
  `);
  if (!clicked) {
    const err = new Error(`Could not find ${sideButton} — is the Trading Panel open?`);
    err.code = ErrorCodes.SELECTOR_NOT_FOUND;
    throw err;
  }

  const dialogOpened2 = await waitForCondition(
    async () => {
      return evaluate(`
        (function() {
          var d = document.querySelector('[data-name="order-dialog"]')
            || document.querySelector('[data-name="order-dialog-popup"]')
            || document.querySelector('[data-dialog-name*="order"]')
            || document.querySelector('[class*="orderDialog"]');
          return !!(d && d.offsetParent !== null);
        })()
      `);
    },
    { timeout: 2500, pollMin: 150, pollMax: 400 },
  );
  if (!dialogOpened2.ok) {
    const err = new Error('Order Dialog did not appear after clicking the order button.');
    err.code = ErrorCodes.TIMEOUT_WAITING_FOR_ELEMENT;
    throw err;
  }
  return { method: 'click' };
}

async function selectOrderType(orderType) {
  const label = orderType === 'market' ? 'Market' : orderType === 'limit' ? 'Limit' : 'Stop';
  const escapedLabel = escapeJsString(label);
  const result = await evaluate(`
    (function() {
      try {
        var dialog = document.querySelector('[data-name="order-dialog"]')
          || document.querySelector('[data-name="order-dialog-popup"]')
          || document.querySelector('[class*="orderDialog"]');
        if (!dialog) return { ok: false, error: 'dialog not open' };
        var buttons = dialog.querySelectorAll('button, [role="button"]');
        var target = '${escapedLabel}'.toLowerCase();
        for (var i = 0; i < buttons.length; i++) {
          var txt = (buttons[i].textContent || '').trim().toLowerCase();
          if (txt === target) {
            buttons[i].click();
            return { ok: true, selected: '${escapedLabel}' };
          }
        }
        return { ok: false, error: 'order type tab not found', target: '${escapedLabel}' };
      } catch(e) { return { ok: false, error: e.message }; }
    })()
  `);
  if (!result?.ok) {
    const err = new Error(`Could not select order type ${label}: ${result?.error || 'unknown'}`);
    err.code = ErrorCodes.SELECTOR_NOT_FOUND;
    err.details = result;
    throw err;
  }
  await sleep(250);
  return result;
}

/**
 * Find and set the value of a numeric input inside the Order Dialog by
 * matching its label or placeholder. Uses React's native setter so the
 * framework picks up the change.
 */
async function setDialogField(fieldPattern, value) {
  const pattern = escapeJsString(fieldPattern);
  const val = validateNumber(value, fieldPattern);
  const strVal = escapeJsString(String(val));
  return evaluate(`
    (function() {
      try {
        var dialog = document.querySelector('[data-name="order-dialog"]')
          || document.querySelector('[data-name="order-dialog-popup"]')
          || document.querySelector('[class*="orderDialog"]');
        if (!dialog) return { ok: false, error: 'dialog not open' };
        var inputs = dialog.querySelectorAll('input');
        var pattern = new RegExp('${pattern}', 'i');
        for (var i = 0; i < inputs.length; i++) {
          var inp = inputs[i];
          var labels = [
            inp.name || '',
            inp.placeholder || '',
            inp.getAttribute('aria-label') || '',
            inp.getAttribute('data-name') || '',
          ];
          var parent = inp.closest('[class*="row"], [class*="field"], label');
          if (parent) {
            var lbl = parent.querySelector('[class*="label"], label');
            if (lbl) labels.push(lbl.textContent || '');
          }
          var matched = labels.some(function(l) { return pattern.test(l); });
          if (matched) {
            var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            setter.call(inp, '${strVal}');
            inp.dispatchEvent(new Event('input', { bubbles: true }));
            inp.dispatchEvent(new Event('change', { bubbles: true }));
            inp.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: 'Enter' }));
            inp.blur();
            return { ok: true, field: labels.find(function(l) { return l; }) || 'unknown', value: inp.value };
          }
        }
        if (dialog.getAttribute('data-name') === 'order-dialog-popup') {
          var visibleInputs = Array.prototype.slice.call(inputs).filter(function(candidate) {
            return candidate.offsetParent !== null;
          });
          var field = '${pattern}'.toLowerCase();
          var priceInputs = visibleInputs.filter(function(candidate) {
            return (candidate.className || '').toString().indexOf('priceInput') !== -1;
          });
          var exitInputs = visibleInputs.filter(function(candidate) {
            return (candidate.className || '').toString().indexOf('input-uv5obCI0') !== -1;
          });
          var targetInput = null;
          if (/qty|quantity|cantidad/.test(field)) {
            targetInput = visibleInputs.find(function(candidate) {
              var cls = (candidate.className || '').toString();
              var rect = candidate.getBoundingClientRect();
              return cls.indexOf('priceInput') === -1
                && cls.indexOf('input-uv5obCI0') === -1
                && rect.width > 30
                && rect.height > 10;
            });
          } else if (/^price|precio/.test(field)) {
            targetInput = priceInputs[0] || visibleInputs[0];
          } else if (/take profit|tp|ganancia/.test(field)) {
            targetInput = exitInputs[0] || null;
          } else if (/stop loss|sl|p[eé]rdida/.test(field)) {
            targetInput = exitInputs[1] || null;
          }
          if (targetInput) {
            var fallbackSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            targetInput.focus();
            fallbackSetter.call(targetInput, '${strVal}');
            targetInput.dispatchEvent(new Event('input', { bubbles: true }));
            targetInput.dispatchEvent(new Event('change', { bubbles: true }));
            targetInput.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: 'Enter' }));
            targetInput.blur();
            return { ok: true, field: 'order-dialog-popup fallback', value: targetInput.value };
          }
        }
        return { ok: false, error: 'field not found', tried: inputs.length };
      } catch(e) { return { ok: false, error: e.message }; }
    })()
  `);
}

/**
 * Submit the Order Dialog by clicking "Place Order" / "Create" / "Buy"
 * / "Sell" (the exact text varies by broker and language).
 */
async function submitOrderDialog({ side, orderType, quantity, symbol } = {}) {
  const escapedSide = escapeJsString(side || '');
  const escapedOrderType = escapeJsString(orderType || '');
  const escapedSymbol = escapeJsString(symbol || '');
  const escapedQuantity = escapeJsString(String(quantity ?? ''));
  return evaluate(`
    (function() {
      try {
        var dialog = document.querySelector('[data-name="order-dialog"]')
          || document.querySelector('[data-name="order-dialog-popup"]')
          || document.querySelector('[class*="orderDialog"]');
        if (!dialog) return { ok: false, error: 'dialog not open' };
        var btns = dialog.querySelectorAll('[data-name="submit-button"], button[data-name="submit"], button[type="submit"], button, [role="button"]');
        var side = '${escapedSide}';
        var orderType = '${escapedOrderType}';
        var symbol = '${escapedSymbol}'.split(':').pop().toLowerCase().replace(/[^a-z0-9]/g, '');
        var qty = '${escapedQuantity}';
        var sideWord = side === 'sell' ? 'sell' : 'buy';
        var oppositeSideWord = sideWord === 'buy' ? 'sell' : 'buy';
        function scoreButton(btn) {
          var txt = (btn.textContent || '').replace(/\\s+/g, ' ').trim();
          var dn = (btn.getAttribute('data-name') || '');
          var lower = txt.toLowerCase();
          var compact = lower.replace(/[^a-z0-9]/g, '');
          if (!txt && !dn) return { score: -1, reason: 'empty', text: txt, data_name: dn };
          if (/^(sell|buy)\\s*[\\d.,]+$/i.test(txt)) return { score: -1, reason: 'quote_price_button', text: txt, data_name: dn };
          if (/\\b(strong\\s+buy|strong\\s+sell|technical|seasonal|more)\\b/i.test(txt)) return { score: -1, reason: 'non_trading_widget_button', text: txt, data_name: dn };
          if (new RegExp('^' + oppositeSideWord + '\\\\b', 'i').test(txt)) return { score: -1, reason: 'opposite_side_submit_button', text: txt, data_name: dn };
          if (/\\b(market|limit|stop)\\b/i.test(txt) && new RegExp('\\\\b' + oppositeSideWord + '\\\\b', 'i').test(txt)) return { score: -1, reason: 'opposite_side_order_ticket_button', text: txt, data_name: dn };
          var rect = btn.getBoundingClientRect();
          var score = 0;
          if (dn === 'submit' || dn === 'submit-button') score += 40;
          if (lower.indexOf(sideWord) !== -1) score += 35;
          if (orderType && lower.indexOf(orderType) !== -1) score += 25;
          if (symbol && compact.indexOf(symbol) !== -1) score += 25;
          if (qty && lower.indexOf(qty) !== -1) score += 10;
          if (/\\b(place|create|submit|send|comprar|vender|crear|enviar)\\b/i.test(txt)) score += 20;
          if (/\\d/.test(txt) && /\\b(market|limit|stop)\\b/i.test(txt)) score += 15;
          score += Math.min(20, Math.max(0, rect.y || 0) / 80);
          return { score: score, reason: 'candidate', text: txt, data_name: dn, y: rect.y, disabled: !!btn.disabled };
        }
        var candidates = [];
        var best = null;
        for (var i = 0; i < btns.length; i++) {
          var b = btns[i];
          if (b.offsetParent === null) continue;
          var candidate = scoreButton(b);
          candidates.push(candidate);
          if (candidate.score < 30) continue;
          if (!best || candidate.score > best.meta.score) best = { button: b, meta: candidate };
        }
        candidates.sort(function(a, b) { return b.score - a.score; });
        if (!best) return { ok: false, error: 'submit button not found', candidates: candidates.slice(0, 8) };
        if (best.button.disabled) return { ok: false, error: 'submit button disabled', candidate: best.meta, candidates: candidates.slice(0, 8) };
        best.button.click();
        return {
          ok: true,
          clicked_text: best.meta.text.substring(0, 80),
          clicked_data_name: best.meta.data_name,
          score: best.meta.score,
          candidates: candidates.slice(0, 8)
        };
      } catch(e) { return { ok: false, error: e.message }; }
    })()
  `);
}

/**
 * Submit an order — market, limit, or stop — with take profit and
 * stop loss if provided.
 *
 * REQUIRES CONSENT. Throws if consent !== true.
 *
 * @param {object} opts
 * @param {boolean} opts.consent         MUST be exactly `true`
 * @param {string}  opts.side            "buy" or "sell"
 * @param {string}  opts.order_type      "market" | "limit" | "stop"
 * @param {number}  opts.quantity        position size in contracts/units
 * @param {number}  [opts.limit_price]   required for limit orders
 * @param {number}  [opts.stop_price]    required for stop orders
 * @param {number}  [opts.take_profit]   optional TP price
 * @param {number}  [opts.stop_loss]     optional SL price
 */
export async function submitOrder(opts = {}) {
  const {
    consent,
    side,
    order_type,
    quantity,
    limit_price,
    stop_price,
    take_profit,
    stop_loss,
  } = opts;

  requireConsent(consent, 'submit an order');

  // Validate inputs up front
  if (side !== 'buy' && side !== 'sell') {
    const err = new Error('side must be "buy" or "sell"');
    err.code = ErrorCodes.INVALID_INPUT;
    throw err;
  }
  if (!['market', 'limit', 'stop'].includes(order_type)) {
    const err = new Error('order_type must be "market", "limit", or "stop"');
    err.code = ErrorCodes.INVALID_INPUT;
    throw err;
  }
  const requestedQty = validateNumber(quantity, 'quantity');
  if (requestedQty <= 0) {
    const err = new Error('quantity must be positive');
    err.code = ErrorCodes.INVALID_INPUT;
    throw err;
  }
  if (order_type === 'limit' && limit_price == null) {
    const err = new Error('limit_price is required for limit orders');
    err.code = ErrorCodes.INVALID_INPUT;
    throw err;
  }
  if (order_type === 'stop' && stop_price == null) {
    const err = new Error('stop_price is required for stop orders');
    err.code = ErrorCodes.INVALID_INPUT;
    throw err;
  }

  const activeSymbol = await getActiveTradingSymbol();
  const quantityRule = normalizeQuantityForSymbol(requestedQty, activeSymbol);
  const qty = quantityRule.quantity;

  const mode = await detectTradingMode();
  if (mode.mode === 'not_connected') {
    const err = new Error(
      'Trading Panel is not connected. Open the Trading Panel and log into a broker (or select Paper Trading) before submitting orders.',
    );
    err.code = ErrorCodes.API_NOT_AVAILABLE;
    err.details = { detected_mode: mode };
    throw err;
  }

  const panelOpen = await ensureTradingPanelOpen();
  if (!panelOpen) {
    const err = new Error('Could not open the Trading Panel.');
    err.code = ErrorCodes.TIMEOUT_WAITING_FOR_ELEMENT;
    throw err;
  }

  const staleDialog = await closeOrderDialogIfOpen({ side });
  const opened = await openOrderDialog({ side });
  const selectedOrderType = await selectOrderType(order_type);

  // Fill the fields. Each setDialogField returns { ok, field? } or
  // { ok: false, error }. We collect errors and report them instead of
  // bailing on the first failure, because different brokers label
  // their fields differently.
  const fillResults = {};
  fillResults.quantity = await setDialogField('qty|quantity|cantidad', qty);

  if (order_type === 'limit') {
    fillResults.limit_price = await setDialogField('price|precio', validateNumber(limit_price, 'limit_price'));
  }
  if (order_type === 'stop') {
    fillResults.stop_price = await setDialogField('stop|trigger|disparo', validateNumber(stop_price, 'stop_price'));
  }
  if (take_profit != null) {
    fillResults.take_profit = await setDialogField('take profit|tp|ganancia', validateNumber(take_profit, 'take_profit'));
  }
  if (stop_loss != null) {
    fillResults.stop_loss = await setDialogField('stop loss|sl|p[eé]rdida', validateNumber(stop_loss, 'stop_loss'));
  }

  const requiredFills = ['quantity'];
  if (order_type === 'limit') requiredFills.push('limit_price');
  if (order_type === 'stop') requiredFills.push('stop_price');
  if (take_profit != null) requiredFills.push('take_profit');
  if (stop_loss != null) requiredFills.push('stop_loss');
  const failedFills = requiredFills.filter((key) => !fillResults[key]?.ok);
  if (failedFills.length) {
    const err = new Error(`Required order fields were not filled: ${failedFills.join(', ')}`);
    err.code = ErrorCodes.SELECTOR_NOT_FOUND;
    err.details = { fill_results: fillResults };
    throw err;
  }

  // Short grace period for the dialog to update the submit-button enabled state
  await sleep(300);

  const submitted = await submitOrderDialog({ side, orderType: order_type, quantity: qty, symbol: activeSymbol });
  if (!submitted?.ok) {
    const err = new Error(`Failed to submit order: ${submitted?.error || 'unknown'}`);
    err.code = ErrorCodes.ELEMENT_NOT_CLICKABLE;
    err.details = { fill_results: fillResults, submit: submitted };
    throw err;
  }

  return {
    success: true,
    mode: mode.mode,
    mode_source: mode.source,
    side,
    order_type,
    quantity: qty,
    requested_quantity: requestedQty,
    quantity_rule: quantityRule,
    limit_price: limit_price ?? null,
    stop_price: stop_price ?? null,
    take_profit: take_profit ?? null,
    stop_loss: stop_loss ?? null,
    stale_dialog: staleDialog,
    dialog_method: opened.method,
    selected_order_type: selectedOrderType,
    fill_results: fillResults,
    submit: submitted,
    note:
      mode.mode === 'paper'
        ? 'Paper trading order submitted. No real money at risk.'
        : mode.mode === 'broker'
          ? 'LIVE broker order submitted. Real money at risk.'
          : 'Order submitted. Trading mode could not be confirmed — verify in the Trading Panel.',
  };
}

/**
 * Cancel a pending order by its visible ID in the Orders tab of the
 * Trading Panel. REQUIRES CONSENT.
 */
export async function cancelOrder({ consent, order_id } = {}) {
  requireConsent(consent, 'cancel an order');
  if (!order_id) {
    const err = new Error('order_id is required');
    err.code = ErrorCodes.INVALID_INPUT;
    throw err;
  }
  const mode = await detectTradingMode();
  const escapedId = escapeJsString(order_id);
  const result = await evaluate(`
    (function() {
      try {
        var target = '${escapedId}';
        var rows = document.querySelectorAll('[data-name$=".orders-table"] tr, [data-name$=".orders-table"] [class*="row"], [data-name="orders"] [class*="row"], [class*="orders-list"] [class*="row"]');
        for (var i = 0; i < rows.length; i++) {
          var row = rows[i];
          if ((row.textContent || '').indexOf(target) === -1) continue;
          var cancelBtn = row.querySelector('[data-name="cancel-order-button"], [data-name="close-settings-cell-button"], [aria-label*="Cancel"], [aria-label*="Cancelar"], [title*="Cancel"], button[class*="cancel"]');
          if (cancelBtn) { cancelBtn.click(); return { ok: true, clicked: true }; }
        }
        return { ok: false, error: 'order row not found or no cancel button' };
      } catch(e) { return { ok: false, error: e.message }; }
    })()
  `);
  if (!result?.ok) {
    const err = new Error(`Failed to cancel order: ${result?.error || 'unknown'}`);
    err.code = ErrorCodes.ELEMENT_NOT_CLICKABLE;
    err.details = result;
    throw err;
  }
  return { success: true, mode: mode.mode, order_id, ...result };
}

/**
 * Close an open position at market. REQUIRES CONSENT.
 */
export async function closePosition({ consent, position_id } = {}) {
  requireConsent(consent, 'close a position');
  if (!position_id) {
    const err = new Error('position_id is required');
    err.code = ErrorCodes.INVALID_INPUT;
    throw err;
  }
  const mode = await detectTradingMode();
  const escapedId = escapeJsString(position_id);

  const tabClick = await evaluate(`
    (function() {
      try {
        var candidates = Array.prototype.slice.call(document.querySelectorAll('button, [role="tab"], [role="button"], div, span'));
        function clean(el) { return (el.textContent || '').replace(/\\s+/g, ' ').trim(); }
        var positionsTab = candidates.find(function(el) {
          if (el.offsetParent === null) return false;
          var txt = clean(el).toLowerCase();
          return /^positions(?:\\s+\\d+)?$/.test(txt) || /^positions\\b/.test(txt);
        });
        if (!positionsTab) return { ok: false, error: 'positions tab not found' };
        positionsTab.click();
        return { ok: true, text: clean(positionsTab).substring(0, 80) };
      } catch(e) { return { ok: false, error: e.message }; }
    })()
  `);
  await sleep(450);

  const result = await evaluate(`
    (function() {
      try {
        var target = '${escapedId}';
        var rows = Array.prototype.slice.call(document.querySelectorAll([
          '[data-name$=".positions-table"] tr',
          '[data-name$=".positions-table"] [class*="row"]',
          '[data-name="positions"] [class*="row"]',
          '[class*="positions-list"] [class*="row"]',
          '[class*="ka-tr"]:not([class*="thead"]):not([class*="emptyStateRow"])'
        ].join(',')));
        var closableRows = [];
        function rowText(row) { return (row.textContent || '').replace(/\\s+/g, ' ').trim(); }
        function findCloseButton(row) {
          var selectors = [
            '[data-name="close-position-button"]',
            '[data-name="close-settings-cell-button"]',
            '[aria-label*="Close"]',
            '[aria-label*="close"]',
            '[aria-label*="Fermer"]',
            '[aria-label*="Cerrar"]',
            '[title*="Close"]',
            '[title*="close"]',
            '[title*="Fermer"]',
            '[title*="Cerrar"]',
            'button[class*="close"]',
            '[role="button"][class*="close"]'
          ];
          for (var s = 0; s < selectors.length; s++) {
            var found = row.querySelector(selectors[s]);
            if (found) return found;
          }
          var buttons = Array.prototype.slice.call(row.querySelectorAll('button, [role="button"], [data-name], [aria-label], [title]'));
          return buttons.find(function(btn) {
            var txt = ((btn.textContent || '') + ' ' + (btn.getAttribute('aria-label') || '') + ' ' + (btn.getAttribute('title') || '') + ' ' + (btn.getAttribute('data-name') || '')).toLowerCase();
            return /close|fermer|cerrar|x|×|−/.test(txt);
          }) || null;
        }
        for (var i = 0; i < rows.length; i++) {
          var row = rows[i];
          if (row.offsetParent === null) continue;
          var text = rowText(row);
          if (!/\\b(long|short|buy|sell|btc|xau|eur|usd|usdt)\\b/i.test(text) && text.indexOf(target) === -1) continue;
          var closeBtn = findCloseButton(row);
          if (!closeBtn) continue;
          closableRows.push({ row: row, closeBtn: closeBtn, text: text });
          if (text.indexOf(target) !== -1) {
            closeBtn.click();
            return { ok: true, clicked: true, matched: 'position_id', row_text: text.substring(0, 300) };
          }
        }
        if (closableRows.length === 1) {
          closableRows[0].closeBtn.click();
          return { ok: true, clicked: true, matched: 'single_open_position_fallback', row_text: closableRows[0].text.substring(0, 300) };
        }
        return {
          ok: false,
          error: 'position row not found or no close button',
          tab_click: ${JSON.stringify(tabClick)},
          row_count: rows.length,
          visible_rows: rows.filter(function(r) { return r.offsetParent !== null; }).slice(0, 8).map(function(r) { return rowText(r).substring(0, 220); }),
          closable_rows: closableRows.map(function(r) { return r.text.substring(0, 220); })
        };
      } catch(e) { return { ok: false, error: e.message }; }
    })()
  `);
  if (!result?.ok) {
    const err = new Error(`Failed to close position: ${result?.error || 'unknown'}`);
    err.code = ErrorCodes.ELEMENT_NOT_CLICKABLE;
    err.details = result;
    throw err;
  }

  await sleep(400);

  const confirmed = await evaluate(`
    (function() {
      try {
        var dialog = document.querySelector('[data-name="trading-partial-closing-dialog"]')
          || document.querySelector('[class*="partial-closing"]')
          || document.querySelector('[class*="closing-dialog"]');
        if (!dialog) return { ok: true, confirmation_required: false };
        var submit = dialog.querySelector('[data-name="submit-button"]')
          || Array.prototype.slice.call(dialog.querySelectorAll('button')).find(function(btn) {
            return /close position|close|cerrar/i.test((btn.textContent || '').trim());
          });
        if (!submit) return { ok: false, error: 'close confirmation button not found' };
        if (submit.disabled) return { ok: false, error: 'close confirmation button disabled' };
        submit.click();
        return { ok: true, confirmation_required: true, confirmed: true };
      } catch(e) { return { ok: false, error: e.message }; }
    })()
  `);
  if (!confirmed?.ok) {
    const err = new Error(`Failed to confirm close position: ${confirmed?.error || 'unknown'}`);
    err.code = ErrorCodes.ELEMENT_NOT_CLICKABLE;
    err.details = confirmed;
    throw err;
  }

  return { success: true, mode: mode.mode, position_id, ...result, confirmation: confirmed };
}
