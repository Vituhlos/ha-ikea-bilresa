# Řešení potíží

[README](../../README.cs.md) · [Všichni průvodci](../README.md) · [English](../en/troubleshooting.md) · **Čeština**

**Zapněte debug logování** (Nastavení → Systém → Logy, nebo):

```yaml
logger:
  logs:
    custom_components.ikea_bilresa: debug
```

- **Nenašla se kolečka** — ověřte, že kolečko funguje v jádrové Matter integraci a
  že URL Matter Serveru je správná. Log při startu vypíše
  `Discovered BILRESA wheel: node …`.
- **Připojeno, ale při otáčení ani stisku nechodí události** — postupujte v tomto
  pořadí:
  1. V **Nastavení → Zařízení a služby → Matter** otevřete zařízení BILRESA.
     Aktualizují se jeho entity `event.*`, když otočíte kolečkem nebo
     stisknete? Pokud ne, příčina je pod touto integrací (baterie, síť Thread
     nebo hraniční router, spárování); opravte nejdřív to.
  2. Otevřete panel BILRESA, vyberte zařízení a **Živý test**. Otočte o jedno
     cvaknutí a jednou stiskněte. Objeví-li se řádky, události do integrace
     dorazí. Pokud se jádrové entity aktualizují, ale Živý test zůstává
     prázdný, pokračujte krokem 3.
  3. V panelu otevřete **Diagnostiku**: ukazuje, zda je Matter připojený, jaký
     zdroj událostí se používá (jádrový klient Matter, nebo vlastní WebSocket)
     a kdy přišla poslední událost. Zapněte debug logování podle návodu výše.
  4. Zkontrolujte kanál: kolečko má přepínač se 3 polohami a posílá jen zvolený
     kanál. Kanál vypnutý v panelu nevysílá nic (jeho přepínač je na jeho
     kartě).
  5. Pořád ticho? Založte [hlášení chyby](https://github.com/Vituhlos/ha-ikea-bilresa/issues/new/choose) s verzí Home Assistant Core,
     verzí Matter Serveru, modelem a firmwarem zařízení, informací, zda je
     spárované i s jiným řadičem, tím, co ukazují Živý test a Diagnostika, a
     staženou diagnostikou integrace (**Nastavení → Zařízení a služby → IKEA
     BILRESA → ⋮ → Stáhnout diagnostiku**; známé identifikátory skrývá, před
     přiložením ji přesto projděte).
- **Špatný kanál** — kolečko má fyzický přepínač 3 kanálů; posílá ten aktivní.
- **Tlačítko v panelu nemá v mém tématu čitelný popisek** — panel vyplňuje
  hlavní tlačítka akcentní barvou, tedy `state-icon-color` tématu, a píše na ně
  barvou `text-primary-color`. Téma, které obě nastaví na stejnou barvu (některá
  světlá na tmavém to dělají), udělá popisek stejně světlý jako výplň. Nastavte
  v tématu vlastní proměnné panelu, které nic jiného v Home Assistantu nemění:

  ```yaml
  # ve vašem tématu
  bilresa-accent: "#44739e"                # volitelné: výplň
  bilresa-on-accent: "rgba(0, 0, 0, 0.85)" # popisek na výplni
  ```

  Obě jsou volitelné a bez nich se použije `state-icon-color` a
  `text-primary-color`, takže téma, které je nenastaví, vypadá jako dřív.
