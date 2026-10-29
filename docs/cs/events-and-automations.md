# Události, entity a automatizace

[README](../../README.cs.md) · [Všichni průvodci](../README.md) · [English](../en/events-and-automations.md) · **Čeština**

Tento průvodce popisuje současné chování integrace. Funkce nad rámec posledního
vydání jsou označené v [PROJECT_STATUS.md](../../PROJECT_STATUS.md).

## Event entity

Každý kanál kolečka se stane `event` entitou, např.
`event.bilresa_scroll_wheel_channel_1`. Id vychází z názvu zařízení, takže u vás
bude jiné, pokud jste zařízení přejmenovali nebo máte víc koleček: najdete ho v
**Nastavení → Zařízení a služby → Entity** a id i `light.example` v příkladech
níže nahraďte vlastními.

Stav entity je časové razítko poslední
akce; atribut `event_type` (a `notches` / `presses`) říká, co se stalo. Používejte ji
jako hlavní spouštěč automatizace. Entity používají nativní button event device
class Home Assistantu; kompatibilní doménová událost navíc obsahuje registry
`device_id`, pokud je dostupné.

## Entity číselníku a tlačítka

Kromě event entit má každý kanál kolečka ještě dvě, nezávislé na jakémkoli
propojení:

| Entita | Co to je |
|---|---|
| `number` *Číselník* | Posuvník od 1 do 100. Otáčení kolečka ho posouvá o *Změnu číselníku na cvaknutí* z panelu (s volitelným zrychlením); hodnota se zachová přes restart. Hodí se ke čtení kolečka v automatizacích a dashboardech, nebo si ji nastavíte sami. |
| `switch` *Tlačítko* | Přepínač zapnuto/vypnuto, který překlopí každý jednoduchý stisk tlačítka kanálu. Jen si pamatuje stav; na zařízení se nic nepřikazuje. Dvojitý stisk, trojitý stisk a podržení se ho netýkají, takže zůstávají volné pro jiné využití. |

## Přehled událostí

| `event_type` | Význam | Atribut navíc |
|--------------|--------|---------------|
| `rotate_up` | Otočeno nahoru o *N* cvaknutí | `notches` |
| `rotate_down` | Otočeno dolů o *N* cvaknutí | `notches` |
| `press` | Jednoduchý stisk | `presses` = 1 |
| `double_press` | Dvojitý stisk | `presses` = 2 |
| `triple_press` | Trojitý stisk | `presses` = 3 |
| `hold` | Podržení tlačítka | — |
| `release` | Uvolnění po podržení | — |

## Spouštěče

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
      entity_id: light.example
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

## Příklady automatizací

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
      entity_id: light.example
    data:
      brightness_step_pct: "{{ trigger.to_state.attributes.notches * 3 }}"
      transition: 1
mode: parallel
max: 20
```

Zduplikujte s `rotate_down` a záporným krokem pro ztlumení a přidejte spouštěč
`press` volající `light.toggle` pro tlačítko.

## Blueprint: plynulé stmívání

Pro nastavení přes automatizace je tu blueprint, který jedním kanálem stmívá
jedno světlo: otáčení mění jas podle počtu cvaknutí (s přechodem, který
překlenuje dávkové aktualizace kolečka) a jednoduchý stisk světlo přepne.
Vstupy jsou event entita kanálu, světlo, krok jasu na cvaknutí a přechod.

[![Otevřít vaši instanci Home Assistantu s importem tohoto blueprintu.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FVituhlos%2Fha-ikea-bilresa%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fikea_bilresa%2Fsmooth_dimming.yaml)

Ovládací propojení bez YAML [nepotřebují](bindings.md#gui-ovládací-propojení-ovládání-bez-yaml)
žádnou automatizaci; blueprint použijte, když ji chcete.

## Sběrnicová událost `ikea_bilresa_event`

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

## Okamžité akce po krátkém uvolnění

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

### Recept: změna barvy při uvolnění, bílá při dvojitém stisku

Vyžaduje sběrnicovou událost `short_release`, která existuje od **0.6.2**
(recept byl otestován s v0.6.2-rc.2; verze 0.6.1 událost nemá).
Světlo nebo skupina světel musí podporovat barvu i teplotu bílé.
V [kompletním YAML příkladu v anglickém průvodci](../en/events-and-automations.md#recipe-change-colour-on-release-restore-white-on-double-click)
nahraďte všechny výskyty `light.example` a nastavte `node_id` a `channel`
ve všech třech spouštěčích podle svého kolečka. Nejsou potřeba žádné
pomocné entity ani skripty.

Každé krátké uvolnění vypnuté světlo rozsvítí, nebo u zapnutého světla změní
barvu na plně sytou. Odstín se posune o náhodných 90–270 stupňů modulo 360,
aby se lišil od právě hlášeného odstínu. Dokončený dvojitý stisk obnoví bílou
3000 K; podržení světlo vypne.

Vazbu pro stmívání otáčením můžete ponechat, ale vypněte v ní akce tlačítka
a podržení i překrývající se automatizace. Uvolnění během dvojitého či
trojitého stisku také mění barvu: přechodné barvy před obnovením bílé jsou
očekávané. Režim `queued` zachová pořadí akcí, ale rychlá uvolnění mohou číst
stejný zastaralý stav, než žárovka nahlásí nový odstín; odlišná barva při
každém rychlém uvolnění proto není zaručena. Filtr `presses: 1` je záměrně
vynechán.

Příklad vychází z funkční automatizace otestované na Home Assistant Green,
HA 2026.10.4, kolečku E2490 (P2.0, firmware 1.9.15) a třech žárovkách
KAJPLATS přes Matter/Thread. Krátká uvolnění byla zaznamenána před dokončenými
jednoduchými, dvojitými i trojitými stisky. Dřívější občasné vynechávání
stisků přetrvalo; recept nedokáže obnovit události, které integrace neobdrží.
Viz [pozorování z hardwarového testu v PR #5](https://github.com/Vituhlos/ha-ikea-bilresa/pull/5#issuecomment-6452179129).

## Více koleček

Vše je klíčované podle Matter uzlu a endpointu, takže **libovolný počet koleček**
funguje najednou bez konfigurace — každé se najde a dostane vlastní zařízení,
entity a události. Pole `node_id` / `wheel_name` / `channel` je v automatizacích
rozliší.
