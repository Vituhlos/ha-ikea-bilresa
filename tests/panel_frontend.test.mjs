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
  panel._hass = { language: "cs" };
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

test("saving wheel settings sends the disabled channel and its revision", async () => {
  let message;
  const panel = newPanel();
  const wheel = {
    key: "wheel-a",
    channels: [
      { channel: 1, enabled: true },
      { channel: 2, enabled: true },
    ],
    settings: { subentry_id: "s1", revision: "rev-1", step: 2, acceleration: 0 },
  };
  panel._hass = {
    callWS: async (payload) => {
      if (payload.type === "ikea_bilresa/overview") return { wheels: [wheel] };
      message = payload;
      return { ok: true };
    },
  };

  panel._updateSettingsDraft(wheel, {
    channel_enabled: { 1: true, 2: false },
  });
  await panel._saveSettings(wheel);

  assert.equal(message.type, "ikea_bilresa/settings/save");
  assert.equal(message.wheel, "wheel-a");
  assert.deepEqual(message.channel_enabled, { 1: true, 2: false });
  assert.equal(message.expected_revision, "rev-1");
});

test("a settings conflict drops the draft instead of resending it", async () => {
  const panel = newPanel();
  const wheel = {
    key: "wheel-a",
    channels: [{ channel: 1, enabled: true }],
    settings: { subentry_id: "s1", revision: "stale", step: 2, acceleration: 0 },
  };
  panel._hass = {
    callWS: async (payload) => {
      if (payload.type === "ikea_bilresa/overview") return { wheels: [wheel] };
      return { ok: false, error: "conflict" };
    },
  };

  panel._updateSettingsDraft(wheel, { channel_enabled: { 1: false } });
  await panel._saveSettings(wheel);

  // Losing the draft is the point: the stored value is the truth now, and
  // silently keeping the rejected edit would let the next save clobber it.
  assert.equal(panel._settingsDraft, null);
  assert.equal(panel._settingsDraftKey, null);
});

test("a wheel without stored settings still offers the defaults", () => {
  const panel = newPanel();
  const state = panel._settingsStateFor({
    key: "wheel-b",
    channels: [{ channel: 1, enabled: true }, { channel: 2, enabled: false }],
  });

  assert.deepEqual(state.channel_enabled, { 1: true, 2: false });
  assert.equal(state.step, 2);
  assert.equal(state.acceleration, 0);
});

test("one wheel's unsaved draft never leaks onto another", () => {
  const panel = newPanel();
  const first = { key: "wheel-a", channels: [{ channel: 1, enabled: true }] };
  const second = { key: "wheel-b", channels: [{ channel: 1, enabled: true }] };

  panel._updateSettingsDraft(first, { channel_enabled: { 1: false } });

  assert.deepEqual(panel._settingsStateFor(second).channel_enabled, { 1: true });
});

test("a wheel saving for the first time omits the revision instead of sending null", async () => {
  // The deployed rc.12 sent expected_revision: null here, and the command's
  // schema rejected it — so the very first save of any wheel always failed.
  let message;
  const panel = newPanel();
  const wheel = {
    key: "wheel-a",
    channels: [{ channel: 1, enabled: true }],
    settings: { subentry_id: null, revision: null, step: 2, acceleration: 0 },
  };
  panel._hass = {
    callWS: async (payload) => {
      if (payload.type === "ikea_bilresa/overview") return { wheels: [wheel] };
      message = payload;
      return { ok: true };
    },
  };

  await panel._saveSettings(wheel);

  assert.ok(!("expected_revision" in message));
});

test("a new binding defaults to the linear step curve", () => {
  // Turning the perceptual curve on by default would break every lamp that
  // already corrects its own dimming curve, and nothing can tell which.
  const panel = newPanel();
  panel._startEditor({ variant: "wheel", key: "w" }, { channel: 1 });

  assert.equal(panel._editorData.step_curve, "linear");
});

test("the step curve is set-once, behind the rotation toggle", async () => {
  // PANEL_DESIGN.md: the disclosure keeps genuinely set-once options only.
  const { readFileSync } = await import("node:fs");
  const source = readFileSync(
    new URL(
      "../custom_components/ikea_bilresa/frontend/ikea_bilresa_panel.js",
      import.meta.url,
    ),
    "utf8",
  );
  const toggle = source.indexOf('this._t("rotation_more")');
  const extras = source.indexOf("if (this._advancedOpen) {", toggle);
  const shortPress = source.indexOf('this._formSection(sections, "short_press")');

  // Behind Rotation's own toggle, not among the fields shown every time.
  assert.ok(toggle > 0 && extras > toggle && extras < shortPress);
  assert.ok(source.slice(extras, shortPress).includes('"step_curve"'));
  assert.ok(!source.slice(source.indexOf('this._formSection(sections, "rotation")'), toggle).includes('"step_curve"'));
});

test("a response that rules gestures out clears them", () => {
  const panel = newPanel();
  panel._loadEditor(false, {
    target: "light.a",
    double_press_target: "light.b",
    hold_action: "toggle",
  });

  panel._chooseResponse("fast");
  assert.equal(panel._editorChoices.double_press, "none");
  assert.equal("double_press_target" in panel._editorData, false);
  assert.equal(panel._editorData.hold_action, "toggle");

  panel._chooseResponse("instant");
  assert.equal(panel._editorData.hold_action, "none");
  assert.equal(panel._editorData.button_response, "instant");
});

test("an unavailable target is named plainly; only a missing one is a fault", () => {
  const panel = newPanel();
  panel._panel = {
    config: {
      labels: {
        target_unavailable: "{target} — unavailable",
        target_missing: "{target} — no longer exists",
      },
    },
  };

  assert.equal(
    panel._targetText({ target_label: "Bulb", target_state: "ok" }),
    "Bulb",
  );
  assert.equal(
    panel._targetText({ target_label: "Bulb", target_state: "unavailable" }),
    "Bulb — unavailable",
  );
  assert.equal(
    panel._targetText({
      target_label: "light.gone",
      target_state: "missing",
      target_missing: true,
    }),
    "light.gone — no longer exists",
  );
  assert.equal(panel._targetText({ target_label: null }), null);
});

test("a backend from before contract 6 still marks its missing targets", () => {
  const panel = newPanel();
  panel._panel = {
    config: { labels: { target_missing: "{target} — no longer exists" } },
  };

  // No target_state at all: the old boolean is all the panel has to go on.
  assert.equal(
    panel._targetText({ target_label: "Bulb", target_missing: true }),
    "Bulb — no longer exists",
  );
  assert.equal(
    panel._targetText({ target_label: "Bulb", target_missing: false }),
    "Bulb",
  );
});

test("the overview banner counts missing targets, never unavailable ones", async () => {
  const { readFileSync } = await import("node:fs");
  const source = readFileSync(
    new URL(
      "../custom_components/ikea_bilresa/frontend/ikea_bilresa_panel.js",
      import.meta.url,
    ),
    "utf8",
  );
  const banner = source.slice(
    source.indexOf("const missing = this._snapshot.wheels.filter"),
    source.indexOf("wrap.appendChild(this._overviewHead())"),
  );

  assert.ok(banner.includes('targetState(control) === "missing"'));
  assert.ok(!banner.includes(".target_missing"));
});

test("a control names the target its state belongs to, not its summary label", () => {
  const panel = newPanel();
  panel._panel = {
    config: {
      labels: {
        target_unavailable: "{target} — unavailable",
        target_missing: "{target} — no longer exists",
      },
    },
  };
  const button = {
    target_label: "2 targets",
    target_state: "missing",
    target_missing: true,
    actions: [
      { target_label: "Hall", target_state: "unavailable" },
      { target_label: "light.gone", target_state: "missing", target_missing: true },
    ],
  };

  assert.equal(panel._controlTargetText(button), "light.gone — no longer exists");
  assert.equal(
    panel._controlTargetText({ target_label: "2 targets", target_state: "ok" }),
    "2 targets",
  );
  // Nothing to point at: fall back to the control's own label.
  assert.equal(
    panel._controlTargetText({ target_label: "Bulb", target_state: "unavailable" }),
    "Bulb — unavailable",
  );
});

const ledgerPanel = () => {
  const panel = newPanel();
  panel._panel = {
    config: {
      labels: {
        action_none: "No action",
        ledger_then_release: "{hold}; on release: {release}",
      },
    },
  };
  return panel;
};
test("gestures with no action get no row", () => {
  const panel = ledgerPanel();
  const rows = panel._ledgerRows(
    [
      { gesture: "rotation", gesture_label: "Rotate", action_label: "Brightness", target_label: "Bulb" },
      { gesture: "double_press", gesture_label: "Double press", action_label: "No action", target_label: null },
      { gesture: "hold", gesture_label: "Hold", action_label: "No action", target_label: null },
      { gesture: "release", gesture_label: "Release", action_label: "No action", target_label: null },
    ],
  );

  assert.deepEqual(rows.map((row) => row.label), ["Rotate"]);
  assert.equal(rows[0].action, "Brightness");
  assert.equal(rows[0].target, "Bulb");
});

test("a hold row mentions the release only when the release does something", () => {
  const panel = ledgerPanel();
  const hold = { gesture: "hold", gesture_label: "Hold", action_label: "Ramp", target_label: "Bulb" };

  const quiet = panel._ledgerRows(
    [hold, { gesture: "release", gesture_label: "Release", action_label: "No action", target_label: null }],
  );
  assert.equal(quiet[0].action, "Ramp");
  assert.equal(quiet[0].target, "Bulb");

  const stopping = panel._ledgerRows(
    [hold, { gesture: "release", gesture_label: "Release", action_label: "Stop ramp", target_label: null }],
  );
  assert.equal(stopping[0].action, "Ramp; on release: Stop ramp");
  assert.equal(stopping[0].target, "Bulb");
  assert.equal(stopping.length, 1);
});

test("a ledger row warns for a missing target, not an unavailable one", () => {
  const panel = ledgerPanel();
  const rows = panel._ledgerRows(
    [
      { gesture: "rotation", gesture_label: "Rotate", action_label: "Brightness", target_label: "Bulb", target_state: "unavailable" },
      { gesture: "short_press", gesture_label: "Press", action_label: "Toggle", target_label: "light.gone", target_state: "missing" },
    ],
  );

  assert.deepEqual(rows.map((row) => row.warning), [false, true]);
});

test("scenes keep an order that can be changed", () => {
  const panel = newPanel();
  panel._editorData = { scenes: ["scene.a", "scene.b", "scene.c"] };
  panel._editorErrors = { scenes: "invalid" };

  panel._sceneMove(2, -1);
  assert.deepEqual(panel._editorData.scenes, ["scene.a", "scene.c", "scene.b"]);
  assert.deepEqual(panel._editorErrors, {});

  // Past either end is a no-op, not a wrap-around.
  panel._sceneMove(0, -1);
  panel._sceneMove(2, 1);
  assert.deepEqual(panel._editorData.scenes, ["scene.a", "scene.c", "scene.b"]);

  panel._sceneRemove(0);
  assert.deepEqual(panel._editorData.scenes, ["scene.c", "scene.b"]);

  panel._sceneAdd("scene.d");
  panel._sceneAdd("scene.c");
  panel._sceneAdd("");
  assert.deepEqual(panel._editorData.scenes, ["scene.c", "scene.b", "scene.d"]);
});

test("the editor shows scene cycling as the short press it replaces", () => {
  const panel = newPanel();
  const stored = {
    click_action: "off",
    scenes: ["scene.a"],
    double_press_target: "light.a",
  };
  panel._loadEditor(false, stored);

  assert.deepEqual(panel._editorChoices, {
    click_action: "scenes",
    double_press: "toggle",
    triple_press: "none",
  });
  assert.equal(panel._editorData.click_action, "off");
  // The draft keeps its own copy: editing it must not touch the snapshot.
  panel._editorData.scenes.push("scene.b");
  assert.deepEqual(stored.scenes, ["scene.a"]);

  panel._loadEditor(true, { click_action: "on" });
  assert.equal(panel._editorChoices.click_action, "on");
  assert.equal(panel._editorData.scenes, undefined);
});

test("leaving a press choice drops what only that choice used", () => {
  const panel = newPanel();
  panel._loadEditor(false, {
    click_action: "off",
    scenes: ["scene.a", "scene.b"],
    double_press_target: "light.a",
  });
  panel._editorErrors = { scenes: "x", double_press_target: "y" };

  panel._chooseGesture("click_action", "toggle");
  assert.equal(panel._editorData.click_action, "toggle");
  assert.deepEqual(panel._editorData.scenes, []);

  panel._chooseGesture("double_press", "none");
  assert.equal("double_press_target" in panel._editorData, false);
  assert.deepEqual(panel._editorErrors, {});

  // Choosing scenes again keeps the stored action; the runtime ignores it.
  panel._chooseGesture("click_action", "scenes");
  assert.equal(panel._editorChoices.click_action, "scenes");
  assert.equal(panel._editorData.click_action, "toggle");
});

test("an empty scene cycle or toggle is caught before saving", async () => {
  const panel = newPanel();
  let sent = 0;
  panel._hass = { callWS: async () => { sent += 1; return { ok: true }; } };
  panel._loadEditor(false, { target: "light.a" });
  panel._chooseGesture("click_action", "scenes");
  panel._chooseGesture("triple_press", "toggle");

  await panel._saveBinding({ key: "wheel-a", variant: "wheel" }, { channel: 1 });

  assert.equal(sent, 0);
  assert.deepEqual(panel._editorErrors, {
    scenes: "scenes_required",
    triple_press_target: "target_required",
  });
});

test("discarding an untouched editor closes it at once", () => {
  const panel = newPanel();
  panel._editingChannel = 1;
  panel._loadEditor(false, { target: "light.a" });

  panel._discard();

  assert.equal(panel._editorData, null);
  assert.equal(panel._discardArmed, null);
});

test("discarding changes takes a second, deliberate press", () => {
  const panel = newPanel();
  panel._editingChannel = 1;
  panel._loadEditor(false, { target: "light.a" });
  panel._chooseGesture("double_press", "toggle");

  panel._discard();
  assert.notEqual(panel._discardArmed, null);
  // A double click is not a decision.
  panel._discard();
  assert.notEqual(panel._editorData, null);

  panel._discardArmed.at -= 1000;
  panel._discard();
  assert.equal(panel._editorData, null);
  assert.equal(panel._discardTimer, null);
});

test("opening another channel over unsaved changes arms Discard first", () => {
  const panel = newPanel();
  const wheel = { key: "wheel-a", variant: "wheel", channels: [] };
  panel._editingChannel = 1;
  panel._loadEditor(false, { target: "light.a", step: 3 });
  panel._editorData.step = 7;

  panel._requestEditor(wheel, { channel: 2 });
  assert.equal(panel._editingChannel, 1);
  assert.equal(typeof panel._discardArmed.then, "function");

  panel._discardArmed.at -= 1000;
  panel._discard();
  assert.equal(panel._editingChannel, 2);
  panel._disarmDiscard();
});

test("a short-press target nothing shows is dropped, not left to be reported", () => {
  const panel = newPanel();

  // A stored scene cycle with a target behind it: the draft is shown without
  // it, and cleaning it up is not an edit.
  panel._loadEditor(false, {
    click_action: "toggle",
    click_target: "light.old",
    scenes: ["scene.a"],
  });
  assert.equal("click_target" in panel._editorData, false);
  assert.deepEqual(panel._editorData.scenes, ["scene.a"]);
  assert.equal(panel._editorDirty(), false);

  // Choosing scene cycling or "no action" hides the picker, so the target goes.
  for (const choice of ["scenes", "none"]) {
    panel._loadEditor(false, { click_action: "toggle", click_target: "light.old" });
    assert.equal(panel._editorData.click_target, "light.old");
    panel._chooseGesture("click_action", choice);
    assert.equal("click_target" in panel._editorData, false, choice);
  }
  assert.equal(panel._editorData.click_action, "none");

  // A choice that shows the picker keeps its target.
  panel._loadEditor(false, { click_action: "on", click_target: "light.keep" });
  assert.equal(panel._editorData.click_target, "light.keep");
  panel._chooseGesture("click_action", "off");
  assert.equal(panel._editorData.click_target, "light.keep");
});

test("a rejected save that marks a hidden rotation field opens the disclosure", async () => {
  const panel = newPanel();
  const wheel = { key: "wheel-a", variant: "wheel" };
  const reject = (fields) => ({
    callWS: async () => ({ ok: false, error: "validation", fields }),
  });
  panel._loadEditor(false, { target: "light.a" });
  assert.equal(panel._advancedOpen, false);

  // An error on a field that is always shown leaves the disclosure alone.
  panel._hass = reject({ target: "target_required" });
  await panel._saveBinding(wheel, { channel: 1 });
  assert.equal(panel._advancedOpen, false);

  // One inside "More rotation settings" opens it, or the message points at
  // a field the user cannot see.
  panel._hass = reject({ max_brightness: "invalid_value" });
  await panel._saveBinding(wheel, { channel: 1 });
  assert.equal(panel._advancedOpen, true);
  assert.deepEqual(panel._editorErrors, { max_brightness: "invalid_value" });
});

test("each Discard button has its own stable id, so focus survives a render", async () => {
  const { readFileSync } = await import("node:fs");
  const node = () => ({
    className: "",
    textContent: "",
    dataset: {},
    children: [],
    attributes: {},
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
    appendChild(child) {
      this.children.push(child);
      return child;
    },
    addEventListener() {},
  });
  const previous = globalThis.document;
  globalThis.document = { createElement: node };
  try {
    const panel = newPanel();
    const header = panel._discardButton(2, "header");
    const form = panel._discardButton(2, "form");
    const other = panel._discardButton(3, "header");

    assert.equal(header.id, "discard-wheel-a-2-header");
    assert.equal(new Set([header.id, form.id, other.id]).size, 3);
    // The same button gets the same id after a render, which is what lets
    // _render() hand the keyboard focus back to it.
    assert.equal(panel._discardButton(2, "header").id, header.id);
  } finally {
    globalThis.document = previous;
  }

  const source = readFileSync(
    new URL(
      "../custom_components/ikea_bilresa/frontend/ikea_bilresa_panel.js",
      import.meta.url,
    ),
    "utf8",
  );
  assert.ok(source.includes('this._discardButton(number, "header")'));
  assert.ok(source.includes('this._discardButton(this._editingChannel, "form")'));
});

test("the community tool is one plain external link, and it carries no data", () => {
  const node = () => ({
    className: "",
    textContent: "",
    dataset: {},
    children: [],
    attributes: {},
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
    appendChild(child) {
      this.children.push(child);
      return child;
    },
    addEventListener() {},
  });
  const previous = globalThis.document;
  globalThis.document = { createElement: node, createElementNS: () => node() };
  try {
    const panel = newPanel();
    panel._panel = {
      config: {
        labels: {
          community_tool_link: "Design labels for your switches",
          community_tool_note: "Community tool by Liquidmasl",
          community_tool_new_window: "opens in a new window",
        },
      },
    };
    const link = panel._communityLink();
    const copy = link.children.find((child) => child.className === "resource-copy");
    const part = (name) => copy.children.find((child) => child.className === name);

    assert.equal(link.href, "https://bilresa.marcel1.com/");
    assert.equal(link.target, "_blank");
    assert.equal(link.rel, "noopener noreferrer");
    // Nothing about the installation can travel with the address.
    const url = new URL(link.href);
    assert.equal(url.search, "");
    assert.equal(url.hash, "");
    assert.equal(url.username, "");

    assert.equal(part("resource-title").textContent, "Design labels for your switches");
    // It says whose tool it is.
    // It says whose tool it is and that it opens in a new window, in words
    // that are part of the link, so a screen reader reads them even where
    // a narrow pane does not draw the second part.
    const note = part("resource-note");
    const byText = note.children.find((child) => child.className === "resource-by");
    const newText = note.children.find((child) => child.className === "resource-new");
    assert.equal(byText.textContent, "Community tool by Liquidmasl");
    assert.equal(newText.textContent, " · opens in a new window");
    // Both icons, the tinted round one and the arrow out, are decoration.
    const icons = link.children.filter((child) => child.attributes["aria-hidden"] === "true");
    assert.equal(icons.length, 2);
  } finally {
    globalThis.document = previous;
  }
});

test("without Home Assistant's components the panel builds no ha-selector", () => {
  const panel = newPanel();

  // The registry here holds only the panel itself: this is the fallback path,
  // and it must be a clean "not available", never an exception.
  assert.equal(
    panel._haSelector({
      id: "x",
      selector: { boolean: {} },
      value: true,
      label: "x",
      onChange: () => undefined,
    }),
    null,
  );
});

test("selectors describe the same ranges and domains the server validates", () => {
  const panel = newPanel();
  panel._panel = {
    config: {
      schema: {
        binding_numbers: { step: { min: 1, max: 25, step: 1, unit: "%" } },
        settings_numbers: { step: { min: 1, max: 25, step: 1, unit: null } },
        mode_domains: { volume: ["media_player"] },
        press_target_domains: ["light", "switch", "script", "scene"],
        ramp_target_domains: ["light"],
      },
    },
  };

  assert.deepEqual(
    panel._numberSelector(panel._numberRange("binding_numbers", "step")),
    { number: { min: 1, max: 25, step: 1, mode: "slider", unit_of_measurement: "%" } },
  );
  // No unit: the key is left out rather than sent as null.
  assert.deepEqual(
    panel._numberSelector(panel._numberRange("settings_numbers", "step")),
    { number: { min: 1, max: 25, step: 1, mode: "slider" } },
  );
  assert.deepEqual(panel._entitySelector(["scene"], ["scene.a"]), {
    entity: { domain: ["scene"], exclude_entities: ["scene.a"] },
  });
  assert.deepEqual(panel._entitySelector(["light"]), {
    entity: { domain: ["light"] },
  });
  // A field the server's schema does not list falls back to the built-in copy.
  assert.equal(panel._numberRange("binding_numbers", "transition").unit, "s");
});

test("a panel config without a schema uses the built-in copy", () => {
  const panel = newPanel();
  panel._panel = { config: { labels: {} } };

  assert.deepEqual(panel._schema().mode_domains.number, ["number", "input_number"]);
  assert.equal(panel._numberRange("binding_numbers", "step").max, 25);
});

const settingsWheel = () => ({
  key: "wheel-a",
  channels: [
    { channel: 1, enabled: true },
    { channel: 2, enabled: true },
  ],
  settings: { revision: "r1", step: 2, acceleration: 0 },
});

test("a channel switch saves the switches and leaves a dial draft alone", async () => {
  const panel = newPanel();
  const wheel = settingsWheel();
  const calls = [];
  panel._snapshot = { wheels: [wheel] };
  panel._hass = {
    callWS: async (message) => {
      calls.push(message);
      return message.type.endsWith("overview") ? panel._snapshot : { ok: true };
    },
  };
  panel._updateSettingsDraft(wheel, { step: 9 });
  panel._updateSettingsDraft(wheel, { channel_enabled: { 1: true, 2: false } });

  await panel._saveSettings(wheel, "channels");

  const sent = calls[0];
  assert.deepEqual(sent.channel_enabled, { 1: true, 2: false });
  // The dial's unsaved 9 is not smuggled in with the switch.
  assert.equal(sent.step, 2);
  assert.equal(panel._settingsStateFor(wheel).step, 9);
});

test("saving the dial does not carry an unsaved channel switch", async () => {
  const panel = newPanel();
  const wheel = settingsWheel();
  const calls = [];
  panel._snapshot = { wheels: [wheel] };
  panel._hass = {
    callWS: async (message) => {
      calls.push(message);
      return message.type.endsWith("overview") ? panel._snapshot : { ok: true };
    },
  };
  panel._updateSettingsDraft(wheel, {
    step: 5,
    acceleration: 20,
    channel_enabled: { 1: false, 2: true },
  });

  await panel._saveSettings(wheel, "dial");

  assert.equal(calls[0].step, 5);
  assert.equal(calls[0].acceleration, 20);
  assert.deepEqual(calls[0].channel_enabled, { 1: true, 2: true });
  assert.equal(calls[0].expected_revision, "r1");
});

test("the editor replaces the ledger instead of sitting under it", async () => {
  const { readFileSync } = await import("node:fs");
  const source = readFileSync(
    new URL(
      "../custom_components/ikea_bilresa/frontend/ikea_bilresa_panel.js",
      import.meta.url,
    ),
    "utf8",
  );
  const detail = source.slice(
    source.indexOf("  _channelDetail(wheel, channel) {"),
    source.indexOf("  _isNoAction(action) {"),
  );

  assert.ok(detail.includes("this._editingChannel !== number &&"));
  // No native multi-select anywhere: it cannot express the order of scenes.
  assert.ok(!source.includes("select.multiple"));
});

test("a Home Assistant selector is handed its new value back", () => {
  // ha-selector draws the value it was given. Number fields change without a
  // re-render, so without this the slider moved and the number box did not.
  const panel = newPanel();
  const listeners = {};
  class FakeSelector {
    addEventListener(name, handler) {
      listeners[name] = handler;
    }
  }
  registry.set("ha-selector", FakeSelector);
  const previous = globalThis.document;
  globalThis.document = { createElement: () => new FakeSelector() };
  try {
    const seen = [];
    const node = panel._haSelector({
      id: "x",
      selector: { number: { min: 1, max: 25 } },
      value: 2,
      label: "Step",
      onChange: (value) => seen.push(value),
    });
    assert.equal(node.value, 2);

    listeners["value-changed"]({
      stopPropagation: () => undefined,
      detail: { value: 7 },
    });

    assert.equal(node.value, 7);
    assert.deepEqual(seen, [7]);
  } finally {
    registry.delete("ha-selector");
    globalThis.document = previous;
  }
});

test("the panel speaks its user's language, not the instance's", () => {
  const panel = newPanel();
  panel._panel = {
    config: {
      language: "cs",
      labels: { add_binding: "Přidat propojení" },
      labels_by_language: {
        cs: { add_binding: "Přidat propojení" },
        en: { add_binding: "Add a control binding" },
      },
    },
  };

  // A user who chose English in their profile on a Czech instance.
  panel._hass = { language: "en" };
  assert.equal(panel._lang(), "en");
  assert.equal(panel._t("add_binding"), "Add a control binding");

  // A regional tag falls back to its base language.
  panel._hass = { language: "en-GB" };
  assert.equal(panel._t("add_binding"), "Add a control binding");

  // A language the panel does not speak falls back to the instance's.
  panel._hass = { language: "de" };
  assert.equal(panel._lang(), "cs");
  assert.equal(panel._t("add_binding"), "Přidat propojení");
});

test("a backend from before 0.6.1 still works: one label set", () => {
  const panel = newPanel();
  panel._panel = { config: { language: "cs", labels: { add_binding: "Přidat propojení" } } };
  panel._hass = { language: "en" };

  assert.equal(panel._t("add_binding"), "Přidat propojení");
});

test("the snapshot is requested in the user's language", async () => {
  const panel = newPanel();
  const calls = [];
  panel._panel = {
    config: { language: "cs", labels_by_language: { cs: {}, en: {} } },
  };
  panel._hass = {
    language: "en",
    callWS: async (message) => {
      calls.push(message);
      return { wheels: [], matter_connected: true };
    },
    connection: {
      subscribeMessage: async (_callback, message) => {
        calls.push(message);
        return () => undefined;
      },
    },
  };

  await panel._connect();

  assert.deepEqual(
    calls.map((message) => message.language),
    ["en", "en"],
  );
});

test("a connect overtaken by a language switch drops its answer and subscription", async () => {
  const panel = newPanel();
  panel._panel = { config: { language: "cs", labels_by_language: { cs: {}, en: {} } } };
  const answers = [];
  const subscriptions = [];
  const unsubscribed = [];
  panel._hass = {
    language: "cs",
    callWS: (message) =>
      new Promise((resolve) => answers.push(() => resolve({ wheels: [], lang: message.language }))),
    connection: {
      subscribeMessage: (_callback, message) =>
        new Promise((resolve) =>
          subscriptions.push(() => resolve(() => unsubscribed.push(message.language))),
        ),
    },
  };
  const tick = () => new Promise((resolve) => setTimeout(resolve, 0));

  // Case 1: the Czech snapshot is still on its way when the user switches.
  const first = panel._connect();
  panel._hass = { ...panel._hass, language: "en" };
  const second = panel._connect();
  answers[1]();
  await tick();
  subscriptions[0]();
  await second;
  answers[0](); // the stale Czech answer arrives late
  await first;
  assert.equal(panel._snapshot.lang, "en");

  // Case 2: a stale connect already got its snapshot and is subscribing.
  panel._hass = { ...panel._hass, language: "cs" };
  const third = panel._connect();
  answers[2]();
  await tick();
  panel._hass = { ...panel._hass, language: "en" };
  const fourth = panel._connect();
  answers[3]();
  await tick();
  subscriptions[2]();
  await fourth;
  subscriptions[1](); // the stale Czech subscription completes late
  await third;

  assert.equal(panel._snapshot.lang, "en");
  assert.deepEqual(unsubscribed, ["cs"]);
});

test("a language switch with the Live test open restarts the live feed", async () => {
  const panel = newPanel();
  let started = 0;
  panel._startActivity = () => {
    started += 1;
  };
  panel._connect = async () => {
    panel._snapshot = { wheels: [] };
  };
  panel._view = "live";
  panel._open = "wheel-a";

  await panel._retry();

  assert.equal(started, 1);
});

const labelsOf = (options) => options.map((option) => option.value);

test("the choices follow the kind of target: a scene is only run", () => {
  const panel = newPanel();

  assert.deepEqual(labelsOf(panel._actionOptions("light.a")), [
    "toggle",
    "on",
    "off",
    "run",
    "none",
  ]);
  assert.deepEqual(labelsOf(panel._actionOptions("script.a")), [
    "on",
    "off",
    "toggle",
    "run",
    "none",
  ]);
  assert.deepEqual(labelsOf(panel._actionOptions("scene.a")), ["on", "run", "none"]);
  assert.deepEqual(
    labelsOf(panel._actionOptions("light.a", { scenes: true, none: false })),
    ["toggle", "on", "off", "run", "scenes"],
  );
  // No target chosen yet: the words of an ordinary switchable entity.
  assert.deepEqual(labelsOf(panel._actionOptions(undefined)), [
    "toggle",
    "on",
    "off",
    "run",
    "none",
  ]);
});

test("the words for a script and a scene are their own", () => {
  // The panel's strings come from the server, so a test sees the keys.
  const panel = newPanel();
  const words = (target) =>
    panel._actionOptions(target).map((option) => option.label);

  assert.deepEqual(words("script.a"), [
    "click_script_on",
    "click_script_off",
    "click_script_toggle",
    "click_run",
    "click_none",
  ]);
  assert.deepEqual(words("scene.a"), ["click_scene_on", "click_run", "click_none"]);
  assert.deepEqual(words("light.a"), [
    "click_toggle",
    "click_on",
    "click_off",
    "click_run",
    "click_none",
  ]);
});

test("only running a script, or toggling it, gets a note about variables", () => {
  const panel = newPanel();

  assert.equal(panel._actionHelp("script.a", "on"), "script_run_help");
  assert.equal(panel._actionHelp("script.a", "toggle"), "script_toggle_help");
  assert.equal(panel._actionHelp("script.a", "off"), undefined);
  assert.equal(panel._actionHelp("scene.a", "on"), undefined);
  assert.equal(panel._actionHelp("light.a", "toggle"), undefined);
});

test("a stored double press keeps its action, and an old one toggled", () => {
  const panel = newPanel();
  panel._loadEditor(false, {
    double_press_target: "script.a",
    double_press_action: "off",
    triple_press_target: "script.b",
    hold_action: "toggle",
    hold_target: "scene.c",
  });

  assert.equal(panel._editorChoices.double_press, "off");
  // No stored action: what it always did.
  assert.equal(panel._editorChoices.triple_press, "toggle");
  assert.equal(panel._editorData.triple_press_action, "toggle");
  // A scene has no toggle; it reads, and is saved, as run.
  assert.equal(panel._editorData.hold_target_action, "on");
});

test("a double press without a target is off, whatever was stored", () => {
  const panel = newPanel();
  panel._loadEditor(false, { double_press_action: "off" });

  assert.equal(panel._editorChoices.double_press, "none");
});

test("choosing an action stores it beside the target, and none drops both", () => {
  const panel = newPanel();
  panel._loadEditor(false, { double_press_target: "light.a" });

  panel._chooseGesture("double_press", "off");
  assert.equal(panel._editorData.double_press_action, "off");
  assert.equal(panel._editorData.double_press_target, "light.a");

  panel._chooseGesture("double_press", "none");
  assert.equal("double_press_action" in panel._editorData, false);
  assert.equal("double_press_target" in panel._editorData, false);
});

test("a script or a scene as a new target is run, anything else toggled", () => {
  const panel = newPanel();
  panel._loadEditor(false, { double_press_target: "light.a" });

  panel._retarget("double_press", "light.a", "script.go");
  assert.equal(panel._editorChoices.double_press, "on");
  assert.equal(panel._editorData.double_press_action, "on");

  // Another script keeps what the person chose.
  panel._chooseGesture("double_press", "off");
  panel._retarget("double_press", "script.go", "script.other");
  assert.equal(panel._editorChoices.double_press, "off");

  panel._retarget("double_press", "script.other", "switch.fan");
  assert.equal(panel._editorChoices.double_press, "toggle");
  assert.equal(panel._editorData.double_press_action, "toggle");

  // Clearing a target changes nothing.
  panel._retarget("double_press", "switch.fan", undefined);
  assert.equal(panel._editorChoices.double_press, "toggle");
});

test("the short press and the hold follow their target the same way", () => {
  const panel = newPanel();
  panel._loadEditor(true, { click_target: "light.a", hold_action: "toggle" });

  panel._retarget("click", "light.a", "scene.evening");
  assert.equal(panel._editorChoices.click_action, "on");
  assert.equal(panel._editorData.click_action, "on");

  panel._retarget("hold", undefined, "script.go");
  assert.equal(panel._editorData.hold_target_action, "on");
});

test("scene cycling is left alone when its target changes", () => {
  const panel = newPanel();
  panel._loadEditor(false, { scenes: ["scene.a"] });

  panel._retarget("click", undefined, "script.go");

  assert.equal(panel._editorChoices.click_action, "scenes");
});

test("an enabled double press without a target is caught before saving", async () => {
  const panel = newPanel();
  let sent = 0;
  panel._hass = { callWS: async () => { sent += 1; return { ok: true }; } };
  panel._loadEditor(false, { target: "light.a" });
  panel._chooseGesture("double_press", "on");

  await panel._saveBinding({ key: "wheel-a", variant: "wheel" }, { channel: 1 });

  assert.equal(sent, 0);
  assert.deepEqual(panel._editorErrors, { double_press_target: "target_required" });
});

// -- verbs by kind of target -------------------------------------------------

const withVerbs = (panel, verbs, labels = {}) => {
  panel._panel = {
    config: {
      labels,
      schema: { gesture_verbs: verbs, press_target_domains: Object.keys(verbs) },
    },
  };
  return panel;
};

test("the actions on offer are the verbs of the chosen kind of target", () => {
  const panel = withVerbs(
    newPanel(),
    {
      light: ["toggle", "on", "off"],
      media_player: ["toggle", "play_pause", "mute_toggle"],
      lock: ["lock"],
    },
    {
      click_toggle: "Toggle target",
      click_play_pause: "Play / pause",
      click_mute_toggle: "Mute / unmute",
      click_lock: "Lock",
      click_run: "Run actions",
      click_none: "No action",
    },
  );

  assert.deepEqual(
    panel._actionOptions("media_player.tv").map((o) => [o.value, o.label]),
    [
      ["toggle", "Toggle target"],
      ["play_pause", "Play / pause"],
      ["mute_toggle", "Mute / unmute"],
      ["run", "Run actions"],
      ["none", "No action"],
    ],
  );
  assert.deepEqual(
    panel._actionOptions("lock.door", { none: false, run: false }).map((o) => o.value),
    ["lock"],
  );
});

test("a backend that sends no verbs still offers toggle, on and off", () => {
  const panel = newPanel();
  panel._panel = { config: { labels: {} } };

  assert.deepEqual(
    panel._actionOptions("light.a", { none: false, run: false }).map((o) => o.value),
    ["toggle", "on", "off"],
  );
});

test("a new target keeps the action while it can do it, else brings its own", () => {
  const panel = withVerbs(newPanel(), {
    light: ["toggle", "on", "off"],
    media_player: ["toggle", "on", "off", "play_pause"],
    lock: ["lock"],
    script: ["on", "off", "toggle"],
  });
  panel._loadEditor(false, { double_press_target: "light.a" });

  // Both are switchable: what was chosen stays.
  panel._chooseGesture("double_press", "off");
  panel._retarget("double_press", "light.a", "media_player.tv");
  assert.equal(panel._editorChoices.double_press, "off");

  // A verb of the player means nothing to a lock: the lock brings its own.
  panel._chooseGesture("double_press", "play_pause");
  panel._retarget("double_press", "media_player.tv", "lock.door");
  assert.equal(panel._editorChoices.double_press, "lock");
  assert.equal(panel._editorData.double_press_action, "lock");

  // A script is run.
  panel._retarget("double_press", "lock.door", "script.go");
  assert.equal(panel._editorChoices.double_press, "on");
});

test("opening a garage door or a gate with a press is said beside the choice", () => {
  const panel = withVerbs(newPanel(), { cover: ["toggle", "open", "close", "stop"] }, {
    cover_open_warning: "Opens with nobody watching.",
  });
  panel._hass = {
    states: {
      "cover.garage": { attributes: { device_class: "garage" } },
      "cover.blind": { attributes: { device_class: "blind" } },
    },
  };

  assert.equal(panel._actionHelp("cover.garage", "open"), "Opens with nobody watching.");
  assert.equal(panel._actionHelp("cover.garage", "toggle"), "Opens with nobody watching.");
  assert.equal(panel._actionHelp("cover.garage", "close"), undefined);
  assert.equal(panel._actionHelp("cover.blind", "open"), undefined);
});

test("the live activity names a verb after the verb unless it has service words", () => {
  const panel = withVerbs(newPanel(), { light: ["toggle"] }, {
    service_toggle: "Toggle",
    action_play_pause: "Play / pause",
  });

  assert.equal(panel._serviceLabel("toggle"), "Toggle");
  assert.equal(panel._serviceLabel("play_pause"), "Play / pause");
});

test("an old short press its target cannot do is shown as no action", () => {
  const panel = withVerbs(newPanel(), {
    light: ["toggle", "on", "off"],
    input_number: ["step_up", "step_down"],
  });
  // Saved when only toggle, on and off existed: toggle on a number did nothing.
  panel._loadEditor(false, { target: "input_number.level", click_action: "toggle" });

  assert.equal(panel._editorChoices.click_action, "none");
  assert.equal(panel._editorData.click_action, "none");

  // A light keeps its toggle.
  panel._loadEditor(false, { target: "light.a", click_action: "toggle" });
  assert.equal(panel._editorChoices.click_action, "toggle");
});

test("clearing the short press target hands the choice to the rotation target", () => {
  const panel = withVerbs(newPanel(), {
    light: ["toggle", "on", "off"],
    button: ["press"],
  });
  panel._loadEditor(false, { target: "light.a", click_target: "button.doorbell" });
  panel._editorChoices.click_action = "press";
  panel._editorData.click_action = "press";

  panel._retarget("click", "button.doorbell", undefined);

  assert.equal(panel._editorChoices.click_action, "toggle");
  assert.equal(panel._editorData.click_action, "toggle");
});

// -- the actions a gesture runs ---------------------------------------------

class FakeNode {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.dataset = {};
    this.listeners = {};
    this.attrs = {};
    this.className = "";
    this.textContent = "";
    this.value = "";
  }
  appendChild(child) {
    this.children.push(child);
    return child;
  }
  append(...children) {
    this.children.push(...children);
  }
  addEventListener(name, handler) {
    this.listeners[name] = handler;
  }
  setAttribute(name, value) {
    this.attrs[name] = value;
  }
}

const walk = (node, found = []) => {
  found.push(node);
  for (const child of node.children || []) walk(child, found);
  return found;
};

const withFakeDom = (run) => {
  const previous = globalThis.document;
  globalThis.document = { createElement: (tag) => new FakeNode(tag) };
  try {
    return run();
  } finally {
    globalThis.document = previous;
    registry.delete("ha-selector");
  }
};

const actionPanel = (data = {}) => {
  const panel = newPanel();
  panel._panel = { config: { labels: {} } };
  panel._hass = {
    services: {
      light: { toggle: {}, turn_on: {} },
      media_player: { media_play_pause: {} },
    },
  };
  panel._loadEditor(false, { target: "light.a", ...data });
  let renders = 0;
  panel._render = () => {
    renders += 1;
  };
  return { panel, renders: () => renders };
};

const PLAY = [
  { action: "media_player.media_play_pause", target: { entity_id: "media_player.tv" } },
];

test("a gesture set to run has no target, keeps its actions and is not 'none'", () => {
  const { panel } = actionPanel({
    double_press_action: "run",
    double_press_sequence: PLAY,
    click_action: "run",
    click_sequence: PLAY,
  });

  assert.equal(panel._editorChoices.double_press, "run");
  assert.equal(panel._editorChoices.click_action, "run");
  assert.deepEqual(panel._editorData.double_press_sequence, PLAY);

  // Leaving run keeps the actions in the form, so switching back finds them.
  panel._chooseGesture("double_press", "toggle");
  assert.deepEqual(panel._editorData.double_press_sequence, PLAY);
  panel._chooseGesture("double_press", "run");
  assert.equal("double_press_target" in panel._editorData, false);
  assert.equal(panel._editorData.double_press_action, "run");
});

test("a gesture that runs actions needs some before it can be saved", () => {
  const { panel } = actionPanel();
  panel._chooseGesture("double_press", "run");
  panel._chooseGesture("click_action", "run");
  panel._editorData.hold_action = "run";

  assert.deepEqual(panel._choiceErrors(), {
    click_action: "actions_required",
    double_press_action: "actions_required",
    hold_action: "actions_required",
  });

  panel._editorData.double_press_sequence = PLAY;
  assert.equal("double_press_action" in panel._choiceErrors(), false);
});

test("Home Assistant's editor gets a copy and its changes are stored as a copy", () => {
  const { panel, renders } = actionPanel({
    double_press_action: "run",
    double_press_sequence: PLAY,
  });
  class FakeSelector extends FakeNode {
    constructor() {
      super("ha-selector");
    }
  }
  withFakeDom(() => {
    registry.set("ha-selector", FakeSelector);
    panel._actionEditor = "ha";

    const wrap = panel._actionsEditor("double_press_sequence", "double_press_action");
    const [editor] = walk(wrap).filter((node) => node.tag === "ha-selector");

    assert.deepEqual(editor.selector, { action: {} });
    assert.deepEqual(editor.value, PLAY);
    // Home Assistant's editor changes what it is given in place.
    editor.value[0].action = "changed.in.place";
    assert.equal(
      panel._editorData.double_press_sequence[0].action,
      "media_player.media_play_pause",
    );

    const next = [{ action: "light.toggle" }];
    editor.listeners["value-changed"]({
      stopPropagation: () => undefined,
      detail: { value: next },
    });
    assert.deepEqual(panel._editorData.double_press_sequence, next);
    next[0].action = "mutated.after";
    assert.equal(panel._editorData.double_press_sequence[0].action, "light.toggle");
    // The editor keeps its own state: rebuilding it under the person's hands
    // would lose their place.
    assert.equal(renders(), 0);
  });
});

test("without Home Assistant's editor the same actions are edited as a list", () => {
  const { panel, renders } = actionPanel({
    double_press_action: "run",
    double_press_sequence: PLAY,
  });
  withFakeDom(() => {
    panel._actionEditor = "form";
    const wrap = panel._actionsEditor("double_press_sequence", "double_press_action");
    const nodes = walk(wrap);

    // One row per action, with a service select, entities and data.
    const selects = nodes.filter((node) => node.tag === "select");
    assert.equal(selects.length, 1);
    const options = walk(selects[0]).filter((node) => node.tag === "option");
    assert.ok(options.map((o) => o.value).includes("media_player.media_play_pause"));

    const [add] = nodes.filter(
      (n) => n.tag === "button" && n.textContent === "actions_add",
    );
    add.listeners.click();
    assert.equal(panel._editorData.double_press_sequence.length, 2);
    assert.equal(renders(), 1);

    // The panel draws again after a change; so does this.
    const again = walk(
      panel._actionsEditor("double_press_sequence", "double_press_action"),
    );
    const [remove] = again.filter(
      (n) => n.tag === "button" && n.textContent === "actions_remove",
    );
    remove.listeners.click();
    assert.equal(panel._editorData.double_press_sequence.length, 1);
  });
});

test("the JSON box replaces the list, and a mistake changes nothing", () => {
  const { panel } = actionPanel({
    double_press_action: "run",
    double_press_sequence: PLAY,
  });
  withFakeDom(() => {
    panel._actionEditor = "form";
    const wrap = panel._actionsEditor("double_press_sequence", "double_press_action");
    const boxes = walk(wrap).filter((node) => node.tag === "textarea");
    const json = boxes[boxes.length - 1];
    assert.deepEqual(JSON.parse(json.value), PLAY);

    json.value = "{ not json";
    json.listeners.change();
    assert.deepEqual(panel._editorData.double_press_sequence, PLAY);
    assert.equal(json.attrs["aria-invalid"], "true");

    // An object is not a list of actions.
    json.value = JSON.stringify({ action: "light.toggle" });
    json.listeners.change();
    assert.deepEqual(panel._editorData.double_press_sequence, PLAY);

    json.value = JSON.stringify([{ delay: { seconds: 1 } }, { action: "light.toggle" }]);
    json.listeners.change();
    assert.deepEqual(panel._editorData.double_press_sequence, [
      { delay: { seconds: 1 } },
      { action: "light.toggle" },
    ]);
  });
});

test("an action the list cannot show is kept and can be removed", () => {
  const { panel } = actionPanel({
    double_press_action: "run",
    double_press_sequence: [{ delay: { seconds: 2 } }, ...PLAY],
  });
  withFakeDom(() => {
    panel._actionEditor = "form";
    const wrap = panel._actionsEditor("double_press_sequence", "double_press_action");

    // Only the plain action has fields; the delay is shown as a note.
    assert.equal(walk(wrap).filter((node) => node.tag === "select").length, 1);
    assert.deepEqual(panel._editorData.double_press_sequence[0], {
      delay: { seconds: 2 },
    });
  });
});

test("the editor of Home Assistant is loaded once, and only when it is needed", async () => {
  const previousElements = globalThis.customElements;
  const loaded = [];
  const hass = {
    loadBackendTranslation: async (name) => loaded.push(name),
    loadFragmentTranslation: async (name) => loaded.push(name),
  };
  try {
    // Already there: nothing to drive.
    Panel._forgetActionEditor();
    globalThis.customElements = {
      get: () => class {},
      whenDefined: () => {
        throw new Error("must not be asked");
      },
    };
    assert.equal(await Panel._loadActionEditor(hass), true);
    assert.deepEqual(loaded.sort(), ["config", "entity_component", "selector", "services"]);

    // Remembered: a second ask does not load again.
    loaded.length = 0;
    assert.equal(await Panel._loadActionEditor(hass), true);
    assert.deepEqual(loaded, []);
  } finally {
    globalThis.customElements = previousElements;
    Panel._forgetActionEditor();
  }
});

test("a frontend that cannot be driven leaves the simple list, not an error", async () => {
  const previousElements = globalThis.customElements;
  const previousDocument = globalThis.document;
  const warn = console.warn;
  console.warn = () => undefined;
  try {
    for (const resolver of [
      {}, // no _getRoutes
      { _getRoutes: () => ({ routes: {} }) }, // no route to the config panel
    ]) {
      Panel._forgetActionEditor();
      globalThis.customElements = {
        get: () => undefined,
        whenDefined: async () => undefined,
      };
      globalThis.document = { createElement: () => resolver };
      assert.equal(await Panel._loadActionEditor({}), false);
    }
    // The element never appears.
    Panel._forgetActionEditor();
    globalThis.customElements = {
      get: () => undefined,
      whenDefined: () => Promise.reject(new Error("never defined")),
    };
    assert.equal(await Panel._loadActionEditor({}), false);
  } finally {
    console.warn = warn;
    globalThis.customElements = previousElements;
    globalThis.document = previousDocument;
    Panel._forgetActionEditor();
  }
});

test("run, then cycle scenes: the short press is no longer run, so it can be saved", () => {
  const { panel } = actionPanel({ click_action: "run", click_sequence: PLAY });

  panel._chooseGesture("click_action", "scenes");

  assert.equal(panel._editorChoices.click_action, "scenes");
  assert.equal(panel._editorData.click_action, "toggle");
});

test("a short press that runs actions keeps run next to a scene target", () => {
  const { panel } = actionPanel({
    click_action: "run",
    click_target: "scene.evening",
    click_sequence: PLAY,
  });

  assert.equal(panel._editorChoices.click_action, "run");
  assert.equal(panel._editorData.click_action, "run");
  assert.deepEqual(panel._editorData.click_sequence, PLAY);
});

test("Home Assistant's editor is built once per field and kept across redraws", () => {
  const { panel } = actionPanel({
    double_press_action: "run",
    double_press_sequence: PLAY,
  });
  class FakeSelector extends FakeNode {
    constructor() {
      super("ha-selector");
    }
  }
  withFakeDom(() => {
    registry.set("ha-selector", FakeSelector);
    panel._actionEditor = "ha";
    const pick = () =>
      walk(panel._actionsEditor("double_press_sequence", "double_press_action")).find(
        (node) => node.tag === "ha-selector",
      );

    const first = pick();
    // An answer from Home Assistant's dialog must find the editor it came from.
    assert.equal(pick(), first);

    // Another binding brings editors of its own.
    panel._loadEditor(false, { target: "light.a" });
    assert.notEqual(pick(), first);
  });
});

test("what the server refused about the list is said under the editor", () => {
  const { panel } = actionPanel({ double_press_action: "run", double_press_sequence: PLAY });
  withFakeDom(() => {
    panel._actionEditor = "form";
    panel._editorErrors = { double_press_sequence: "invalid_value" };

    const wrap = panel._actionsEditor("double_press_sequence", "double_press_action");

    const note = walk(wrap)
      .filter((node) => node.className === "field-error" && !node.hidden)
      .at(-1);
    assert.equal(note.textContent, "validation_invalid_value");
  });
});

test("a row added and not given an action cannot be saved", () => {
  const { panel } = actionPanel({ double_press_action: "run", double_press_sequence: PLAY });
  withFakeDom(() => {
    panel._actionEditor = "form";
    const wrap = panel._actionsEditor("double_press_sequence", "double_press_action");
    const [add] = walk(wrap).filter(
      (n) => n.tag === "button" && n.textContent === "actions_add",
    );
    add.listeners.click();

    assert.deepEqual(panel._editorData.double_press_sequence[1], { action: "" });
    assert.equal(panel._choiceErrors().double_press_action, "actions_incomplete");
  });
});

test("only a plain action gets fields: a template target or data stays as written", () => {
  const { panel } = actionPanel({
    double_press_action: "run",
    double_press_sequence: [
      { action: "light.toggle", target: "{{ states('sensor.x') }}" },
      { action: "light.toggle", data: "{{ x }}" },
    ],
  });
  withFakeDom(() => {
    panel._actionEditor = "form";
    const wrap = panel._actionsEditor("double_press_sequence", "double_press_action");

    assert.equal(walk(wrap).filter((node) => node.tag === "select").length, 0);
    assert.equal(
      panel._editorData.double_press_sequence[0].target,
      "{{ states('sensor.x') }}",
    );
  });
});

test("a load that failed is asked again the next time, not remembered", async () => {
  const previousElements = globalThis.customElements;
  const warn = console.warn;
  console.warn = () => undefined;
  let asked = 0;
  try {
    Panel._forgetActionEditor();
    globalThis.customElements = {
      get: () => undefined,
      whenDefined: () => {
        asked += 1;
        return Promise.reject(new Error("not yet"));
      },
    };
    assert.equal(await Panel._loadActionEditor({}), false);
    assert.equal(await Panel._loadActionEditor({}), false);
    assert.equal(asked, 2);
  } finally {
    console.warn = warn;
    globalThis.customElements = previousElements;
    Panel._forgetActionEditor();
  }
});

test("text that was refused blocks Save until it is corrected", () => {
  const { panel } = actionPanel({ double_press_action: "run", double_press_sequence: PLAY });
  withFakeDom(() => {
    panel._actionEditor = "form";
    const wrap = panel._actionsEditor("double_press_sequence", "double_press_action");
    const boxes = walk(wrap).filter((node) => node.tag === "textarea");
    const json = boxes[boxes.length - 1];

    json.value = "{ not json";
    json.listeners.change();

    // The old list is still in the draft; saving it would drop what was typed.
    assert.equal(panel._choiceErrors().double_press_action, "actions_invalid");

    json.value = JSON.stringify(PLAY);
    json.listeners.change();
    assert.equal("double_press_action" in panel._choiceErrors(), false);
  });
});

test("a box left by clicking Save does not redraw the form under the button", () => {
  const { panel, renders } = actionPanel({
    double_press_action: "run",
    double_press_sequence: PLAY,
  });
  withFakeDom(() => {
    panel._actionEditor = "form";
    const wrap = panel._actionsEditor("double_press_sequence", "double_press_action");
    const boxes = walk(wrap).filter((node) => node.tag === "textarea");
    const json = boxes[boxes.length - 1];
    json.value = JSON.stringify([{ action: "light.toggle" }]);

    json.listeners.change();

    assert.deepEqual(panel._editorData.double_press_sequence, [{ action: "light.toggle" }]);
    // Drawn a moment later, not now: a click on Save may be on its way.
    assert.equal(renders(), 0);
    assert.notEqual(panel._renderLaterTimer, undefined);
    clearTimeout(panel._renderLaterTimer);
  });
});

test("a route load that ends without the element is not remembered either", async () => {
  const previousElements = globalThis.customElements;
  const previousDocument = globalThis.document;
  const warn = console.warn;
  console.warn = () => undefined;
  let loads = 0;
  try {
    Panel._forgetActionEditor();
    globalThis.customElements = {
      get: () => undefined,
      whenDefined: async () => undefined,
    };
    const route = { load: async () => (loads += 1) };
    globalThis.document = {
      createElement: () => ({
        _getRoutes: () => ({ routes: { tmp: route } }),
        routerOptions: { routes: { automation: route } },
      }),
    };
    assert.equal(await Panel._loadActionEditor({}), false);
    assert.equal(await Panel._loadActionEditor({}), false);
    assert.equal(loads, 4);
  } finally {
    console.warn = warn;
    globalThis.customElements = previousElements;
    globalThis.document = previousDocument;
    Panel._forgetActionEditor();
  }
});

test("refused text stays on screen and keeps blocking Save until it is corrected", () => {
  const { panel } = actionPanel({ double_press_action: "run", double_press_sequence: PLAY });
  withFakeDom(() => {
    panel._actionEditor = "form";
    const draw = () => {
      const boxes = walk(
        panel._actionsEditor("double_press_sequence", "double_press_action"),
      ).filter((node) => node.tag === "textarea");
      return boxes[boxes.length - 1];
    };
    let json = draw();
    json.value = "{ not json";
    json.listeners.change();

    // Another field of the list changes, and the form is drawn again.
    const [row] = walk(
      panel._actionsEditor("double_press_sequence", "double_press_action"),
    ).filter((node) => node.tag === "input");
    row.value = "light.a";
    row.listeners.change();

    // The refused text is put back, and saving is still refused.
    json = draw();
    assert.equal(json.value, "{ not json");
    assert.equal(json.attrs["aria-invalid"], "true");
    assert.equal(panel._choiceErrors().double_press_action, "actions_invalid");

    json.value = JSON.stringify(PLAY);
    json.listeners.change();
    assert.equal("double_press_action" in panel._choiceErrors(), false);
    assert.equal(draw().value, JSON.stringify(PLAY, null, 2));
  });
});

test("a click on a list that was replaced meanwhile acts on the real list", () => {
  const { panel, renders } = actionPanel({
    double_press_action: "run",
    double_press_sequence: PLAY,
  });
  withFakeDom(() => {
    panel._actionEditor = "form";
    const wrap = panel._actionsEditor("double_press_sequence", "double_press_action");
    const boxes = walk(wrap).filter((node) => node.tag === "textarea");
    const json = boxes[boxes.length - 1];
    const [add] = walk(wrap).filter(
      (n) => n.tag === "button" && n.textContent === "actions_add",
    );

    // The JSON box is changed and its redraw waits.
    const typed = [{ action: "light.toggle" }, { action: "light.turn_on" }];
    json.value = JSON.stringify(typed);
    json.listeners.change();
    clearTimeout(panel._renderLaterTimer);
    assert.deepEqual(panel._editorData.double_press_sequence, typed);

    // Add was drawn before that: it only shows the real list, and writes nothing
    // back.
    add.listeners.click();
    assert.deepEqual(panel._editorData.double_press_sequence, typed);
    assert.equal(renders(), 1);
  });
});

test("changing the actions clears the server's old verdict on them", () => {
  const { panel } = actionPanel({ double_press_action: "run", double_press_sequence: PLAY });
  panel._editorErrors = {
    double_press_sequence: "invalid_value",
    double_press_action: "actions_required",
  };

  panel._setSequence("double_press_sequence", "double_press_action", [
    { action: "light.toggle" },
  ]);

  assert.deepEqual(panel._editorErrors, {});
});

test("successive edits of one row keep each other, and adding keeps refused text", () => {
  const { panel } = actionPanel({
    double_press_action: "run",
    double_press_sequence: PLAY,
  });
  withFakeDom(() => {
    panel._actionEditor = "form";
    // The form is drawn once: a row edit does not redraw it.
    const wrap = panel._actionsEditor("double_press_sequence", "double_press_action");
    const nodes = walk(wrap);
    const target = nodes.find((n) => n.tag === "input");
    const [data] = nodes.filter((n) => n.tag === "textarea");

    target.value = "light.a, light.b";
    target.listeners.change();
    data.value = JSON.stringify({ brightness: 5 });
    data.listeners.change();

    assert.deepEqual(panel._editorData.double_press_sequence[0], {
      action: "media_player.media_play_pause",
      target: { entity_id: ["light.a", "light.b"] },
      data: { brightness: 5 },
    });

    // Refused data is still refused after a row is added at the end.
    data.value = "{ nope";
    data.listeners.change();
    const [add] = nodes.filter((n) => n.tag === "button" && n.textContent === "actions_add");
    add.listeners.click();
    assert.equal(panel._choiceErrors().double_press_action, "actions_invalid");
  });
});

test("removing a row keeps what was edited in the others", () => {
  const second = { action: "light.toggle", target: { entity_id: "light.a" } };
  const { panel } = actionPanel({
    double_press_action: "run",
    double_press_sequence: [...PLAY, second],
  });
  withFakeDom(() => {
    panel._actionEditor = "form";
    const nodes = walk(panel._actionsEditor("double_press_sequence", "double_press_action"));
    const inputs = nodes.filter((n) => n.tag === "input");
    const removes = nodes.filter((n) => n.tag === "button" && n.textContent === "actions_remove");

    inputs[1].value = "light.b";
    inputs[1].listeners.change();
    removes[0].listeners.click();

    assert.deepEqual(panel._editorData.double_press_sequence, [
      { action: "light.toggle", target: { entity_id: ["light.b"] } },
    ]);
  });
});

test("refused data keeps its row when another row goes", () => {
  const { panel } = actionPanel({
    double_press_action: "run",
    double_press_sequence: [
      ...PLAY,
      { action: "light.toggle" },
      { action: "light.turn_on" },
    ],
  });
  withFakeDom(() => {
    panel._actionEditor = "form";
    const nodes = walk(panel._actionsEditor("double_press_sequence", "double_press_action"));
    const data = nodes.filter((n) => n.tag === "textarea");
    data[2].value = "{ nope";
    data[2].listeners.change();
    const [remove] = nodes.filter((n) => n.tag === "button" && n.textContent === "actions_remove");

    remove.listeners.click();

    // The third row is the second now, and its refused text went with it.
    assert.deepEqual([...panel._refusedText.keys()], ["double_press_sequence|data|1"]);
    assert.equal(panel._choiceErrors().double_press_action, "actions_invalid");
  });
});

test("null is not data, and a templated target is left to the JSON box", () => {
  const templated = { action: "light.toggle", target: { entity_id: "{{ a }}, {{ b }}" } };
  const { panel } = actionPanel({
    double_press_action: "run",
    double_press_sequence: [...PLAY, templated],
  });
  withFakeDom(() => {
    panel._actionEditor = "form";
    const nodes = walk(panel._actionsEditor("double_press_sequence", "double_press_action"));

    // Only the first action has fields.
    assert.equal(nodes.filter((n) => n.tag === "select").length, 1);

    const data = nodes.filter((n) => n.tag === "textarea")[0];
    data.value = "null";
    data.listeners.change();
    assert.equal(panel._choiceErrors().double_press_action, "actions_invalid");
  });
});

test("text that was refused counts as an unsaved change", () => {
  const { panel } = actionPanel({ double_press_action: "run", double_press_sequence: PLAY });
  const before = panel._editorSnapshot();

  panel._refuse("double_press_sequence|json", "{ nope");

  assert.notEqual(panel._editorSnapshot(), before);
});

test("an answer from Home Assistant's editor after the form was closed does nothing", () => {
  const { panel } = actionPanel({ double_press_action: "run", double_press_sequence: PLAY });
  panel._editorData = null;

  assert.doesNotThrow(() =>
    panel._setSequence("double_press_sequence", "double_press_action", []),
  );
});
