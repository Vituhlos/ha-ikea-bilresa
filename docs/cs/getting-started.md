# Začínáme

[README](../../README.cs.md) · [Všichni průvodci](../README.md) · [English](../en/getting-started.md) · **Čeština**

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
| Kolečko (E2490) a dvoutlačítko (E2489) spárované s Matter Serverem a jádrovou integrací Matter | **Podporováno** | Integrace odebírá proud událostí jádrového klienta Matter (`matter` je závislost v `manifest.json`). Zaznamenané hardwarové běhy na firmwaru 1.9.15 šly touto cestou ([HARDWARE_TEST.md](../HARDWARE_TEST.md), [DEVICE_REFERENCE.md](../DEVICE_REFERENCE.md)); ověření některých gest ještě chybí. |
| Pasivní WebSocket k Matter Serveru, záloha, když API jádrového klienta není k dispozici | **Podporováno v kódu, na hardwaru neověřeno** | Body kontrolního seznamu pro zálohu v [HARDWARE_TEST.md](../HARDWARE_TEST.md) jsou otevřené. |
| Ovladač spárovaný přes **ZHA** | **Nepodporováno** | Integrace nemá žádnou cestu přes ZHA; čte jen události Matteru. |
| Ovladač spárovaný přes **Zigbee2MQTT** | **Nepodporováno** | Neexistuje žádná cesta přes MQTT ani Zigbee2MQTT. |
| Světla a další entity na **ZHA nebo Zigbee2MQTT** jako *cíle* propojení | **Podporováno z návrhu, u skupin neověřeno** | Cílem je jakákoli entita Home Assistantu podporované domény, bez ohledu na integraci, která ji poskytuje. Opravy pro světelné skupiny Zigbee2MQTT jsou v testovacích kandidátech; potvrzení od zadavatele chybí ([issue #9](https://github.com/Vituhlos/ha-ikea-bilresa/issues/9)). |
| Ovladač spárovaný i s jiným řadičem Matteru (například Apple Home) | **Neověřeno** | Zařízení Matter lze spárovat do více fabric ([DEVICE_REFERENCE.md](../DEVICE_REFERENCE.md)); s touto integrací to testováno nebylo. |

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
[CHANGELOG.md](../../CHANGELOG.md) a nejdřív udělejte zálohu.

### Ručně

Zkopírujte složku `custom_components/ikea_bilresa/` do
`config/custom_components/` v Home Assistantu a restartujte.

## Nastavení

**Nastavení → Zařízení a služby → Přidat integraci → IKEA BILRESA.**
Potvrďte předvyplněnou URL Matter Serveru (měňte ji, jen pokud běží jinde). Integrace
najde všechna podporovaná zařízení BILRESA automaticky. Kolečko dostane event
entitu na každý kanál, dvoutlačítko na každé fyzické tlačítko.

## Další kroky

- V postranním menu otevřete **IKEA BILRESA** a vyberte zařízení: v
  [průvodci panelem](panel.md) je, co tam uvidíte a upravíte.
- Přimějte gesto něco udělat: [ovládací propojení](bindings.md), včetně spuštění
  scény nebo skriptu.
- Použijte gesta ve vlastních automatizacích:
  [události, entity a automatizace](events-and-automations.md).
- Nic se neděje: [řešení potíží](troubleshooting.md).
