import assert from "node:assert/strict";
import test from "node:test";

class FakeHTMLElement {
  attachShadow() {
    this.shadowRoot = {
      activeElement: null,
      getElementById: () => null,
      replaceChildren: () => undefined,
    };
    return this.shadowRoot;
  }
}

const registry = new Map();
globalThis.HTMLElement = FakeHTMLElement;
globalThis.customElements = {
  define: (name, constructor) => registry.set(name, constructor),
  get: (name) => registry.get(name),
};

await import(
  "../custom_components/ikea_bilresa/frontend/ikea_bilresa_panel.js"
);

const Panel = registry.get("ikea-bilresa-panel");

const newPanel = () => {
  const panel = new Panel();
  panel._render = () => undefined;
  panel._open = "wheel-a";
  panel._view = "live";
  return panel;
};

test("live activity keeps only the selected wheel and stays bounded", async () => {
  let forward;
  let unsubscribed = 0;
  const panel = newPanel();
  panel._hass = {
    connection: {
      subscribeMessage: async (callback, message) => {
        assert.deepEqual(message, { type: "ikea_bilresa/activity/subscribe" });
        forward = callback;
        return () => {
          unsubscribed += 1;
        };
      },
    },
  };

  await panel._startActivity();
  assert.equal(typeof forward, "function");

  forward({ wheel: "wheel-b", channel: 1, gesture: "press" });
  assert.equal(panel._activities.length, 0);

  for (let index = 0; index < 10; index += 1) {
    forward({
      wheel: "wheel-a",
      channel: 1,
      gesture: "rotate",
      direction: "up",
      notches: index + 1,
      result: null,
      dispatched: null,
    });
  }

  assert.equal(panel._activities.length, 8);
  assert.equal(panel._activities[0].notches, 10);
  assert.equal(panel._activities[7].notches, 3);
  assert.match(panel._activities[0].received_at, /^\d{4}-\d{2}-\d{2}T/);

  panel._stopActivity();
  assert.equal(unsubscribed, 1);
});

test("leaving live mode cancels a subscription that resolves late", async () => {
  let resolveSubscription;
  let unsubscribed = 0;
  const panel = newPanel();
  panel._hass = {
    connection: {
      subscribeMessage: () =>
        new Promise((resolve) => {
          resolveSubscription = resolve;
        }),
    },
  };

  const starting = panel._startActivity();
  panel._stopActivity();
  resolveSubscription(() => {
    unsubscribed += 1;
  });
  await starting;

  assert.equal(unsubscribed, 1);
  assert.equal(panel._activityUnsub, null);
  assert.equal(panel._activityPending, false);
});

test("switching away from Live test unsubscribes immediately", async () => {
  let unsubscribed = 0;
  const panel = newPanel();
  panel._activityUnsub = () => {
    unsubscribed += 1;
  };

  panel._setView("diagnostics");

  assert.equal(unsubscribed, 1);
  assert.equal(panel._view, "diagnostics");
  assert.equal(panel._activityUnsub, null);
});

test("binding updates merge into the matching physical action", async () => {
  let forward;
  const panel = newPanel();
  panel._hass = {
    connection: {
      subscribeMessage: async (callback) => {
        forward = callback;
        return () => undefined;
      },
    },
  };
  await panel._startActivity();

  forward({
    wheel: "wheel-a",
    action_id: "action-1",
    channel: 1,
    gesture: "rotate",
    dispatch_status: "received",
  });
  forward({
    wheel: "wheel-a",
    action_id: "action-1",
    channel: 1,
    gesture: "rotate",
    dispatch_status: "accepted",
    dispatched: true,
    result: { kind: "brightness", before: 42, after: 58, unit: "%" },
  });

  assert.equal(panel._activities.length, 1);
  assert.equal(panel._activities[0].dispatch_status, "accepted");
  assert.deepEqual(panel._activities[0].result, {
    kind: "brightness",
    before: 42,
    after: 58,
    unit: "%",
  });
});

test("panel tests use the binding websocket command", async () => {
  let message;
  const panel = newPanel();
  panel._hass = {
    callWS: async (payload) => {
      message = payload;
      return { ok: true, action_id: "test-action" };
    },
  };

  await panel._testBinding(
    { key: "wheel-a" },
    2,
    "rotate",
    { direction: "up", notches: 1 },
  );

  assert.deepEqual(message, {
    type: "ikea_bilresa/binding/test",
    wheel: "wheel-a",
    channel: 2,
    gesture: "rotate",
    direction: "up",
    notches: 1,
  });
});

test("structured results lead with the human-readable outcome", () => {
  const panel = newPanel();
  panel._panel = {
    config: {
      labels: {
        result_kind_brightness: "Jas",
      },
    },
  };

  assert.equal(
    panel._formatResult({
      kind: "brightness",
      before: 42,
      after: 58,
      unit: "%",
    }),
    "Jas 42 → 58 %",
  );
});
