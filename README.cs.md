# IKEA BILRESA pro Home Assistant

[English](README.md) · **Čeština**

[![release](https://img.shields.io/github/v/release/Vituhlos/ha-ikea-bilresa)](https://github.com/Vituhlos/ha-ikea-bilresa/releases)
[![CI](https://github.com/Vituhlos/ha-ikea-bilresa/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Vituhlos/ha-ikea-bilresa/actions/workflows/ci.yml)
[![stars](https://img.shields.io/github/stars/Vituhlos/ha-ikea-bilresa)](https://github.com/Vituhlos/ha-ikea-bilresa/stargazers)
[![license](https://img.shields.io/github/license/Vituhlos/ha-ikea-bilresa)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/use/custom_repositories/)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.8.0%2B-41BDF5)

Responzivní ovládání s konfigurací v GUI pro **kolečko i dvoutlačítko IKEA
BILRESA** (Matter přes Thread). Kolečko zpracovává události `MultiPressOngoing`
a reaguje už během otáčení — ne až po zastavení. Fyzický ovladač ale stále hlásí
cvaknutí v dávkách, takže jde o svižnější stupňovité ovládání, nikoli o
skutečně analogově plynulé scrollování. Dvoutlačítko získává samostatné event
entity, propojení, spouštěče automatizací a stejný panel BILRESA.

Pokud vám tato integrace šetří čas, můžete podpořit její vývoj. Je to zcela dobrovolné.

<a href="https://buymeacoffee.com/Vituhlos"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" height="40"></a>

> **Stav:** poslední stabilní vydání je **v0.6.1**, tedy 0.6.0 s opravou: panel
> mluví jazykem, který si každý uživatel zvolil ve svém profilu. Řada 0.6
> přidává dvoutlačítko BILRESA, panel BILRESA, další cíle propojení a spouštěče
> automatizací pro každé gesto. Vyžaduje Home Assistant 2026.8 nebo novější a
> nahrazuje dřívější spouštěče zařízení; před přechodem z 0.5.x si přečtěte
> poznámky k přechodu v [CHANGELOG.md](CHANGELOG.md) a udělejte zálohu.
>
> **Stav ověření:** předběžné vydání `v0.7.0-rc.4` obsahuje přepracované
> rozložení panelu a editor propojení, které ve stabilním vydání nejsou, spolu s opravami z
> `v0.6.2-rc.2` (světelné skupiny Zigbee2MQTT, událost `short_release`, vypnuté
> kanály). Je to testovací kandidát bez ověření na hardwaru. Některé kombinace zařízení a gest stále čekají na
> hardwarové ověření; aktuální checklist je v
> [docs/HARDWARE_TEST.md](docs/HARDWARE_TEST.md).

---

## Obsah

- [Proč to vzniklo](#proč-to-vzniklo)
- [Funkce](#funkce)
- [Jak to funguje](#jak-to-funguje)
- [Požadavky](#požadavky)
  - [Kompatibilita](#kompatibilita)
- [Instalace](#instalace)
- [Nastavení](#nastavení)
  - [Panel BILRESA](#panel-bilresa)
  - [GUI ovládací propojení](#gui-ovládací-propojení-ovládání-bez-yaml)
  - [Scény a skripty jako cíle](#scény-a-skripty-jako-cíle)
- [Používání (manuál)](#používání-manuál)
  - [Event entity](#event-entity)
  - [Entity číselníku a tlačítka](#entity-číselníku-a-tlačítka)
  - [Přehled událostí](#přehled-událostí)
  - [Spouštěče](#spouštěče)
  - [Příklady automatizací](#příklady-automatizací)
  - [Blueprint: plynulé stmívání](#blueprint-plynulé-stmívání)
  - [Sběrnicová událost `ikea_bilresa_event`](#sběrnicová-událost-ikea_bilresa_event)
  - [Okamžité akce po krátkém uvolnění](#okamžité-akce-po-krátkém-uvolnění)
- [Více koleček](#více-koleček)
- [Řešení potíží](#řešení-potíží)
- [Plán](#plán)
- [Omezení](#omezení)
- [Komunitní nástroje](#komunitní-nástroje)
- [Přispívání](#přispívání)
- [Licence](#licence)

## Proč to vzniklo

BILRESA se přes Matter hlásí jako **generický spínač (Generic Switch)** s multi-press
událostmi. Matter integrace v HA zveřejňuje jen `MultiPressComplete` — počká, až
otáčení *ukončíte*, a pak pošle jednu dávku „N stisků", navíc omezenou na 8. Výsledek
je laglé, skákavé stmívání a rychlé otočení o víc než 8 cvaknutí se úplně ztratí.

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
- 🔢 **Správné počítání cvaknutí** — gesture engine převádí kumulativní, dávkovaný
  čítač kolečka na **delty za jednotlivé události** (až 18 na gesto), takže se jas
  posune o správnou hodnotu.
- 🧭 **Automatické nalezení libovolného počtu zařízení BILRESA** — kolečka a
  dvoutlačítka se rozlišují podle Matter endpointů, ne podle názvu produktu
  nebo konkrétní instalace.
- 🎛️ **Čisté události** — `rotate_up` / `rotate_down` (s počtem `notches`),
  `press` / `double_press` / `triple_press`, `hold`, `release` pro kolečko;
  tlačítko 1/2 nabízí `press`, `double_press`, `hold`, `release`.
- 🔘 **Nezávislá propojení dvoutlačítka** — každé tlačítko může přepínat jiný
  cíl, nebo mohou na společném světle používat pevný směr zesílit/zeslabit.
- 🖥️ **Panel v postranním menu** — přehled zařízení BILRESA, editor s jednou
  částí na každé gesto, živý test, který ukáže, co gesto udělalo, a diagnostika
  jen pro čtení. Česky a anglicky, každému uživateli v jeho vlastním jazyce.
- 🎚️ **Ovládací propojení bez YAML** — otáčení stmívá světlo, mění hlasitost,
  polohu krytu, teplotu nebo rychlost ventilátoru; stisk, dvojitý stisk, trojitý
  stisk nebo podržení přepne, zapne či vypne, nebo spustí **scénu** či **skript**.
- 📟 **Entity číselníku a tlačítka** — každý kanál kolečka má navíc číselník
  1–100 a přepínač zapnuto/vypnuto, které umí číst automatizace i dashboardy.
- 🪶 **Žádné závislosti navíc** — drobný WebSocket klient nad `aiohttp`, nic se
  neinstaluje ani nerozbíjí při aktualizacích.
- 🛡️ **Do sítě Matter se nic nezapisuje** — integrace poslouchá události Matteru
  a nikdy neposílá ovladači žádný příkaz Matteru ani nemění jeho spárování.
  Propojení působí jen přes běžné služby Home Assistantu na entitách, které
  zvolíte.

## Jak to funguje

```
kolečko / dvoutlačítko BILRESA ──Matter/Thread──▶ Matter Server ──▶ tato integrace
                                                                    ├▶ event entity, číselník a tlačítko
                                                                    ├▶ ikea_bilresa_event a spouštěče
                                                                    └▶ ovládací propojení ──▶ služby Home Assistantu
                                                                         (světla, scény, skripty, …)
```

Integrace běžně znovu použije existující subscription klienta `MatterClient` z
jádrové Matter integrace. Kompatibilní fallback se připojí k WebSocketu Matter
Serveru (výchozí `ws://core-matter-server:5580/ws`), pošle jednou
`start_listening` a dekóduje události clusteru `Switch` (`0x003B`) pro každý
nalezený BILRESA uzel.

Každé kolečko má **3 kanály**, každý = 3 Matter Switch endpointy:

| Role | Matter schopnosti |
|------|-------------------|
| Otáčení ↑ / ↓ | MomentarySwitch + Release + MultiPress, `MultiPressMax = 18` |
| Tlačítko (stisk) | navíc LongPress, `MultiPressMax = 3` |

Dvoutlačítko E2489 má dva samostatné tlačítkové endpointy bez označení kanálu.
Každý vytvoří vlastní event entitu Tlačítko 1/2 a podporuje jednoduchý stisk,
dvojitý stisk, podržení a uvolnění (`MultiPressMax = 2`).

Ovládací propojení běží uvnitř Home Assistantu: propojení přečte rozpoznané
gesto a zavolá služby Home Assistantu, například `light.turn_on`, `scene.turn_on`
nebo `script.turn_on`, na zvolené entitě. Přes Matter integrace nic neposílá.

## Požadavky

- Home Assistant **2026.8** nebo novější.
- Add-on **Matter Server** (nebo externí Matter Server) s BILRESA kolečky už
  spárovanými do Matteru a funkčními.
- Nakonfigurovaná jádrová integrace **Matter** (slouží k automatickému zjištění
  URL serveru; BILRESA může být spárovaná do Home Assistantu i Apple Home).
- Síť Thread dostupná pro integraci Matter, protože BILRESA je zařízení Matter
  přes Thread.

### Kompatibilita

Integrace funguje s BILRESA zařízeními, která Home Assistant už vidí přes svou
integraci **Matter**. Záleží na tom, jak se *ovladač* dostane do Home
Assistantu, a to je oddělené od toho, co *ovládá*.

| Použití | Stav | Doklad |
|---|---|---|
| Kolečko (E2490) a dvoutlačítko (E2489) spárované s Matter Serverem a jádrovou integrací Matter | **Podporováno** | Integrace odebírá proud událostí jádrového klienta Matter (`matter` je závislost v `manifest.json`). Zaznamenané hardwarové běhy na firmwaru 1.9.15 šly touto cestou ([HARDWARE_TEST.md](docs/HARDWARE_TEST.md), [DEVICE_REFERENCE.md](docs/DEVICE_REFERENCE.md)); ověření některých gest ještě chybí. |
| Pasivní WebSocket k Matter Serveru, záloha, když API jádrového klienta není k dispozici | **Podporováno v kódu, na hardwaru neověřeno** | Body kontrolního seznamu pro zálohu v [HARDWARE_TEST.md](docs/HARDWARE_TEST.md) jsou otevřené. |
| Ovladač spárovaný přes **ZHA** | **Nepodporováno** | Integrace nemá žádnou cestu přes ZHA; čte jen události Matteru. |
| Ovladač spárovaný přes **Zigbee2MQTT** | **Nepodporováno** | Neexistuje žádná cesta přes MQTT ani Zigbee2MQTT. |
| Světla a další entity na **ZHA nebo Zigbee2MQTT** jako *cíle* propojení | **Podporováno z návrhu, u skupin neověřeno** | Cílem je jakákoli entita Home Assistantu podporované domény, bez ohledu na integraci, která ji poskytuje. Opravy pro světelné skupiny Zigbee2MQTT jsou v testovacích kandidátech; potvrzení od zadavatele chybí ([issue #9](https://github.com/Vituhlos/ha-ikea-bilresa/issues/9)). |
| Ovladač spárovaný i s jiným řadičem Matteru (například Apple Home) | **Neověřeno** | Zařízení Matter lze spárovat do více fabric ([DEVICE_REFERENCE.md](docs/DEVICE_REFERENCE.md)); s touto integrací to testováno nebylo. |

„Podporováno“ znamená, že to ukazuje kód a zaznamenané běhy, ne že je každé gesto
a nastavení ověřené.

## Instalace

### HACS (doporučeno)

[![Otevře váš Home Assistant a zobrazí tento repozitář v HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Vituhlos&repository=ha-ikea-bilresa&category=integration)

Nebo ručně:

1. HACS → ⋮ → **Vlastní repozitáře** → přidejte
   `https://github.com/Vituhlos/ha-ikea-bilresa`, kategorie **Integration**.
2. Nainstalujte **IKEA BILRESA**.
3. **Restartujte Home Assistant.**

Integrace zatím není ve výchozím katalogu HACS — výše uvedený krok s vlastním
repozitářem je potřeba. Přechod z 0.5.x obsahuje breaking changes; přečtěte si
[CHANGELOG.md](CHANGELOG.md) a nejdřív udělejte zálohu.

### Ručně

Zkopírujte složku `custom_components/ikea_bilresa/` do
`config/custom_components/` v Home Assistantu a restartujte.

## Nastavení

**Nastavení → Zařízení a služby → Přidat integraci → IKEA BILRESA.**
Potvrďte předvyplněnou URL Matter Serveru (měňte ji, jen pokud běží jinde). Integrace
najde všechna podporovaná zařízení BILRESA automaticky. Kolečko dostane event
entitu na každý kanál, dvoutlačítko na každé fyzické tlačítko.

### Panel BILRESA

Home Assistant přidá do postranního menu položku **IKEA BILRESA** (jen pro
administrátory; jako každý panel ji lze skrýt). Tady vše vidíte a nastavíte bez
YAML.

- **Přehled.** Každé kolečko a dvoutlačítko, které integrace našla, s názvem,
  oblastí a časem poslední aktivity. Pruh upozorní, když je Matter odpojený,
  když se zastavily živé aktualizace nebo když propojení míří na entitu, která už
  neexistuje.
- **Stránka zařízení** má tři záložky. *Kanály* (u dvoutlačítka *Tlačítka*)
  vypíše každý kanál s tím, co dělá které gesto a na čem, a tlačítko **Upravit
  propojení**; přepínač u kanálu ho vypne a vypnutý kanál nedělá nic, dokud ho
  znovu nezapnete. *Živý test* ukazuje každé gesto, jak je rozpoznáno, a akci,
  kterou poslalo svému cíli, ale jen dokud je záložka otevřená. *Diagnostika* je
  pohled jen pro čtení na dostupnost, spojení s Matterem, použitý zdroj událostí
  a propojení se zařízením; soukromé identifikátory Matteru se neukazují.
- **Editor** má pro každé gesto jednu část: otáčení (jen kolečko), krátký stisk,
  dvojitý stisk, trojitý stisk (jen kolečko) a podržení. Každá ukazuje akci a
  cíl. Krátký stisk navíc obsahuje **odezvu**: počkat na jednoduchý, dvojitý či
  trojitý stisk, spustit po prvním krátkém uvolnění, nebo spustit už při prvním
  stisku (viz [ovládací propojení](#gui-ovládací-propojení-ovládání-bez-yaml)).
  Odezva, která nějaké gesto vylučuje, to řekne v jeho části, místo aby selhalo
  uložení. **Uložit propojení** zkontroluje pole a označí ta, která odmítne;
  **Zahodit** zavře needitovaný editor hned a při neuložených změnách chce druhý
  stisk; **Smazat propojení** žádá potvrzení. Pokud se propojení mezitím změnilo
  jinde, panel to řekne a nepřepíše ho.
- **Číselník.** Každý kanál kolečka má číselnou entitu (1 až 100), kterou otáčení
  posouvá. Část *Číselník* nastavuje, o kolik ji posune jedno cvaknutí a kolik
  přidá rychlejší otáčení; na propojení to nemá vliv.
- **Jazyk a téma.** Panel mluví jazykem zvoleným v profilu každého uživatele
  (česky nebo anglicky). Téma, kvůli kterému jsou hlavní tlačítka nečitelná,
  může nastavit dvě proměnné; viz [Řešení potíží](#řešení-potíží).

Panel lze použít místo nativního průvodce níže i spolu s ním; oba zapisují stejná
propojení.

### GUI ovládací propojení (ovládání bez YAML)

Nechcete psát automatizace? V [panelu](#panel-bilresa), nebo u položky **IKEA
BILRESA** (Nastavení → Zařízení a služby) přes **＋ Přidat → Ovládací propojení**,
vyberte:

- výchozí profil (světlo, média, kryt, klimatizace, scény nebo vlastní), případně
  zkopírujte existující propojení jako výchozí nastavení,
- **Kolečko** a **Kanál**,
- **cílovou entitu**, kterou otáčení ovládá,
- **Změnu jasu na jedno cvaknutí** (%), **Minimální jas** (%, `0` = otočením dolů lze
  světlo vypnout) a **Přechod** (s),
- **akci jednoduchého stisku** (přepnout / zapnout / vypnout / nic) a volitelný
  **cíl tlačítka** — takže stisk může ovládat *jinou* entitu než stmívané světlo
  (např. stmíváš žárovku, ale přepínáš její Shelly ve vypínači). Cílem stisku,
  dvojitého či trojitého stisku nebo podržení může být i **scéna** nebo
  **skript** (viz [Scény a skripty](#scény-a-skripty-jako-cíle) níže) a každé z
  těchto gest má vlastní **akci** na svém cíli: přepnout, zapnout nebo vypnout,
- **odezvu tlačítka**: okamžitě při prvním stisku, rychle po krátkém uvolnění,
  nebo přesné rozpoznání jednoho, dvou či tří stisků,
- volitelný seřazený seznam **scén**, které jednoduché stisky postupně aktivují
  (má přednost před běžnou akcí jednoduchého stisku),
- **akci při podržení**: přepnout entitu, plynule měnit cíl otáčení, nebo nic.
  Rampování začne nahoru a po každém dokončeném podržení obrátí směr, protože
  událost dlouhého stisku BILRESY sama žádný směr nenese.

Pro nejnižší latenci přímého ovládání zvolte **Okamžitě při stisku**. Protože při
prvním eventu ještě nelze poznat, zda vznikne dvojitý stisk nebo podržení, lze tento
režim uložit jen tehdy, když jsou tyto samostatné akce vypnuté. **Rychle po
uvolnění** reaguje po prvním krátkém uvolnění a zůstává bezpečné pro běžné
podržení; rozpoznání více stisků čeká na dokončovací událost BILRESY. Existující
propojení bez uložené volby zachovají dosavadní čekání, dokud režim výslovně
nezměníte. Vypnutý kanál nespustí propojení v žádném z těchto režimů.
Veřejné event entity a spouštěče přesně rozlišují jeden, dva a
tři stisky ve všech režimech.

Integrace pak to světlo stmívá v reálném čase. Přidejte si klidně víc propojení —
jedno na kanál kolečka — takže to škáluje na libovolný počet koleček bez YAML.
Když cíl chybí nebo je `unknown` či `unavailable`, propojení neposílá žádný
příkaz (scénu nebo skript ve stavu `unknown`, například dosud nespuštěnou scénu,
ale spustí); rampování se bezpečně zastaví a další akce po návratu vyjde ze skutečného
stavu entity. Otočení nahoru z vypnutého světla začne na nastaveném minimu
(nebo prvním použitelném kroku, když je minimum nula). Externí změna v HA
přenastaví výchozí bod dalšího otočení; obrácení směru během přechodu pokračuje
z poslední požadované hodnoty.

#### Scény a skripty jako cíle

Každé gesto stisku (jednoduchý, dvojitý, trojitý stisk a podržení) provede jednu
akci na jednom cíli. Akce znamená u různých cílů něco jiného:

| Cíl | Přepnout | Zapnout | Vypnout |
|---|---|---|---|
| světlo, vypínač | přepne | zapne | vypne |
| **skript** | spustí ho, nebo zastaví, když běží | **spustí ho** | **zastaví ho** |
| **scéna** | spustí ji | spustí ji | nejde (při ukládání se odmítne) |

Panel pojmenuje volby podle cíle (u skriptu: *Spustit skript*, *Zastavit
skript*, *Přepnout skript*) a když vyberete skript nebo scénu, předvybere
*Spustit*. Propojení uložené před touto volbou nemá akci uloženou a přepíná dál,
jako vždy.

**Spustit skript** spustí skript a předá mu, které gesto ho spustilo, v
proměnných `gesture` (`short_press`, `double_press`, `triple_press` nebo
`hold`), `presses`, `channel`, `endpoint` a `device`, takže jeden skript může
obsloužit víc tlačítek. Přepnutí a zastavení proměnné předat nemohou. Skript,
který už běží, se řídí svým
[režimem](https://www.home-assistant.io/docs/script/#script-modes) (ve výchozím
stavu se druhé spuštění ignoruje s varováním).

```yaml
script:
  bilresa_lights:
    mode: restart
    sequence:
      - action: light.toggle
        target:
          entity_id: >-
            {{ 'light.hall' if gesture == 'double_press' else 'light.kitchen' }}
```

Vyberte tento skript jako cíl krátkého i dvojitého stisku s akcí *Spustit
skript*; jedním přepnete kuchyňské světlo, druhým chodbové. Scéna, která nebyla
nikdy aktivována, hlásí stav `unknown` a přesto se spustí.

U dvoutlačítka stejný průvodce nejdřív vybere Tlačítko 1 nebo Tlačítko 2 a pak
zobrazí jen podporované akce: nezávislý cíl jednoduchého/dvojitého stisku a
podržení/uvolnění. Nejsou tam pole pro otáčení, scény ani trojitý stisk. Podržení
může směr jasu střídat nebo ho držet pevně nahoru/dolů, takže dvě tlačítka mohou
pro jedno světlo vytvořit softwarový pár ve stylu DIRIGERA.

Zapnuté zrychlení vychází z počtu dekódovaných cvaknutí za uplynulý čas, ne z
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
akce; atribut `event_type` (a `notches` / `presses`) říká, co se stalo. Používejte ji
jako hlavní spouštěč automatizace. Entity používají nativní button event device
class Home Assistantu; kompatibilní doménová událost navíc obsahuje registry
`device_id`, pokud je dostupné.

### Entity číselníku a tlačítka

Kromě event entit má každý kanál kolečka ještě dvě, nezávislé na jakémkoli
propojení:

| Entita | Co to je |
|---|---|
| `number` *Číselník* | Posuvník od 1 do 100. Otáčení kolečka ho posouvá o *Změnu číselníku na cvaknutí* z panelu (s volitelným zrychlením); hodnota se zachová přes restart. Hodí se ke čtení kolečka v automatizacích a dashboardech, nebo si ji nastavíte sami. |
| `switch` *Tlačítko* | Přepínač zapnuto/vypnuto, který překlopí každý jednoduchý stisk tlačítka kanálu. Jen si pamatuje stav; na zařízení se nic nepřikazuje. Dvojitý stisk, trojitý stisk a podržení se ho netýkají, takže zůstávají volné pro jiné využití. |

### Přehled událostí

| `event_type` | Význam | Atribut navíc |
|--------------|--------|---------------|
| `rotate_up` | Otočeno nahoru o *N* cvaknutí | `notches` |
| `rotate_down` | Otočeno dolů o *N* cvaknutí | `notches` |
| `press` | Jednoduchý stisk | `presses` = 1 |
| `double_press` | Dvojitý stisk | `presses` = 2 |
| `triple_press` | Trojitý stisk | `presses` = 3 |
| `hold` | Podržení tlačítka | — |
| `release` | Uvolnění po podržení | — |

### Spouštěče

Integrace nabízí jeden spouštěč automatizace na každé gesto. V editoru
automatizací vyberte jako cíl kolečko (nebo některou z jeho entit `Kanál`) a zvolte
spouštěč:

| Spouštěč | Spustí se, když |
|----------|-----------------|
| `ikea_bilresa.rotated_up` | je kanál otočen nahoru |
| `ikea_bilresa.rotated_down` | je kanál otočen dolů |
| `ikea_bilresa.pressed` | je tlačítko stisknuto jednou |
| `ikea_bilresa.double_pressed` | je tlačítko stisknuto dvakrát |
| `ikea_bilresa.triple_pressed` | je tlačítko kolečka stisknuto třikrát |
| `ikea_bilresa.held` | je tlačítko dlouze drženo |
| `ikea_bilresa.released` | je tlačítko uvolněno po dlouhém stisknutí |

```yaml
triggers:
  - trigger: ikea_bilresa.rotated_up
    target:
      entity_id: event.bilresa_scroll_wheel_channel_1
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

Cíl, který pojmenuje celé zařízení, pokrývá všechny kanály daného kolečka.
Dvoutlačítko nemá otáčení ani trojité stisknutí, takže tyto dva spouštěče se
pro něj nikdy nespustí.

> **Přechod z 0.5.x nebo dřívějšího prerelease 0.6.0:** dřívější *spouštěče
> zařízení* („Kanál 1 otočeno nahoru" na stránce zařízení) byly odstraněny. Od
> Home Assistantu 2026.8 patří zařízení jediné integraci a spouštěč zařízení
> funguje jen na zařízení, které jeho integrace vlastní. Automatizace, které
> nějaký stále používají, najdete v **Nastavení → Systém → Opravy**; nahraďte
> v nich spouštěč odpovídajícím spouštěčem z tabulky výše.

### Příklady automatizací

**Plynulé stmívání** — posuňte jas o počet cvaknutí, s `transition`, aby světlo mezi
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

Zduplikujte s `rotate_down` a záporným krokem pro ztlumení a přidejte spouštěč
`press` volající `light.toggle` pro tlačítko.

### Blueprint: plynulé stmívání

Pro nastavení přes automatizace je tu blueprint, který jedním kanálem stmívá
jedno světlo: otáčení mění jas podle počtu cvaknutí (s přechodem, který
překlenuje dávkové aktualizace kolečka) a jednoduchý stisk světlo přepne.
Vstupy jsou event entita kanálu, světlo, krok jasu na cvaknutí a přechod.

[![Otevřít vaši instanci Home Assistantu s importem tohoto blueprintu.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FVituhlos%2Fha-ikea-bilresa%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fikea_bilresa%2Fsmooth_dimming.yaml)

Ovládací propojení bez YAML [nepotřebují](#gui-ovládací-propojení-ovládání-bez-yaml)
žádnou automatizaci; blueprint použijte, když ji chcete.

### Sběrnicová událost `ikea_bilresa_event`

Každá akce se navíc vypálí na sběrnici jako `ikea_bilresa_event` — hodí se pro
jednu automatizaci obsluhující víc koleček. Pole: `node_id`, `wheel_name`,
`channel`, `endpoint_id`, `type` (`rotate` / `press` / `hold` / `release` /
`short_release`), `direction` (`up` / `down`), `notches`, `presses`.

```yaml
triggers:
  - trigger: event
    event_type: ikea_bilresa_event
    event_data:
      type: rotate
```

### Okamžité akce po krátkém uvolnění

Automatizace, která má zareagovat hned po uvolnění krátkého stisku tlačítka,
naslouchá `ikea_bilresa_event` s `type: short_release`, filtrované podle
`node_id` a `channel` vašeho kolečka. Nefiltrujte podle `presses: 1`: konečný
počet stisků v okamžiku uvolnění ještě není známý.

```yaml
triggers:
  - trigger: event
    event_type: ikea_bilresa_event
    event_data:
      node_id: 12  # Nahraďte Matter node ID svého kolečka.
      channel: 1
      type: short_release
```

Tato událost existuje jen na sběrnici a přijde při každém krátkém uvolnění,
včetně uvolnění uvnitř dvojitého nebo trojitého stisku. Dokončená událost
`press` s konečným počtem přijde i nadále. Spouštěč dokončeného jednoduchého
stisku v automatizaci nahraďte, nepřidávejte druhý spouštěč pro stejnou akci,
jinak se spustí dvakrát. Samostatná akce na dvojitý stisk může tu časnou akci
přebít, ale mezistav bude vidět. Dlouhé podržení tuto událost nevysílá. Event
entity, spouštěče `ikea_bilresa.*` a přímé vazby na světla se chovají dál podle
dokončeného gesta; přímá vazba, která má reagovat už při uvolnění, k tomu má
vlastní nastavení **Odezva tlačítka → Rychle po uvolnění**. Vypnutý kanál
nevysílá ani `short_release`.

Dvoutlačítko E2489 nemá kanál (`channel` je prázdné), jeho dvě tlačítka proto
rozlišujte podle `endpoint_id`. Při více než dvou stiscích za sebou přijde
`short_release` pro každé nahlášené uvolnění, ale žádné dokončené `press` už
nenásleduje (zařízení ukončí sekvenci s nulovým počtem).

## Více koleček

Vše je klíčované podle Matter uzlu a endpointu, takže **libovolný počet koleček**
funguje najednou bez konfigurace — každé se najde a dostane vlastní zařízení,
entity a události. Pole `node_id` / `wheel_name` / `channel` je v automatizacích
rozliší.

## Řešení potíží

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

## Plán

Co obsahuje které vydání, je v [CHANGELOG](CHANGELOG.md). Tady je, kam projekt
míří; nic z toho není slib ani termín a každá položka ještě potřebuje své kontroly
v [docs/HARDWARE_TEST.md](docs/HARDWARE_TEST.md).

**Stabilní (v0.6.1).** Event entity, spouštěče automatizací, entity číselníku a
tlačítka, ovládací propojení s několika režimy otáčení, zrychlením, procházením
scén a plynulou změnou při podržení, dvoutlačítko, panel BILRESA, využití
Matter klienta Home Assistantu s WebSocketem jen pro čtení jako zálohou, česky a
anglicky.

**V předběžném vydání, bez ověření na hardwaru** (až `v0.7.0-rc.4`). Přepracovaný
panel a jeho editor propojení, událost `short_release`, opravy světelných skupin
Zigbee2MQTT, vypnuté kanály, které mlčí, a scény a skripty jako cíle gest.

**Plánováno, zhruba v tomto pořadí.**

- Vlastní akce pro každé gesto, skripty dostanou informaci, které gesto je
  spustilo (v revizi).
- Podržení s akcí při začátku a jinou při konci, například pro spuštění skriptu,
  který cokoli mění, dokud držíte, a zastavení při uvolnění.
- Plné akce Home Assistantu (libovolná služba s daty) pro gesto, místo jediné
  entity.
- Režim otáčení, který prochází seznamem scén.
- Zbývající hardwarové ověření a potom ikona značky v `home-assistant/brands` a
  výchozí obchod HACS.

## Omezení

- Kolečko má vestavěnou ~500ms–1s anti-flood brzdu mezi dávkami cvaknutí, takže se
  to *blíží* pocitu DIRIGERA, ale není to úplně analogově spojité. Odpovídající
  `transition` na světle dávky přemostí do plynulého náběhu.
- Cílová světla jdou přes Home Assistant (ne přímý Matter/Zigbee bind), což přidá
  malou, obvykle nepostřehnutelnou LAN latenci.
- Gesto působí na jednu entitu, nebo spustí jednu scénu či jeden skript. Pro víc
  věcí naráz ho zaměřte na skript (nebo scénu), který je udělá; skript spuštěný
  akcí *Spustit skript* se navíc dozví, které gesto ho spustilo.
- Panel je pro administrátory; ostatní uživatelé ho nevidí. Event entity,
  spouštěče a propojení na něm nezávisí.

## Komunitní nástroje

Tyto nástroje vytvořili jiní lidé. Nejsou součástí integrace, ta na nich nezávisí
a nic jim neposílá; integrace je neudržuje ani nedoporučuje, řiďte se podmínkami
jednotlivých projektů.

- **[Somrig Inlay Sheet Builder](https://bilresa.marcel1.com/)** — webový nástroj od člena komunity pro
  návrh vložek (štítků) pro spínače. Podle jeho autora umí vytvořit i modely krytů
  pro 3D tisk. Panel na něj odkazuje ze stránky zařízení.

## Přispívání

Issues a pull requesty jsou vítány — [CONTRIBUTING.md](CONTRIBUTING.md)
vysvětluje, jak nahlásit chybu nebo navrhnout funkci (pro obojí jsou připravené
formuláře), jak spustit kontroly a kdy je potřeba hardwarové ověření. Hlášení
bezpečnostních problémů řeší [SECURITY.md](SECURITY.md).

Pro vývojáře a agenty: aktuální stav implementace, úroveň ověření a prioritní
backlog jsou v [PROJECT_STATUS.md](PROJECT_STATUS.md), kanonický postup vývoje
v [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) a plánovací dokumenty v
[docs/ROADMAP.md](docs/ROADMAP.md) a
[docs/ROADMAP_BUTTON.md](docs/ROADMAP_BUTTON.md).

## Licence

[MIT](LICENSE) © 2026 Vituhlos
