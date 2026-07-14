# IKEA BILRESA (plynulý scroll) pre Home Assistant

[English](README.md) · [Čeština](README.cs.md) · **Slovenčina**

[![hacs](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![release](https://img.shields.io/github/v/release/Vituhlos/ha-ikea-bilresa)](https://github.com/Vituhlos/ha-ikea-bilresa/releases)
[![license](https://img.shields.io/github/license/Vituhlos/ha-ikea-bilresa)](LICENSE)

Vráti **koliesku IKEA BILRESA** (Matter cez Thread) plynulé ovládanie — také, aké
má na originálnom IKEA hube DIRIGERA — tým, že reaguje na **`MultiPressOngoing`
udalosti v reálnom čase**, ktoré vstavaná Matter integrácia v Home Assistante
zahadzuje.

> **Stav:** v0.2 — vrstva udalostí v reálnom čase hotová. Blueprint na plynulé
> stmievanie a GUI bindings na svetlá sú v [pláne](#plán).

---

## Obsah

- [Prečo to vzniklo](#prečo-to-vzniklo)
- [Funkcie](#funkcie)
- [Ako to funguje](#ako-to-funguje)
- [Požiadavky](#požiadavky)
- [Inštalácia](#inštalácia)
- [Nastavenie](#nastavenie)
- [Používanie (manuál)](#používanie-manuál)
  - [Event entity](#event-entity)
  - [Prehľad udalostí](#prehľad-udalostí)
  - [Príklady automatizácií](#príklady-automatizácií)
  - [Zbernicová udalosť `ikea_bilresa_event`](#zbernicová-udalosť-ikea_bilresa_event)
- [Viac koliesok](#viac-koliesok)
- [Riešenie problémov](#riešenie-problémov)
- [Plán](#plán)
- [Obmedzenia](#obmedzenia)
- [Prispievanie](#prispievanie)
- [Licencia](#licencia)

## Prečo to vzniklo

BILRESA sa cez Matter hlási ako **generický spínač (Generic Switch)** s multi-press
udalosťami. Matter integrácia v HA zverejňuje len `MultiPressComplete` — počká, kým
otáčanie *ukončíš*, a potom pošle jednu dávku „N stlačení", navyše obmedzenú na 8.
Výsledok je laggy, skákavé stmievanie a rýchle otočenie nad 8 zárezov sa úplne
stratí.

Zariadenie pritom posiela aj **`MultiPressOngoing`** — priebežné počítadlo v reálnom
čase, kým točíš — čo je presne to, čo robí hub DIRIGERA plynulým. Táto integrácia si
otvorí vlastné read-only WebSocket spojenie k Matter Serveru a tieto priebežné
udalosti počúva, takže Home Assistant reaguje počas gesta, nie až po ňom.

Nadväzujúca práca v HA:
[core#159035 (issue)](https://github.com/home-assistant/core/issues/159035) ·
[core#159045 (PR)](https://github.com/home-assistant/core/pull/159045).

## Funkcie

- ⚡ **Reakcia v reálnom čase** — reaguje na `MultiPressOngoing` už počas otáčania,
  nie až po zastavení.
- 🔢 **Správne počítanie zárezov** — gesture engine prevádza kumulatívne, dávkované
  počítadlo kolieska na **delty za jednotlivé udalosti** (až 18 na gesto), takže sa
  jas posunie o správnu hodnotu.
- 🧭 **Automatické nájdenie ľubovoľného počtu koliesok** — kanály a smery sa čítajú
  z Matter deskriptorov každého kolieska; nič nie je natvrdo.
- 🎛️ **Čisté udalosti** — `rotate_up` / `rotate_down` (s počtom `notches`),
  `press` / `double_press` / `triple_press`, `hold`, `release`.
- 🪶 **Žiadne závislosti navyše** — drobný WebSocket klient nad `aiohttp`, nič sa
  neinštaluje ani nerozbíja pri aktualizáciách.
- 🛡️ **Bezpečné a pasívne** — len *počúva*; nikdy neposiela príkazy zariadeniam,
  takže nemôže rušiť jadrovú Matter integráciu.

## Ako to funguje

```
koliesko BILRESA ──Matter/Thread──▶ Matter Server ──WS──▶ táto integrácia ──▶ event entity
                                                                            └▶ ikea_bilresa_event
```

Integrácia sa pripojí k WebSocketu Matter Servera (predvolené
`ws://core-matter-server:5580/ws`, automaticky zistené z tvojej Matter
konfigurácie), pošle raz `start_listening` a dekóduje udalosti clusteru `Switch`
(`0x003B`) pre každý nájdený BILRESA uzol.

Každé koliesko má **3 kanály**, každý = 3 Matter Switch endpointy:

| Rola | Matter schopnosti |
|------|-------------------|
| Scroll ↑ / ↓ (rotary) | MomentarySwitch + Release + MultiPress, `MultiPressMax = 18` |
| Tlačidlo (stlačenie) | navyše LongPress, `MultiPressMax = 3` |

## Požiadavky

- Home Assistant **2024.6** alebo novší.
- Add-on **Matter Server** (alebo externý Matter Server) s BILRESA kolieskami už
  spárovanými do Matteru a funkčnými.
- Nakonfigurovaná jadrová integrácia **Matter** (slúži na automatické zistenie URL
  servera; BILRESA môže byť spárovaná do Home Assistantu aj Apple Home).

## Inštalácia

### HACS (odporúčané)

1. HACS → ⋮ → **Vlastné repozitáre** → pridaj
   `https://github.com/Vituhlos/ha-ikea-bilresa`, kategória **Integration**.
2. Nainštaluj **IKEA BILRESA (smooth scroll)**.
3. **Reštartuj Home Assistant.**

### Ručne

Skopíruj priečinok `custom_components/ikea_bilresa/` do
`config/custom_components/` v Home Assistante a reštartuj.

## Nastavenie

**Nastavenia → Zariadenia a služby → Pridať integráciu → IKEA BILRESA.**
Potvrď predvyplnenú URL Matter Servera (meň ju len ak beží inde). Integrácia nájde
všetky kolieska automaticky a vytvorí jedno zariadenie na koliesko s jednou event
entitou na kanál.

## Používanie (manuál)

Táto sekcia je manuál pre aktuálnu verziu (v0.2).

### Event entity

Každý kanál kolieska sa stane `event` entitou, napr.
`event.bilresa_scroll_wheel_nelca_channel_1`. Jej stav je časová pečiatka poslednej
akcie; atribút `event_type` (a `notches` / `presses`) hovorí, čo sa stalo. Používaj
ju ako spúšťač automatizácie.

### Prehľad udalostí

| `event_type` | Význam | Atribút navyše |
|--------------|--------|----------------|
| `rotate_up` | Otočené hore o *N* zárezov | `notches` |
| `rotate_down` | Otočené dole o *N* zárezov | `notches` |
| `press` | Jednoduché stlačenie | `presses` = 1 |
| `double_press` | Dvojstlačenie | `presses` = 2 |
| `triple_press` | Trojstlačenie | `presses` = 3 |
| `hold` | Podržanie tlačidla | — |
| `release` | Uvoľnenie po podržaní | — |

### Príklady automatizácií

**Plynulé stmievanie** — posuň jas o počet zárezov, s `transition`, aby svetlo medzi
~1s dávkami kolieska plynulo nabiehalo:

```yaml
alias: BILRESA – plynulé zosvetlenie
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

Zduplikuj s `rotate_down` a záporným krokom pre stlmenie a pridaj spúšťač `press`
volajúci `light.toggle` pre tlačidlo.

### Zbernicová udalosť `ikea_bilresa_event`

Každá akcia sa navyše vypáli na zbernicu ako `ikea_bilresa_event` — hodí sa pre
jednu automatizáciu obsluhujúcu viac koliesok. Polia: `node_id`, `wheel_name`,
`channel`, `endpoint_id`, `type` (`rotate` / `press` / `hold` / `release`),
`direction` (`up` / `down`), `notches`, `presses`.

```yaml
triggers:
  - trigger: event
    event_type: ikea_bilresa_event
    event_data:
      type: rotate
```

## Viac koliesok

Všetko je kľúčované podľa Matter uzla a endpointu, takže **ľubovoľný počet koliesok**
funguje naraz bez konfigurácie — každé sa nájde a dostane vlastné zariadenie, entity
a udalosti. Polia `node_id` / `wheel_name` / `channel` ich v automatizáciách rozlíšia.

## Riešenie problémov

**Zapni debug logovanie** (Nastavenia → Systém → Logy, alebo):

```yaml
logger:
  logs:
    custom_components.ikea_bilresa: debug
```

- **Nenašli sa kolieska** — over, že koliesko funguje v jadrovej Matter integrácii a
  že URL Matter Servera je správna. Log pri štarte vypíše
  `Discovered BILRESA wheel: node …`.
- **Pri otáčaní nechodia udalosti** — skontroluj batériu kolieska a že sa jadrové
  Matter `event.*` entity pri otáčaní aktualizujú.
- **Zlý kanál** — koliesko má fyzický prepínač 3 kanálov; posiela ten aktívny.

## Plán

- [x] Listener v reálnom čase, auto-discovery koliesok, `ikea_bilresa_event`. *(0.1)*
- [x] Gesture engine, `event` entity, zariadenie na koliesko, čisté akcie. *(0.2)*
- [ ] Blueprint na **plynulé stmievanie**.
- [ ] **GUI bindings na svetlá** (config subentries) — namapuj kanál kolieska na
      svetlo a integrácia riadi jas/farbu priamo, bez YAML.
- [ ] Voľby per binding: veľkosť kroku, akcelerácia, min/max, akcie tlačidiel.

## Obmedzenia

- Koliesko má vstavanú ~500ms–1s anti-flood brzdu medzi dávkami zárezov, takže sa to
  *blíži* pocitu DIRIGERA, ale nie je to úplne analógovo spojité. Zodpovedajúci
  `transition` na svetle dávky premostí do plynulého nábehu.
- Cieľové svetlá idú cez Home Assistant (nie priamy Matter/Zigbee bind), čo pridá
  malú, obvykle nepostrehnuteľnú LAN latenciu.

## Prispievanie

Issues a pull requesty sú vítané. Pri hlásení problému prosím uveď firmware kolieska
a verzie Home Assistantu / Matter Servera a pri problémoch so scrollom prilož debug
log udalostí.

## Licencia

[MIT](LICENSE) © 2026 Vituhlos
