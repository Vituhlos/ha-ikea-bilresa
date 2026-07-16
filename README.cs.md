# IKEA BILRESA (plynulý scroll) pro Home Assistant

> **Předávání vývoje:** aktuální stav implementace, úroveň ověření a prioritní
> backlog jsou v [PROJECT_STATUS.md](PROJECT_STATUS.md). Společný postup vývoje
> je v [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

[English](README.md) · **Čeština**

[![hacs](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![release](https://img.shields.io/github/v/release/Vituhlos/ha-ikea-bilresa)](https://github.com/Vituhlos/ha-ikea-bilresa/releases)
[![license](https://img.shields.io/github/license/Vituhlos/ha-ikea-bilresa)](LICENSE)

Vrátí **kolečku IKEA BILRESA** (Matter přes Thread) plynulé ovládání — takové,
jaké má na originálním IKEA hubu DIRIGERA — tím, že reaguje na **`MultiPressOngoing`
události v reálném čase**, které vestavěná Matter integrace v Home Assistantu
zahazuje.

> **Stav:** poslední stabilní vydání je v0.5.0; prerelease v0.5.9-rc.3 ladí
> administrátorský panel podle skutečných screenshotů z Home Assistanta.
> Zachovává detail koleček, živé výsledky propojení, testování akcí z panelu a
> revizně chráněné vytváření, úpravu a mazání propojení z v0.5.9-rc.1.
>
> Malý patch release train `0.5.1`–`0.5.7` je v
> [docs/ROADMAP.md](docs/ROADMAP.md).

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
zatímco točíš — což je přesně to, co dělá hub DIRIGERA plynulým. Tato integrace
odebírá události z existujícího Matter klienta Home Assistantu, takže reaguje
během gesta, ne až po něm. Na starším nebo nekompatibilním klientském API použije
jako fallback vlastní read-only WebSocket.

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

Integrace běžně znovu použije existující subscription klienta `MatterClient` z
jádrové Matter integrace. Kompatibilní fallback se připojí k WebSocketu Matter
Serveru (výchozí `ws://core-matter-server:5580/ws`), pošle jednou
`start_listening` a dekóduje události clusteru `Switch` (`0x003B`) pro každý
nalezený BILRESA uzel.

Každé kolečko má **3 kanály**, každý = 3 Matter Switch endpointy:

| Role | Matter schopnosti |
|------|-------------------|
| Scroll ↑ / ↓ (rotary) | MomentarySwitch + Release + MultiPress, `MultiPressMax = 18` |
| Tlačítko (stisk) | navíc LongPress, `MultiPressMax = 3` |

## Požadavky

- Home Assistant **2026.6** nebo novější.
- Add-on **Matter Server** (nebo externí Matter Server) s BILRESA kolečky už
  spárovanými do Matteru a funkčními.
- Nakonfigurovaná jádrová integrace **Matter** (slouží k automatickému zjištění
  URL serveru; BILRESA může být spárovaná do Home Assistantu i Apple Home).

## Instalace

### HACS (doporučeno)

1. HACS → ⋮ → **Vlastní repozitáře** → přidej
   `https://github.com/Vituhlos/ha-ikea-bilresa`, kategorie **Integration**.
2. Nainstaluj **IKEA BILRESA**.
3. **Restartuj Home Assistant.**

### Ručně

Zkopíruj složku `custom_components/ikea_bilresa/` do
`config/custom_components/` v Home Assistantu a restartuj.

## Nastavení

**Nastavení → Zařízení a služby → Přidat integraci → IKEA BILRESA.**
Potvrď předvyplněnou URL Matter Serveru (měň ji jen pokud běží jinde). Integrace
najde všechna kolečka automaticky a vytvoří jedno zařízení na kolečko s jednou
event entitou na kanál.

### GUI ovládací propojení (ovládání bez YAML)

Nechceš psát automatizace? U položky **IKEA BILRESA**
(Nastavení → Zařízení a služby) klikni na **＋ Přidat → Ovládací propojení** a vyber:

- výchozí profil (světlo, média, roleta, klima, scény nebo vlastní), případně
  zkopíruj existující propojení jako výchozí nastavení,
- **Kolečko** a **Kanál**,
- **cílovou entitu**, kterou scroll ovládá,
- **Změnu jasu na zářez** (%), **Minimální jas** (%, `0` = otočením dolů lze
  světlo vypnout) a **Přechod** (s),
- **akci jednoduchého stisku** (přepnout / zapnout / vypnout / nic) a volitelný
  **cíl tlačítka** — takže stisk může ovládat *jinou* entitu než stmívané světlo
  (např. stmíváš žárovku, ale přepínáš její Shelly ve vypínači),
- **odezvu tlačítka**: rychlý jednoduchý stisk pro okamžité přímé ovládání,
  nebo přesné rozpoznání jednoho, dvou či tří stisků,
- volitelný seřazený seznam **scén**, které jednoduché stisky postupně aktivují
  (má přednost před běžnou akcí jednoduchého stisku),
- **akci při podržení**: přepnout entitu, plynule měnit cíl scrollu, nebo nic.
  Rampování začne nahoru a po každém dokončeném podržení obrátí směr, protože
  událost dlouhého stisku BILRESY sama žádný směr nenese.

Pro rychlou odezvu zvol **Rychlý jednoduchý stisk**; akce tohoto propojení se
provede hned po uvolnění tlačítka. Pokud propojení používá cíle pro dvojstisk či
trojstisk, zvol rozpoznání více stisků, které počká na dokončovací událost
BILRESY. Existující propojení bez uložené volby zachovají dosavadní čekání,
dokud režim výslovně nezměníš. Veřejné event entity a device triggery přesně
rozlišují jeden, dva a tři stisky v obou režimech.

Integrace pak to světlo stmívá v reálném čase. Přidej si klidně víc propojení —
jedno na kanál kolečka — takže to škáluje na libovolný počet koleček bez YAML.
Když cíl chybí nebo je `unknown` či `unavailable`, propojení neposílá žádný
příkaz; rampování se bezpečně zastaví a další akce po návratu vyjde ze skutečného
stavu entity. Otočení nahoru z vypnutého světla začne na nastaveném minimu
(nebo prvním použitelném kroku, když je minimum nula). Externí změna v HA
přenastaví výchozí bod dalšího otočení; obrácení směru během přechodu pokračuje
z poslední požadované hodnoty.

Zapnutá akcelerace vychází z počtu dekódovaných zářezů za uplynulý čas, ne z
velikosti jedné Matter dávky. Resetuje se po pauze, změně směru, dokončení gesta
a reconnectu; výchozí hodnota zůstává vypnutá do fyzického doladění. Ochrana po
stisku sleduje hranice gest, takže stará dobíhající dávka nevrátí akci tlačítka,
ale nové úmyslné otočení projde ihned.

## Používání (manuál)

Tato sekce popisuje současné chování integrace. Funkce nad rámec posledního
vydání jsou označené v [PROJECT_STATUS.md](PROJECT_STATUS.md).

### Event entity

Každý kanál kolečka se stane `event` entitou, např.
`event.bilresa_scroll_wheel_channel_1`. Její stav je časové razítko poslední
akce; atribut `event_type` (a `notches` / `presses`) říká, co se stalo. Používej ji
jako hlavní spouštěč automatizace. Entity používají nativní button event device
class Home Assistantu; kompatibilní doménová událost navíc obsahuje registry
`device_id`, pokud je dostupné.

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
    entity_id: event.bilresa_scroll_wheel_channel_1
    attribute: event_type
    to: rotate_up
conditions:
  - "{{ trigger.to_state.attributes.event_type == 'rotate_up' }}"
actions:
  - action: light.turn_on
    target:
      entity_id: light.priklad
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
- [x] **GUI bindings na světla** (config subentries) — namapuj kanál kolečka na
      světlo a integrace řídí jas přímo, bez YAML. *(0.3)*
- [x] Minimální práh jasu a samostatný cíl tlačítka. *(0.4)*
- [x] CI, unit testy a diagnostics. *(0.5)*
- [x] Hot add/remove koleček, stav připojení/Repairs a in-place bindingy.
      *(další)*
- [x] Režimy scrollu (jas / teplota bílé / barva), akcelerace, max jas,
      akce double/triple/hold. *(další)*
- [x] **Device triggers** a **blueprint na plynulé stmívání**. *(další)*
- [x] Cyklení scén, hold-to-ramp a informace System Health. *(další)*
- [x] Změna URL Matter Serveru přes parent reconfigure flow. *(další)*
- [x] Prověřené discovery — HA nemá podporovaný discovery zdroj pro závislost na
      jiné integraci; rozhodnutí je v [docs/DISCOVERY.md](docs/DISCOVERY.md).
- [x] Interní `quality_scale.yaml` pouze s doloženými pravidly `done`/`exempt`.
- [x] Reuse event streamu core Matter klienta s kompatibilním fallbackem na
      samostatný pasivní WebSocket. *(další)*
- [x] Naplánovaný stabilizační patch train `0.5.1`–`0.5.7`; implementace je v
      pracovním stromu, ale každý balík má vlastní ověřovací bránu.
- [ ] Dokončit hardwarové ověření a automatické pokrytí testy.
- [ ] **Finální publikační fáze:** brand icon/PR do `home-assistant/brands` a
      zařazení do výchozího HACS katalogu, až když bude integrace hotová.

## Omezení

- Kolečko má vestavěnou ~500ms–1s anti-flood brzdu mezi dávkami zářezů, takže se
  to *blíží* pocitu DIRIGERA, ale není to úplně analogově spojité. Odpovídající
  `transition` na světle dávky přemostí do plynulého náběhu.
- Cílová světla jdou přes Home Assistant (ne přímý Matter/Zigbee bind), což přidá
  malou, obvykle nepostřehnutelnou LAN latenci.

## Přispívání

Issues a pull requesty jsou vítány. Při hlášení problému prosím uveď firmware
kolečka a verze Home Assistantu / Matter Serveru a u problémů se scrollem přilož
debug log událostí. Postup vývoje a hardwarového ověření je v
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) a
[docs/HARDWARE_TEST.md](docs/HARDWARE_TEST.md).

## Licence

[MIT](LICENSE) © 2026 Vituhlos
