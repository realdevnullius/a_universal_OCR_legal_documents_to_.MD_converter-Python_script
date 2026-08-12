# Juridische documenten naar Markdown — batchconverter

**[English version (README.md)](README.md)**

Zet vonnissen, juridische correspondentie, e-mailthreads en gefotografeerde dossierstukken in bulk om naar gestructureerde, LLM-klare Markdown.

Gebouwd op **IBM Docling** voor layoutanalyse en **Tesseract OCR** voor tekstherkenning. Draait volledig offline. Gericht op Windows x64 met Microsoft Store Python, waar de sandbox-paden van die versie standaard-opzetten laten vastlopen.

Het pakket bevat een optionele Nederlandse juridische woordenlijst, plus het gereedschap om te **meten of die woordenlijst werkelijk iets oplevert** — inclusief eerlijke resultaten van een batch van 249 documenten. Zie [CUSTOMDIC.md](CUSTOMDIC.md) om er een te bouwen voor je eigen taal en vakgebied.

---

## Mappenstructuur

De root van de repository bevat alleen scripts. Al het andere staat in vier werkmappen die automatisch worden aangemaakt bij de eerste run:

```
.\                      de scripts
  _SOURCE-DOCS\         zet hier je documenten
  _FAILED\              documenten die niet geconverteerd konden worden (meestal RAM)
  _WITH-DICT.out\       markdown van een run MET de woordenlijst
  _NO-DICT.out\         markdown van een run ZONDER
```

De markdown wordt rechtstreeks in de uitvoermap geschreven. Er wordt achteraf niets verplaatst, dus een onderbroken run laat geen bestanden op de verkeerde plek achter en gaat gewoon verder waar hij was gebleven.

---

## Bestanden in deze repository

| Bestand | Functie |
|---|---|
| `jpg.pdf.convert.py` | De converter. Alle instellingen staan bovenaan. |
| `ocr_words_patch.py` | Schuift `--user-words` in de Tesseract-aanroep die Docling intern doet. Docling biedt geen manier om extra vlaggen mee te geven, dus dit onderschept `subprocess.run`. |
| `ocr-without-dict.cmd` | Draait de conversie **zonder** woordenlijst. Dit is de basisrun en de aanbevolen standaard. |
| `ocr-with-dict.cmd` | Dezelfde conversie **met** de woordenlijst, ter vergelijking. |
| `dutch_legal_lean.words` | 1.715 Nederlandse juridische termen en afkortingen. |
| `deduplicate.py` | Vergelijkt de twee uitvoermappen en meldt of de woordenlijst iets heeft veranderd. |
| `dedup_outputs.cmd` | Wrapper voor `deduplicate.py`: tellingen vooraf, proefronde, bevestiging en samenvatting. |
| `check_markdown.py` | Markeert markdown die mogelijk pagina's mist. |
| `CUSTOMDIC.md` | Hoe de woordenlijst werkt, plus een kant-en-klare AI-prompt om er zelf een te bouwen. |

---

## Installatie (Windows x64)

### 1. Python

Installeer **Python 3.9 of nieuwer** via de Microsoft Store. De scripts zijn geschreven om de geïsoleerde profielpaden van die versie te overleven.

### 2. Tesseract OCR

Download de Windows x64-installer, bijvoorbeeld van [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).

Vouw tijdens de installatie **Additional language data** uit en vink de taal aan die je nodig hebt — `nld` voor Nederlands. Het standaard installatiepad is `C:\Program Files\Tesseract-OCR\tesseract.exe`; als je dat wijzigt, pas dan `TESSERACT_PATH` bovenin `jpg.pdf.convert.py` aan.

### 3. Python-pakketten

```powershell
pip install docling
```

---

## Gebruik

1. Zet je documenten in `.\_SOURCE-DOCS\`
2. Dubbelklik op `ocr-without-dict.cmd` (de basisrun) of `ocr-with-dict.cmd`, of draai ze vanuit PowerShell.

Beide wrappers forceren de werkmap naar hun eigen map, dus starten vanuit Verkenner, via een snelkoppeling of via *Als administrator uitvoeren* werkt allemaal identiek.

Ondersteunde invoer: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`. Docling leest ook `.docx`, `.pptx`, `.html`, `.rtf` — voeg de extensie toe aan de `extensions`-lijst in het script om die in te schakelen.

### Naamgeving uitvoer

```
brief.pdf   ->  brief.pdf.md        (zonder woordenlijst)
brief.pdf   ->  brief.pdf.dic.md    (met woordenlijst)
```

De bronextensie blijft behouden, zodat `scan.pdf` en `scan.jpg` elkaars uitvoer niet overschrijven. De `.dic`-markering maakt het mogelijk om beide versies van hetzelfde document te vergelijken, of ze samen aan een AI Agent voor te leggen.

---

## Instellingen

Allemaal bovenin `jpg.pdf.convert.py`:

| Instelling | Standaard | Wat het doet |
|---|---|---|
| `LANGUAGE` | `"EN"` | Taal van de meldingen van het script. `"EN"` of `"NL"`. Niet de OCR-taal. |
| `LIMIT_MEMORY_USAGE` | `False` | Zet op `True` om op ~150 DPI te verwerken i.p.v. volledige resolutie. Scheelt ruwweg driekwart van het geheugengebruik per pagina. |
| `TESSERACT_PATH` | Program Files | Volledig pad naar `tesseract.exe`. |
| `QUARANTINE_INCOMPLETE` | `True` | Weiger markdown te schrijven als Docling pagina's heeft laten vallen. Laat dit aan staan. |
| `MIN_FREE_MB` | `2000` | Waarschuw vóór een document als het bruikbare geheugen onder deze waarde zakt. `0` schakelt uit. |
| `MEM_WARN_STEP_MB` | `500` | Na de eerste waarschuwing pas weer melden als het geheugen nóg zoveel is gedaald. |

De OCR-taal staat apart, in `lang=["nld"]`. Voeg daar verdere Tesseract-taalcodes aan toe.

`LANGUAGE` kan ook zonder het script te bewerken worden overschreven, door `SCRIPT_LANG=NL` te zetten in de `.cmd`-wrapper of in je shell. De wrappers zetten dit expliciet, dus het wijzigen van één regel daar is voldoende.

---

## Herstelronde

Een document dat mislukt — meestal `std::bad_alloc` bij geheugengebrek — wordt naar `_FAILED` verplaatst en er wordt geen markdown voor geschreven. Een onvolledig document is achteraf niet te onderscheiden van een compleet document, en dat is precies het soort stille fout dat een juridisch dossier zich niet kan veroorloven.

```
_SOURCE-DOCS\  ──►  (conversie mislukt)  ──►  _FAILED\
                                                │
_SOURCE-DOCS\  ◄──  (lukt bij tweede poging)  ◄──  draai het script in _FAILED\
```

Opnieuw proberen:

1. Kopieer **allebei** `jpg.pdf.convert.py` en `ocr_words_patch.py` naar `.\_FAILED\`
2. Draai de `.cmd` daar, of `python .\jpg.pdf.convert.py`

De bronbestanden worden dan uit `_FAILED` gelezen, de markdown gaat nog steeds naar de uitvoermap één niveau hoger, en een document dat alsnog slaagt verhuist terug naar `_SOURCE-DOCS`.

Geheugen komt meestal vrij tussen runs, dus een tweede poging slaagt vaak waar de eerste vastliep. Blijft een document mislukken, zet dan `LIMIT_MEMORY_USAGE = True` of splits zeer grote PDF's op.

---

## Wat een run rapporteert

Elke run eindigt met een samenvatting:

```
Batch complete!
  Fully processed : 249
  Incomplete      : 0
  Failed          : 0
  Skipped         : 0

  Total running time: 1h 04m 10s
  Average per document: 15.5s  (249 converted)
  Word list was ACTIVE during this run.
```

`Average per document` is het cijfer om runs te vergelijken, aangezien de aantallen zelden precies overeenkomen.

Bij een normale afronding schrijft het script `_run_complete.flag`, waar de `.cmd`-wrapper op controleert. Dit is belangrijk omdat een geheugenallocatiefout in Tesseract of PyTorch Python kan beëindigen met **exitcode 0 en geen traceback** — de exitcode alleen is niet te vertrouwen. Als de markering ontbreekt, meldt de wrapper dat en vertelt hij dat de run gewoon opnieuw gestart kan worden.

---

## Helpt de woordenlijst werkelijk?

Draai beide wrappers over dezelfde documenten en dubbelklik daarna op `dedup_outputs.cmd`.

Het telt eerst beide uitvoermappen — de vergelijking zegt alleen iets als beide runs dezelfde documenten hebben gehad — toont dan de proefronde, vraagt voordat het iets verwijdert en sluit af met het cijfer dat de vraag beantwoordt:

```
  The word list changed the output of 2 of 249 documents (0.8%).
```

Het alternatief via de commandline:

```powershell
python deduplicate.py --dry-run
python deduplicate.py
```

Het koppelt `_WITH-DICT.out\<naam>.dic.md` aan `_NO-DICT.out\<naam>.md`. Identieke paren betekenen dat de woordenlijst niets heeft veranderd, en de `.dic.md`-kopie wordt verwijderd. Afwijkende paren blijven staan, met de afwijkende woorden erbij.

**Resultaten van de benchmark over 249 documenten:**

| | |
|---|---|
| Identiek | 247 |
| Verschillend | 2 (0,8%) |

Van die twee: één echte verbetering (`huipofficier` → `hulpofficier`), en één artefact van de vergelijking zelf — de basisrun produceerde één extra token, waarna de woord-voor-woord vergelijking uit de pas loopt en een reeks schijnverschillen meldt.

Over 249 documenten verbeterde de woordenlijst dus precies één woord, en brak niets.

Een eerdere ronde van dezelfde benchmark leverde ook een verslechtering op (`Piketadvocaat` → `piketadvocaat`), veroorzaakt door een woordenlijst die volledig naar kleine letters was omgezet. Het toevoegen van de variant met beginhoofdletter loste dat op, bevestigd door het betreffende document opnieuw te converteren. Dit is de reden dat `dutch_legal_lean.words` beide vormen bevat.

Netto-effect: ongeveer nul. Op Tesseract 4 en 5 weegt de LSTM-engine zijn visuele herkenning veel zwaarder dan woordenboekhints, dus `--user-words` duwt eerder dan dat het corrigeert. De run zonder woordenlijst was ook meetbaar sneller.

Het gereedschap staat hier zodat je dit voor je eigen materiaal kunt meten, in plaats van iemand op zijn woord te geloven — mijzelf incluis.

---

## Bekende beperkingen

**De pijplijn is niet deterministisch.** Twee runs over hetzelfde bestand leverden verschillende uitvoer op, en in één ervan werd een tekstblok als `<!-- image -->` geclassificeerd en verdween de tekst. Controleer alles steekproefsgewijs waar je op vertrouwt.

**Geheugen is het echte knelpunt.** Docling's layoutmodel reserveert veel meer dan de documentgrootte doet vermoeden. PDF's boven de ~150 pagina's zijn het gebruikelijke breekpunt.

**Geen vervanging voor het lezen van het origineel.** OCR-uitvoer is een zoek- en analysehulpmiddel. Controleer alles wat ertoe doet tegen het brondocument.

---

## Privacy

Alles draait lokaal. Geen cloud-API's, geen telemetrie, geen enkel document verlaat de machine.

De meegeleverde `.gitignore` werkt als allowlist: alles wordt genegeerd, en alleen de projectbestanden worden teruggezet. `_SOURCE-DOCS\` en `_FAILED\` verschijnen op GitHub als lege mappen; de uitvoermappen worden nooit gepubliceerd. Als je deze repository forkt, houd die opzet dan in stand — een denylist kan een bestandstype missen waar niemand aan heeft gedacht.
