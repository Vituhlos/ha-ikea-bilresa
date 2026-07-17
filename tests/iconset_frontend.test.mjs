import assert from "node:assert/strict";
import test from "node:test";

globalThis.window = globalThis;

await import(
  "../custom_components/ikea_bilresa/frontend/bilresa_icons.js"
);

test("registers the bilresa icon provider on both HA contracts", () => {
  assert.equal(
    window.customIcons.bilresa.getIcon,
    window.customIconsets.bilresa,
  );
  assert.equal(typeof window.customIcons.bilresa.getIconList, "function");
});

test("serves the selected two-path scroll-wheel glyph", async () => {
  const icon = await window.customIcons.bilresa.getIcon("scroll-wheel");

  assert.equal(icon.viewBox, "0 0 24 24");
  assert.match(icon.path, /M11\.3 1\.4/);
  assert.match(icon.secondaryPath, /M13\.05 1\.35/);
  assert.deepEqual(await window.customIcons.bilresa.getIconList(), [
    { name: "scroll-wheel" },
  ]);
});

test("does not invent icons outside the bilresa namespace contract", async () => {
  assert.equal(
    await window.customIcons.bilresa.getIcon("not-a-bilresa-icon"),
    undefined,
  );
});
