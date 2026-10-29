# Ovládací propojení

[README](../../README.cs.md) · [Všichni průvodci](../README.md) · [English](../en/bindings.md) · **Čeština**

Ovládací propojení přiměje jeden kanál kolečka, nebo jedno tlačítko
dvoutlačítka, působit na zvolenou entitu. [Panel](panel.md) a nativní průvodce
níže zapisují stejná propojení.

## GUI ovládací propojení (ovládání bez YAML)

Nechcete psát automatizace? V [panelu](panel.md), nebo u položky **IKEA
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

## Akce podle druhu cíle

Co gesto umí, závisí na cíli, který zvolíte: seznam akcí v panelu ukáže jen to,
co daný druh cíle dokáže provést. Přepnout, zapnout a vypnout existuje pro vše
přepínatelné (světlo, vypínač, ventilátor, zvlhčovač, dálkové ovládání,
klimatizaci, input boolean); ostatní:

| Cíl | Akce |
|---|---|
| **přehrávač** | přehrát / pozastavit, přehrát, pozastavit, zastavit, další skladba, předchozí skladba, hlasitěji, tišeji, ztlumit / zrušit ztlumení, a přepnout, zapnout, vypnout |
| **roleta, vrata (cover)** | přepnout, otevřít, zavřít, zastavit |
| **zámek** | zamknout |
| **vysavač** | spustit, pozastavit, zastavit, vrátit do stanice, najít |
| **ventilátor** | zrychlit, zpomalit, a přepnout, zapnout, vypnout |
| **tlačítko, input button** | stisknout tlačítko |
| **automatizace** | spustit automatizaci |
| **input select, select** | další, předchozí, první, poslední možnost |
| **input number** | zvýšit, snížit (o krok čísla) |
| **ventil** | zavřít, zastavit |
| **siréna** | vypnout |
| skript, scéna | viz níže |

Ztlumit / zrušit ztlumení požádá přehrávač o opak toho, co v okamžiku stisku
hlásí; přehrávač, který neřekne, zda je ztlumený (třeba vypnutý), se přeskočí.
Nedostupný cíl se přeskočí a živá aktivita řekne proč.

**Co je záměrně vynecháno:** odemknutí zámku, jeho otevření nebo přepnutí;
zapnutí sirény; otevření ventilu; vypnutí alarmu. Jeden náhodný stisk na ovladači,
který si může vzít kdokoli, nesmí otevřít dveře, spustit sirénu, pustit vodu ani
vypnout alarm; použijte skript nebo automatizaci, kde si určíte jak. U garážových
vrat a brány panel vedle *Otevřít* a *Přepnout* upozorní, že se po stisku otevřou,
i když se nikdo nedívá.

Pokud zařízení některou akci nepodporuje (třeba přehrávač nemá *další skladbu*),
Home Assistant zapíše chybu do protokolu; živá aktivita přesto řekne, že akce byla
přijata, protože volání se posílá bez čekání na zařízení. Propojení uložené před
touto změnou funguje beze změny.

## Scény a skripty jako cíle

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
            {{ 'light.example_b' if gesture == 'double_press' else 'light.example_a' }}
```

Nahraďte `light.example_a` a `light.example_b` vlastními světly. Vyberte skript
jako cíl krátkého i dvojitého stisku s akcí *Spustit skript*; jedním přepnete
první světlo, druhým druhé. Scéna, která nebyla
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
