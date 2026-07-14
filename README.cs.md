# IKEA BILRESA (plynulý scroll) pro Home Assistant

[English](README.md) · **Čeština** · [Slovenčina](README.sk.md)

[![hacs](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![release](https://img.shields.io/github/v/release/Vituhlos/ha-ikea-bilresa)](https://github.com/Vituhlos/ha-ikea-bilresa/releases)
[![license](https://img.shields.io/github/license/Vituhlos/ha-ikea-bilresa)](LICENSE)

Vrátí **kolečku IKEA BILRESA** (Matter přes Thread) plynulé ovládání — takové,
jaké má na originálním IKEA hubu DIRIGERA — tím, že reaguje na **`MultiPressOngoing`
události v reálném čase**, které vestavěná Matter integrace v Home Assistantu
zahazuje.

> **Stav:** v0.2 — vrstva událostí v reálném čase hotová. Blueprint na plynulé
> stmívání a GUI bindings na světla jsou v [plánu](#plán).

---

## Obsah

- [Proč to vzniklo](#proč-to-vzniklo)
- [Funkce](#funkce)
- [Jak to funguje](#jak-to-funguje)
- [Požadavky](#požadavky)
- [Instalace](#instalace)
- [Nastavení](#nastavení)
- [Používání (manuál)](#používání-manuál)
  - [Event entity](#event-entity)
  - [Přehled událostí](#přehled-událostí)
  - [Příklady automatizací](#příklady-automatizací)
  - [Sběrnicová událost `ikea_bilresa_event`](#sběrnicová-událost-ikea_bilresa_event)
- [Více koleček](#více-koleček)
- [Řešení potíží](#řešení-potíží)
- [Plán](#plán)
- [Omezení](#omezení)
- [Přispívání](#přispívání)
- [Licence](#licence)

## Proč to vzniklo

BILRESA se přes Matter hlásí jako **generický spínač (Generic Switch)** s multi-press
událostmi. Matter integrace v HA zveřejňuje jen `MultiPressComplete` — počká, až
otáčení *ukončíš*, a pak pošle jednu dávku „N stisků", navíc omezenou na 8. Výsledek
je laglé, skákavé stmívání a rychlé zatočení nad 8 zářezů se úplně ztratí.

Zařízení přitom posílá i **`MultiPressOngoing`** — průběžný čítač v reálném čase,
zatímco točíš — což je přesně to, co dělá hub DIRIGERA plynulým. Tato integrace si
otevře vlastní read-only WebSocket spojení k Matter Serveru a tyto průběžné události
poslouchá, takže Home Assistant reaguje během gesta, ne až po něm.

Navazující práce v HA:
[core#159035 (issue)](https://github.com/home-assistant/core/issues/159035) ·
[core#159045 (PR)](https://github.com/home-assistant/core/pull/159045).

## Funkce

- ⚡ **Reakce v reálném čase** — reaguje na `MultiPressOngoing` už během otáčení,
  ne až po zastavení.
- 🔢 **Správné počítání zářezů** — gesture engine převádí kumulativní, dávkovaný
  čítač kolečka na **delty za jednotlivé události** (až 18 na gesto), takže se jas
  posune o správnou hodnotu.
- 🧭 **Automatické nalezení libovolného počtu koleček** — kanály a směry se čtou
  z Matter deskriptorů každého kolečka; nic není napevno.
- 🎛️ **Čisté události** — `rotate_up` / `rotate_down` (s počtem `notches`),
  `press` / `double_press` / `triple_press`, `hold`, `release`.
- 🪶 **Žádné závislosti navíc** — drobný WebSocket klient nad `aiohttp`, nic se
  neinstaluje ani nerozbíjí při aktualizacích.
- 🛡️ **Bezpečné a pasivní** — jen *poslouchá*; nikdy neposílá příkazy zařízením,
  takže nemůže rušit jádrovou Matter integraci.

## Jak to funguje

```
kolečko BILRESA ──Matter/Thread──▶ Matter Server ──WS──▶ tato integrace ──▶ event entity
                                                                          └▶ ikea_bilresa_event
```

Integrace se připojí k WebSocketu Matter Serveru (výchozí
`ws://core-matter-server:5580/ws`, automaticky zjištěné z tvé Matter konfigurace),
pošle jednou `start_listening` a dekóduje události clusteru `Switch` (`0x003B`) pro
každý nalezený BILRESA uzel.

Každé kolečko má **3 kanály**, každý = 3 Matter Switch endpointy:

| Role | Matter schopnosti |
|------|-------------------|
| Scroll ↑ / ↓ (rotary) | MomentarySwitch + Release + MultiPress, `MultiPressMax = 18` |
| Tlačítko (stisk) | navíc LongPress, `MultiPressMax = 3` |

## Požadavky

- Home Assistant **2024.6** nebo novější.
- Add-on **Matter Server** (nebo externí Matter Server) s BILRESA kolečky už
  spárovanými do Matteru a funkčními.
- Nakonfigurovaná jádrová integrace **Matter** (slouží k automatickému zjištění
  URL serveru; BILRESA může být spárovaná do Home Assistantu i Apple Home).

## Instalace

### HACS (doporučeno)

1. HACS → ⋮ → **Vlastní repozitáře** → přidej
   `https://github.com/Vituhlos/ha-ikea-bilresa`, kategorie **Integration**.
2. Nainstaluj **IKEA BILRESA (smooth scroll)**.
3. **Restartuj Home Assistant.**

### Ručně

Zkopíruj složku `custom_components/ikea_bilresa/` do
`config/custom_components/` v Home Assistantu a restartuj.

## Nastavení

**Nastavení → Zařízení a služby → Přidat integraci → IKEA BILRESA.**
Potvrď předvyplněnou URL Matter Serveru (měň ji jen pokud běží jinde). Integrace
najde všechna kolečka automaticky a vytvoří jedno zařízení na kolečko s jednou
event entitou na kanál.

## Používání (manuál)

Tato sekce je manuál pro aktuální verzi (v0.2).

### Event entity

Každý kanál kolečka se stane `event` entitou, např.
`event.bilresa_scroll_wheel_nelca_channel_1`. Její stav je časové razítko poslední
akce; atribut `event_type` (a `notches` / `presses`) říká, co se stalo. Používej ji
jako spouštěč automatizace.

### Přehled událostí

| `event_type` | Význam | Atribut navíc |
|--------------|--------|---------------|
| `rotate_up` | Zatočeno nahoru o *N* zářezů | `notches` |
| `rotate_down` | Zatočeno dolů o *N* zářezů | `notches` |
| `press` | Jednoduchý stisk | `presses` = 1 |
| `double_press` | Dvojstisk | `presses` = 2 |
| `triple_press` | Trojstisk | `presses` = 3 |
| `hold` | Podržení tlačítka | — |
| `release` | Uvolnění po podržení | — |

### Příklady automatizací

**Plynulé stmívání** — posuň jas o počet zářezů, s `transition`, aby světlo mezi
~1s dávkami kolečka plynule najíždělo:

```yaml
alias: BILRESA – plynulé zesvětlení
triggers:
  - trigger: state
    entity_id: event.bilresa_scroll_wheel_nelca_channel_1
    attribute: event_type
    to: rotate_up
conditions:
  - "{{ trigger.to_state.attributes.event_type == 'rotate_up' }}"
actions:
  - action: light.turn_on
    target:
      entity_id: light.svetylka_svetylka
    data:
      brightness_step_pct: "{{ trigger.to_state.attributes.notches * 3 }}"
      transition: 1
mode: parallel
max: 20
```

Zduplikuj s `rotate_down` a záporným krokem pro ztlumení a přidej spouštěč
`press` volající `light.toggle` pro tlačítko.

### Sběrnicová událost `ikea_bilresa_event`

Každá akce se navíc vypálí na sběrnici jako `ikea_bilresa_event` — hodí se pro
jednu automatizaci obsluhující víc koleček. Pole: `node_id`, `wheel_name`,
`channel`, `endpoint_id`, `type` (`rotate` / `press` / `hold` / `release`),
`direction` (`up` / `down`), `notches`, `presses`.

```yaml
triggers:
  - trigger: event
    event_type: ikea_bilresa_event
    event_data:
      type: rotate
```

## Více koleček

Vše je klíčované podle Matter uzlu a endpointu, takže **libovolný počet koleček**
funguje najednou bez konfigurace — každé se najde a dostane vlastní zařízení,
entity a události. Pole `node_id` / `wheel_name` / `channel` je v automatizacích
rozliší.

## Řešení potíží

**Zapni debug logování** (Nastavení → Systém → Logy, nebo):

```yaml
logger:
  logs:
    custom_components.ikea_bilresa: debug
```

- **Nenašla se kolečka** — ověř, že kolečko funguje v jádrové Matter integraci a
  že URL Matter Serveru je správná. Log při startu vypíše
  `Discovered BILRESA wheel: node …`.
- **Při otáčení nechodí události** — zkontroluj baterii kolečka a že se jádrové
  Matter `event.*` entity při otáčení aktualizují.
- **Špatný kanál** — kolečko má fyzický přepínač 3 kanálů; posílá ten aktivní.

## Plán

- [x] Listener v reálném čase, auto-discovery koleček, `ikea_bilresa_event`. *(0.1)*
- [x] Gesture engine, `event` entity, zařízení na kolečko, čisté akce. *(0.2)*
- [ ] Blueprint na **plynulé stmívání**.
- [ ] **GUI bindings na světla** (config subentries) — namapuj kanál kolečka na
      světlo a integrace řídí jas/barvu přímo, bez YAML.
- [ ] Volby per binding: velikost kroku, akcelerace, min/max, akce tlačítek.

## Omezení

- Kolečko má vestavěnou ~500ms–1s anti-flood brzdu mezi dávkami zářezů, takže se
  to *blíží* pocitu DIRIGERA, ale není to úplně analogově spojité. Odpovídající
  `transition` na světle dávky přemostí do plynulého náběhu.
- Cílová světla jdou přes Home Assistant (ne přímý Matter/Zigbee bind), což přidá
  malou, obvykle nepostřehnutelnou LAN latenci.

## Přispívání

Issues a pull requesty jsou vítány. Při hlášení problému prosím uveď firmware
kolečka a verze Home Assistantu / Matter Serveru a u problémů se scrollem přilož
debug log událostí.

## Licence

[MIT](LICENSE) © 2026 Vituhlos
