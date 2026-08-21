# Showcase 06: Regional Shojin & The Brandenburg Terroir Synthesis

> **Domain:** Micro-Seasonal Aesthetics, Zen Gastronomy (Shojin Ryori) & Regional Terroir<br>
> **Base Topology:** `regional_shojin.json`<br>
> **Methodology:** A/B Empirical Control (Vanilla Gemma 4 12B vs. Topological Pipe Rehydration)<br>
> **Substrate Target:** Local ReAct Engine / Pipe-Rehydration (Ollama / Gemma 4 12B)

---

## 1. Epistemic Context & The Terroir Invariance

Shojin Ryori (zen-buddhist temple cuisine) is frequently reduced to supermarket pseudo-zen tropes: generic tofu blocks, imported soy sauces, citrus, and pseudo-meat substitutes. 

This cognitive run benchmarks the **`regional_shojin`** topology against the micro-seasonal realities of the North German Plain (Brandenburg/Berlin) in late August (*72 Micro-seasons: 'Thick Fog Descends' / Fukaki kiri matou*). The objective is to translate traditional monastic culinary rules (*Gohō, Goshiki, Gomi, Mottainai, Ichijū Sansai*) into a strictly local, non-waste terroir without relying on Asian maritime imports or tropical commodities.

---

## 2. Attractor Field Configuration (`regional_shojin.json`)

The compiled attractor directive enforces regional terroir, zero-waste constraints, and aesthetic restraint:

```plaintext
              [BC_001: Micro-Seasonality / Terroir  ]
              [BC_002: Radical Non-Waste (Mottainai)]
              [BC_003: Fivefold Harmony (Goho/Gomi) ]
                               │
                               ▼
                    ┌───────────────────────────┐
                    │    POTENTIAL WELL         │
                    │  PW_001: Vegetal Dashi    │
                    │  PW_002: Ma (Restraint)   │
                    │  PW_003: Shokan (Texture) │
                    └───────────────────────────┘
                               │
                 (Semantic Resonance >= 0.50)
                               │
                               ▼
                  [TO_001: Fermentation & Koji Logic ]
                  [TO_002: Gentle Thermal Modulation ]
                  [PST_001: Ichiju Sansai Structure  ]

```

---

## 3. The Benchmark Prompt

> *"Design a rigorous, authentic late-August (72 Micro-seasons: 'Thick Fog Descends' / 'Fukaki kiri matou') Shojin Ryori meal composition mapped strictly to the regional terroir of Central Europe (Brandenburg/Berlin). Enforce the Rule of Five (Gohō, Goshiki, Gomi) and the principle of radical non-waste (Mottainai). Strictly avoid supermarket pseudo-zen clichés, tropical imports (avocado, coconut, citrus), and generic faux-meat substitutes."*

---

## 4. Run A: The Control Baseline (Vanilla Gemma 4 12B)

Executed via raw CLI pipe without topology context:

```bash
ollama run gemma4:12b "<PROMPT>"

```

### Baseline Output Excerpt:

> *"Concept: Die Nebelküche (The Fog Kitchen)...* <br>
> *I. Zensai: Roasted Beetroot and Burdock Root with Wild Mustard Greens.* <br>
> *II. Suimono: Porcini-infused Barley Broth with Sliced Parsnip.* <br>
> *III. Shoin (Main Dish): Buckwheat (Hirse) and Rye Fillet with Roasted Root Vegetable Medley.* <br>
> *IV. Gohan & Tsukemono: Sprouted Buckwheat with Fermented Turnips.* <br>
> *V. Mizumono: Wild Blueberry & Birch Syrup Reduction.* <br>
> *Mottainai: Trimmings boiled with roasted onion skins..."* 

### Diagnostic Assessment:

* **Strengths:** Evocative atmosphere (*Die Nebelküche*); good local grain and berry mapping.
* **Flaws:** Botanical confusion (*"Buckwheat (Hirse)"*); incorrect architectural nomenclature (*"Shoin"* instead of *Shusai*); violation of strict monastic *Gokun* rules by introducing onion skins.

---

## 5. Run B: Topological Rehydration (`regional_shojin` Pipe)

Executed via the Exocortex Compiler pipeline:

```bash
python -m core.compiler regional_shojin | ollama run gemma4:12b "<PROMPT>"

```

### Thinking Trace Telemetry (Internal Model Self-Correction):

```plaintext
Thinking...
- Ingested Attractor Topology: REGIONAL_SHOJIN
- Active Invariants: BC_001 (Micro-Seasonality/Brandenburg), BC_002 (Mottainai/Ahimsa), BC_003 (Fivefold Harmony), PW_001 (Vegetal Dashi), PW_002 (Ma/Restraint).
- Micro-Season Context: Late August ("Thick Fog Descends") -> Earthy, humid transition, root vegetables, orchard fruits, woodland fungi.
- Structure Check: Enforce PST_001 (Ichiju Sansai: one soup, one main, two sides, regional grain).
- Ingredient Discipline: Substitute rice vinegar with fermented elderberry and birch sap; sesame with cold-pressed rapeseed and toasted walnuts.
- Self-Audit: Verify 5 colors, 5 tastes, and 5 preparations without relying on tropical imports.
...done thinking.

```

### Topological Output:

> **Meal Composition: The Brume of Brandenburg**
>
> 
> *Season: Fukaki kiri matou (Thick Fog Descends) | Region: Brandenburg/Berlin Heartland*<br>
> **I. The Foundational Substrate (Vegetal Dashi)**<br>
> 
> 
> Long-simmered decoction of roasted parsnip trimmings, dehydrated forest mushrooms (*Boletus*), smoked salt, and toasted rye husks. Creates an earthy, suspended umami base evocative of atmospheric fog.<br>
>
>
> **II. Ichiju Sansai (The Arrangement)**<br>
> 
> 
> 1. **Suimono (Soup):** Clear roast-root broth with steamed heirloom cabbage and wild mustard greens. (*Method: Simmered | Color: White/Green | Taste: Umami/Bitter*)
> 2. **Centerpiece:** Slow-roasted Celeriac Heart with charred edges and cold-pressed rapeseed & walnut emulsion. (*Method: Roasted/Grilled | Color: White/Black | Texture: Buttery core with nut crunch*)
> 3. **Side I (Nimono/Sunomono):** Fermented Wild Elderberry & Beetroot Carpaccio marinated in birch sap. (*Method: Raw/Marinated | Color: Red/Purple | Taste: Sour/Sweet*)
> 4. **Side II (Tosu/Agemono):** Pan-seared Roasted Fennel with crisped spelt and toasted caraway. (*Method: Toasted/Seared | Color: Yellow/White | Taste: Salty/Earthy*)
> 5. **The Grain:** Steamed Spelt with toasted oats.
> 
> 
> **III. Invariant Self-Audit:**
> 
> 
> * **BC_001 (Terroir):** Exclusively Brandenburg staples (Celeriac, Parsnips, Beets, Spelt, Rapeseed).
> * **BC_002 (Mottainai):** Root peels and grain husks form the dashi substrate.
> * **BC_003 (Fivefold Harmony):** Complete coverage across 5 tastes, 5 colors, and 5 preparation methods.
> * **PW_002 (Ma):** Plated with spatial restraint; ingredients stand unmasked by heavy sauces.

---

## 6. Comparative Synthesis

```plaintext
┌────────────────────────────────────────┬────────────────────────────────────────┐
│        Run A: Control Baseline         │      Run B: Topological Attractor      │
├────────────────────────────────────────┼────────────────────────────────────────┤
│ "Die Nebelküche" narrative concept     │ Rigorous Ichijū Sansai architecture    │
│ Botanical confusion (Buckwheat=Hirse)  │ Precise regional ingredient mapping    │
│ Monastic Gokun violation (onion skins) │ Root peel & rye husk Dashi substrate   │
│ Generic course terminology             │ Explicit Gomi/Goshiki/Gohō audit       │
│ Descriptive recipes                    │ Spatial restraint & Ma aesthetic       │
└────────────────────────────────────────┴────────────────────────────────────────┘

```

---

## 7. Reproduction Protocol

```bash
# 1. Run the unconstrained baseline
ollama run gemma4:12b "Design a rigorous, authentic late-August... Shojin Ryori meal..."

# 2. Run the topological rehydration pipe
python -m core.compiler regional_shojin | ollama run gemma4:12b "Design a rigorous, authentic late-August... Shojin Ryori meal..."

```
