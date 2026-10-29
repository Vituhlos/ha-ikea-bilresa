# Panel BILRESA

[README](../../README.cs.md) · [Všichni průvodci](../README.md) · [English](../en/panel.md) · **Čeština**

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
  stisku (viz [ovládací propojení](bindings.md#gui-ovládací-propojení-ovládání-bez-yaml)).
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
  může nastavit dvě proměnné; viz [Řešení potíží](troubleshooting.md).

Panel lze použít místo nativního průvodce popsaného v [ovládacích
propojeních](bindings.md#gui-ovládací-propojení-ovládání-bez-yaml) i spolu s ním;
oba zapisují stejná propojení.
