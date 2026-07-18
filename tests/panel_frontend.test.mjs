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

test("an unconfigured button leads with recognized hardware, not a missing result", () => {
  const panel = newPanel();
  panel._panel = {
    config: {
      labels: {
        live_event_label: "Poslední gesto",
        result_gesture_press: "Stisk rozpoznán",
        result_not_configured_button_detail:
          "Gesto dorazilo do Home Assistantu.",
      },
    },
  };
  const activity = {
    button: 1,
    gesture: "press",
    presses: 1,
    dispatch_status: "not_configured",
    result: null,
  };

  assert.equal(panel._liveResultLabel(activity), "Poslední gesto");
  assert.equal(panel._liveResult(activity), "Stisk rozpoznán");
  assert.equal(
    panel._liveExplanation(activity),
    "Gesto dorazilo do Home Assistantu.",
  );
  assert.deepEqual(panel._dispatchLabel(activity), [
    "unknown",
    "dispatch_not_configured_button",
  ]);
});

test("recognized multi-press copy keeps the physical gesture specific", () => {
  const panel = newPanel();
  panel._panel = {
    config: {
      labels: {
        result_gesture_double_press: "Dvojitý stisk rozpoznán",
      },
    },
  };

  assert.equal(
    panel._recognizedResult({ gesture: "press", presses: 2 }),
    "Dvojitý stisk rozpoznán",
  );
});

test("live setup opens the matching dual-button editor", () => {
  const panel = newPanel();
  const wheel = {
    variant: "dual_button",
    buttons: [
      { button: 1, configured: false, binding: null },
      { button: 2, configured: false, binding: null },
    ],
  };

  panel._configureFromLive(wheel, {
    button: 2,
    gesture: "press",
    dispatch_status: "not_configured",
  });

  assert.equal(panel._view, "buttons");
  assert.equal(panel._openButton, 2);
  assert.equal(panel._editingChannel, 2);
  assert.equal(panel._editingKind, "button");
});

test("dual button keeps the existing detail shell and adapted live test", () => {
  const panel = newPanel();

  assert.deepEqual(
    panel._viewsFor({ variant: "dual_button" }),
    ["buttons", "live", "diagnostics"],
  );
  assert.deepEqual(
    panel._viewsFor({ variant: "wheel" }),
    ["channels", "live", "diagnostics"],
  );
});

test("dual-button live activity names its safe button number", () => {
  const panel = newPanel();
  panel._panel = {
    config: {
      labels: {
        gesture_button_press_double: "Tlačítko {button} · dvojitý stisk",
      },
    },
  };

  assert.equal(
    panel._gestureLabel({
      button: 2,
      channel: null,
      gesture: "press",
      presses: 2,
    }),
    "Tlačítko 2 · dvojitý stisk",
  );
});

test("hold activity labels integration-observed duration honestly", () => {
  const panel = newPanel();
  panel._language = "cs";
  panel._panel = {
    config: {
      labels: {
        gesture_button_release: "Tlačítko {button} · uvolnění",
        gesture_observed_duration: "zachyceno {duration} s",
      },
    },
  };

  assert.equal(
    panel._gestureLabel({
      button: 1,
      gesture: "release",
      observed_duration_ms: 2250,
    }),
    "Tlačítko 1 · uvolnění · zachyceno 2,25 s",
  );
});

test("dual-button panel test sends button and no rotary address", async () => {
  const panel = newPanel();
  let message;
  panel._hass = {
    callWS: async (payload) => {
      message = payload;
      return { ok: true };
    },
  };

  await panel._testBinding(
    { key: "button-device", variant: "dual_button" },
    1,
    "press",
    { presses: 1 },
  );

  assert.deepEqual(message, {
    type: "ikea_bilresa/binding/test",
    wheel: "button-device",
    button: 1,
    gesture: "press",
    presses: 1,
  });
  assert.equal("channel" in message, false);
});

test("dual button selection changes only the open physical button", () => {
  const panel = newPanel();
  panel._openButton = 1;
  panel._editingChannel = 1;
  panel._editingKind = "button";
  panel._editorData = {};

  panel._openButtonAt(2);

  assert.equal(panel._openButton, 2);
  assert.equal(panel._editingChannel, null);
  assert.equal(panel._editingKind, null);
  assert.equal(panel._editorData, null);
});

test("dual-button editor starts without rotary or triple-press fields", () => {
  const panel = newPanel();
  const device = { variant: "dual_button" };
  const button = { button: 1, binding: null };

  panel._startEditor(device, button);

  assert.equal(panel._editingKind, "button");
  assert.equal(panel._editingChannel, 1);
  assert.deepEqual(panel._editorData, {
    click_action: "toggle",
    button_response: "multi_press",
    hold_action: "toggle",
    ramp_direction: "alternate",
  });
  assert.equal("mode" in panel._editorData, false);
  assert.equal("triple_press_target" in panel._editorData, false);
});

test("dual-button save sends only its safe display number", async () => {
  const panel = newPanel();
  const messages = [];
  const binding = {
    id: "binding-button-2",
    revision: "rev-2",
    data: {
      click_action: "toggle",
      click_target: "light.second",
      hold_action: "none",
      button_response: "multi_press",
      ramp_direction: "alternate",
    },
  };
  const device = {
    key: "button-device-a",
    variant: "dual_button",
    buttons: [{ button: 1 }, { button: 2, binding }],
    channels: [],
  };
  panel._snapshot = { wheels: [device] };
  panel._editorData = { ...binding.data };
  panel._editorBinding = binding;
  panel._editingChannel = 2;
  panel._editingKind = "button";
  panel._hass = {
    callWS: async (payload) => {
      messages.push(payload);
      if (payload.type === "ikea_bilresa/overview") {
        return panel._snapshot;
      }
      return { ok: true, binding };
    },
  };

  await panel._saveBinding(device, device.buttons[1]);

  assert.deepEqual(messages[0], {
    type: "ikea_bilresa/binding/save",
    wheel: "button-device-a",
    button: 2,
    data: binding.data,
    binding_id: "binding-button-2",
    expected_revision: "rev-2",
  });
  assert.equal("channel" in messages[0], false);
  assert.equal("endpoint" in messages[0], false);
});
