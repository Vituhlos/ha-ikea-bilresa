# Jak to funguje, omezení a plán

[README](../../README.cs.md) · [Všichni průvodci](../README.md) · [English](../en/how-it-works.md) · **Čeština**

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

## Plán

Co obsahuje které vydání, je v [CHANGELOG](../../CHANGELOG.md). Tady je, kam projekt
míří; nic z toho není slib ani termín a každá položka ještě potřebuje své kontroly
v [docs/HARDWARE_TEST.md](../HARDWARE_TEST.md).

**Stabilní (v0.6.1).** Event entity, spouštěče automatizací, entity číselníku a
tlačítka, ovládací propojení s několika režimy otáčení, zrychlením, procházením
scén a plynulou změnou při podržení, dvoutlačítko, panel BILRESA, využití
Matter klienta Home Assistantu s WebSocketem jen pro čtení jako zálohou, česky a
anglicky.

**V předběžném vydání, bez ověření na hardwaru** (až `v0.7.0-rc.5`). Přepracovaný
panel a jeho editor propojení, událost `short_release`, opravy světelných skupin
Zigbee2MQTT, vypnuté kanály, které mlčí, scény a skripty jako cíle gest, vlastní
akce pro každé gesto (skripty se dozvědí, které gesto je spustilo) a oprava
zamrzání při Matter aktualizacích.

**Plánováno, zhruba v tomto pořadí.**

- Podržení s akcí při začátku a jinou při konci, například pro spuštění skriptu,
  který cokoli mění, dokud držíte, a zastavení při uvolnění.
- Plné akce Home Assistantu (libovolná služba s daty) pro gesto, místo jediné
  entity.
- Režim otáčení, který prochází seznamem scén.
- Zbývající hardwarové ověření a potom ikona značky v `home-assistant/brands` a
  výchozí obchod HACS.
