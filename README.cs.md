# IKEA BILRESA pro Home Assistant

[English](README.md) · **Čeština**

[![release](https://img.shields.io/github/v/release/Vituhlos/ha-ikea-bilresa)](https://github.com/Vituhlos/ha-ikea-bilresa/releases)
[![CI](https://github.com/Vituhlos/ha-ikea-bilresa/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Vituhlos/ha-ikea-bilresa/actions/workflows/ci.yml)
[![stars](https://img.shields.io/github/stars/Vituhlos/ha-ikea-bilresa)](https://github.com/Vituhlos/ha-ikea-bilresa/stargazers)
[![license](https://img.shields.io/github/license/Vituhlos/ha-ikea-bilresa)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/use/custom_repositories/)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.8.0%2B-41BDF5)

Responzivní ovládání s konfigurací v GUI pro **kolečko i dvoutlačítko IKEA
BILRESA** (Matter přes Thread) v Home Assistantu.

Kolečko hlásí události `MultiPressOngoing` v reálném čase, takže Home Assistant
může reagovat už během otáčení, ne až po zastavení. Ovladač ale stále posílá
cvaknutí v dávkách, takže jde o svižné stupňovité ovládání, nikoli o skutečně
analogové plynulé posouvání.

> **Stabilní vydání:** poslední stabilní vydání je **v0.6.1**. Řada 0.6 přidala dvoutlačítko, panel BILRESA,
> další cíle propojení a spouštěč automatizace pro každé gesto. Vyžaduje Home
> Assistant 2026.8 nebo novější a nahrazuje dřívější spouštěče zařízení: před
> přechodem z 0.5.x udělejte zálohu a přečtěte si poznámky k přechodu v
> [CHANGELOGu](CHANGELOG.md).
>
> **Testovací kandidát:** předběžné vydání **v0.7.0-rc.5** má přepracovaný panel
> a editor propojení, které stabilní vydání nemá, akci pro každé gesto, opravu
> zamrzání při Matter aktualizacích (GitHub #21) a opravy z `v0.6.2-rc.2`
> (světelné skupiny Zigbee2MQTT, událost `short_release`, vypnuté kanály).
> Není ověřené na hardwaru a některé kombinace zařízení a gest stále čekají na
> ověření; viz [hardwarový kontrolní seznam](docs/HARDWARE_TEST.md).

Pokud vám tato integrace šetří čas, můžete podpořit její vývoj. Je to zcela
dobrovolné.

<a href="https://buymeacoffee.com/Vituhlos"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" height="40"></a>

## Přehled

| | |
|---|---|
| ⚡ **Reakce v reálném čase** | Reaguje na `MultiPressOngoing` už během otáčení, ne až po zastavení. |
| 🖥️ **Panel v postranním menu** | Přehled zařízení, editor s jednou částí na každé gesto, živý test a diagnostika jen pro čtení. Česky a anglicky. |
| 🎚️ **Ovládací propojení bez YAML** | Otáčení stmívá světlo nebo mění hlasitost, polohu krytu, teplotu či ventilátor; stisk, dvojitý stisk, trojitý stisk nebo podržení přepne, zapne či vypne, nebo spustí **scénu** či **skript**. |
| 🎛️ **Události a spouštěče** | Event entity, spouštěč automatizace pro každé gesto, sběrnicová událost a okamžité krátké uvolnění pro rychlé automatizace. |
| 📟 **Entity číselníku a tlačítka** | Každý kanál kolečka má navíc číselník 1–100 a přepínač zapnuto/vypnuto pro automatizace a dashboardy. |
| 🧭 **Libovolný počet zařízení** | Kolečka (E2490) a dvoutlačítka (E2489) se najdou automaticky. |
| 🛡️ **Do Matteru se nic nezapisuje** | Integrace poslouchá události Matteru a nikdy neposílá ovladači příkaz Matteru ani nemění jeho spárování. |

## Rychlý start

1. **Zkontrolujte**, že máte Home Assistant 2026.8 nebo novější, Matter Server s
   už spárovaným BILRESA a síť Thread, kterou integrace Matter dosáhne.
2. **Nainstalujte** přes HACS: přidejte `https://github.com/Vituhlos/ha-ikea-bilresa`
   jako vlastní repozitář (kategorie *Integrace*), nainstalujte **IKEA BILRESA** a
   restartujte Home Assistant.
   [![Otevřít vaši instanci Home Assistantu a tento repozitář v obchodě HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Vituhlos&repository=ha-ikea-bilresa&category=integration)
3. **Přidejte integraci** v **Nastavení → Zařízení a služby → Přidat integraci →
   IKEA BILRESA**, pak v postranním menu otevřete **IKEA BILRESA**, vyberte
   zařízení a u kanálu stiskněte **Upravit propojení** (ve stabilní verzi v0.6.1 nabízí kanál
   bez propojení místo toho **Přidat propojení**).

Podrobnosti a postup, když něco nefunguje, jsou v průvodcích níže.

## Funguje s

- ✅ Kolečko (E2490) nebo dvoutlačítko (E2489) spárované s Matter Serverem a s
  jádrovou integrací Matter v Home Assistantu.
- ❌ Ovladač spárovaný přes ZHA nebo Zigbee2MQTT. Světla a další entity na ZHA
  nebo Zigbee2MQTT mohou být stále *cíli* propojení.

Celá tabulka s doklady ke každému případu je v
[Začínáme](docs/cs/getting-started.md#kompatibilita).

## Dokumentace

| Průvodce | Odpovídá na |
|---|---|
| [Začínáme](docs/cs/getting-started.md) | Co potřebuji, které sestavy fungují, jak to nainstaluji a nastavím? |
| [Panel BILRESA](docs/cs/panel.md) | Co panel ukazuje a jak upravím propojení, číselník nebo kanál? |
| [Ovládací propojení](docs/cs/bindings.md) | Jak přiměju gesto něco udělat, včetně spuštění scény nebo skriptu? |
| [Události, entity a automatizace](docs/cs/events-and-automations.md) | Jaké události, entity a spouštěče existují a jak je použiji v automatizacích? |
| [Řešení potíží](docs/cs/troubleshooting.md) | Nic se neděje, nebo je tlačítko v mém tématu nečitelné? |
| [Jak to funguje, omezení a plán](docs/cs/how-it-works.md) | Proč to vzniklo, jak to funguje, jaká jsou omezení a co se plánuje? |

[CHANGELOG](CHANGELOG.md) uvádí každé vydání a
[docs/HARDWARE_TEST.md](docs/HARDWARE_TEST.md) je aktuální hardwarový kontrolní
seznam. Všichni průvodci jsou i v angličtině; viz [všichni průvodci](docs/README.md).

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
