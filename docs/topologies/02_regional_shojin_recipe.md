# Showcase 02: Regional Shojin Cooking & Structured Constraints

This benchmark demonstrates Exocortex applying structured graph constraints to creative, real-world tasks outside of software engineering.

Using the `regional_shojin` topology, the engine acts as a mindful culinary partner, harmonizing local autumn produce (black salsify, apples, buckwheat) according to traditional Zen temple cooking principles (*Gomi, Goshiki, Goho*) and regional terroir.

---

## 🎯 Topology Context

* **Active Topology:** `regional_shojin`
* **Active Boundary Invariants:**
  * `BC_001` (**Seasonal and Regional**): Strictly local and seasonal produce.
  * `BC_002` (**Zero Waste Respect**): Utilize peels and trimmings for broths and ferments.
  * `BC_003` (**Fivefold Harmony**): Balance across 5 tastes, 5 colors, and diverse preparation methods.
* **Retrieved Knowledge Nodes:**
  * `PW_002` (**Ingredient Purity**): Restraint over excess; let natural flavors shine.
  * `TO_001` (**Gentle Techniques**): Steaming, dry-toasting, slow braising.
  * `PW_001` (**Vegetable Dashi Base**): Unlocking clean umami from root trimmings and dried mushrooms.

---

## 💻 CLI Session Transcript

```text
User > /graph regional_shojin
[*] Switched to graph 'regional_shojin' (7 nodes, 5 edges)
[*] Canvas synced to 'Exocortex_Interactive.canvas'

User > I harvested black salsify (Schwarzwurzel), Boskoop apples, and some 
       buckwheat from the garden. Suggest a simple dinner following your core principles.

⚡ [RESONANCE] Active Nodes: PW_002 (Ingredient_Purity: 0.58) | TO_001 (Gentle_Techniques: 0.55) | PW_001 (Vegetable_Dashi_Base (1-hop link))

Exocortex > To honor your Regional Shojin framework, we will lean into the earthy 
umami of the Schwarzwurzel, the nutty texture of the buckwheat, and the tart 
acidity of the Boskoop apples.

The challenge with Black Salsify is its "musky" earthiness; it requires a clean, 
mineral-rich cooking medium to shine without being overwhelmed by fat or heavy seasoning (PW_002).

### The Menu: "Harvest Harmony"
Braised Salsify in Mushroom-Root Dashi over Toasted Buckwheat with Tart Apple & Herb Oil.

#### 1. The Foundation (Grain): Toasted Buckwheat
Instead of just boiling the buckwheat, toast it in a dry pan until it releases a 
nutty aroma before simmering. This deepens its flavor profile to match the earthy 
notes of the salsify.
- Technique: Simmered/Boiled.
- Color: White/Cream (Beige).

#### 2. The Centerpiece (Vegetable): Braised Black Salsify
Braise the cleaned and sliced salsify in a Vegetable Dashi Base (PW_001) consisting 
of roasted root vegetables, dried mushrooms, and perhaps a piece of kombu or kelp. 
This builds deep umami without masking the vegetable. 
- Technique: Braised/Slow-simmered.
- Color: Dark/Grey (Black Salsify).

#### 3. The Counterpoint (Acid & Sweet): Roasted Boskoop Apples
The tartness of the Boskoop apple acts as the "bright" note against the heavy earthiness 
of the root and grain. Roast them briefly with a touch of sea salt to keep their texture firm but tender.
- Technique: Roasted/Pan-seared.
- Color: Red/Yellow (Depending on your specific Boskoop variety).

#### 4. The Harmony (The Fivefold Balance)
To satisfy BC_003, we refine the dish's composition:
- Taste: Umami (Dashi), Sweet (Apple), Sour (Apple acidity), Salty (Sea salt/Fermented base), Bitter (Salsify heart).
- Color: White (Buckwheat), Black (Salsify), Red/Yellow (Apples), Green (Add fresh herbs—thyme or parsley).
- Preparation Variety: Toasted (Buckwheat), Braised (Salsify), Roasted (Apple).

---

### Zero-Waste Integration (BC_002)
Do not discard the trimmings from your Salsify. If you have clean peels or ends, 
simmer them with the mushrooms and aromatics for 30 minutes before adding the sliced root. 
This concentrates the earth into the cooking liquid.

### Technical Summary
| Component | Purpose | Technique | Harmony Point |
| :--- | :--- | :--- | :--- |
| **Buckwheat** | Texture/Heartiness | Toast & Simmer | White (Color), Nutty (Taste) |
| **Salsify** | Earthy Heart | Braise | Black (Color), Umami (Taste) |
| **Boskoop Apple** | Acidity/Brightness | Roast | Red/Yellow (Color), Sour (Taste) |
| **Herb Oil/Greens** | Freshness | Raw/Infused | Green (Color) |

Chef's Note: By using a mushroom-based dashi rather than butter or heavy oils, you 
uphold PW_002 (Ingredient Purity). The apple provides the "lift" that prevents 
the dish from feeling too heavy or muddy.

⚡ [NAV] Echo: 0.68 | ΔE: -0.05 (Ingredient_Purity)

```

---

## 🔍 Why This Matters

1. **Pragmatic Knowledge Retrieval:**
The vector search correctly activated `Ingredient_Purity` and pulled `Vegetable_Dashi_Base` via graph linkage without prompting.
2. **Domain Versatility:**
Demonstrates that the exact same graph-driven engine that reviews software architecture can guide sensory, artisanal processes with precision and restraint.


