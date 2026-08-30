# Showcase 02: Regional Shojin Cooking & Structured Constraints

This benchmark demonstrates Exocortex applying structured graph constraints to sensory, artisanal tasks outside of software engineering.

Using the `regional_shojin` topology, the engine acts as a mindful culinary thinking partner, harmonizing local autumn harvest produce (black salsify, Boskoop apples, buckwheat) according to traditional Zen temple cooking principles (*Gomi, Goshiki, Goho*) and regional terroir.

---

## 🎯 Topology Context

* **Active Topology:** `regional_shojin`
* **Active Constraints:**
  * `CST_001` (**Seasonal_and_Regional**): Use strictly local, seasonal, plant-based ingredients. Honor terroir and natural cycles.
  * `CST_002` (**Zero_Waste_Respect**): Treat every part of the plant with respect. Peels, trimmings, and cores become broths, seasonings, or ferments.
  * `CST_003` (**Fivefold_Harmony**): Balance each meal across 5 tastes (*Gomi*), 5 colors (*Goshiki*), and diverse preparation methods (*Goho*).
* **Retrieved Knowledge Nodes:**
  * `CNC_001` (**Vegetable_Dashi_Base**): Deep, clean plant umami using dried mushrooms, kombu, and roasted vegetable scraps.
  * `CNC_002` (**Ingredient_Purity**): Restraint over complexity; highlight natural textures and authentic essence without masking.
  * `RUL_001` (**Gentle_Techniques**): Preserve texture and vitality via gentle simmering, light roasting, and raw pairing.

---

## 💻 CLI Session Transcript

````text
You > /graph regional_shojin

[*] Switched to graph 'regional_shojin' (7 nodes, 5 edges)
[*] Canvas synced to 'Exocortex_Interactive.canvas'

You > I harvested black salsify (Schwarzwurzel), Boskoop apples, and some buckwheat from the garden. Suggest a simple dinner following your core principles.

⚡ [CONTEXT] Active Nodes: CNC_002 (Ingredient_Purity: 0.58) | RUL_001 (Gentle_Techniques: 0.55) | CNC_001 (Vegetable_Dashi_Base (1-hop link))

Exocortex > To design this meal, I am applying the **Regional Shojin** framework: prioritizing ingredient purity, utilizing your gathered harvest fully, and balancing the elements of taste and texture without masking their natural profiles.

### The Concept: "Earth & Orchard"
This dish focuses on the harmony between the earthy, nutty notes of the **Salsify** and **Buckwheat**, balanced by the sharp acidity of the **Boskoop Apple**. 

By using a **Vegetable Dashi (CNC_001)** as your cooking base for the grains, we create depth without heavy fats or excessive seasoning.

---

### The Menu: Roasted Salsify & Buckwheated Grain Bowl
*Served with a Tart Apple & Herb Relish.*

#### 1. Preparation of the Base (The Dashi & Grains)
*   **Technique:** Simmering / Slow Cooking
*   **Action:** Do not discard the ends or trimmings of the salsify during preparation. Simmer these "waste" pieces with water and a pinch of salt to create a simple vegetable dashi. 
*   **Integration:** Cook the **Buckwheat** directly in this dashi. This infuses the grain with umami from the roots while maintaining their earthy integrity (CNC_002).

#### 2. The Main Component (The Salsify)
*   **Technique:** Braising or Roasting
*   **Action:** Slice the **Salsify** into rounds. Roast them until the edges are slightly caramelized. 
*   **Why:** Salsify has a nutty, celery-like flavor that intensifies when roasted. This provides the "Hearty/Savory" (Umami) component of the meal.

#### 3. The Counterpoint (The Boskoop Apple)
*   **Technique:** Raw / Fresh
*   **Action:** Thinly slice the **Boskoop apples**. Toss them with a tiny amount of salt and, if available, a pinch of any local herbs (like parsley or chives). 
*   **Why:** The tartness of the Boskoop acts as the "Sour" and "Sweet" balance to cut through the density of the buckwheat and roasted root.

---

### Alignment with Core Principles:

| Constraint | Application in this Menu |
| :--- | :--- |
| **CST_001 (Regional)** | Uses only your garden-harvested seasonal items. |
| **CST_002 (Zero Waste)** | Salsify trimmings are repurposed into the dashi base. |
| **CST_003 (5x Harmony)** | **Tastes:** Umami (Buckwheat/Salsify), Sweet/Sour (Apple), Bitter (hint of roasted root). <br> **Colors:** White (Salsify interior), Dark (Buckwheat), Red/Yellow (Boskoop skins).<br> **Methods:** Braised/Simmered (Grains), Roasted (Salsify), Raw (Apples). |
| **CNC_002 (Purity)** | No heavy sauces; the flavor of the "earth" (salsify) and "field" (buckwheat) is front-and-center. |

### Preparation Note for your Scratchpad:
> **Recipe Idea: Harvested Root & Grain Bowl**
> *   *Base:* Buckwheat cooked in a root-scrap dashi.
> *   *Protein/Body:* Roasted Salsify (ensure skins are well-scraped to remove bitterness).
> *   *Accent:* Raw Boskoop slices (to provide acidity and crunch).
> *   *Note:* The interplay between the "heavy" earth of the root and the "bright" acid of the apple is the core experience.

⚡ [NAV] Echo: 0.66 | ΔE: -0.06 (Ingredient_Purity)

````

---

## 🔍 Why This Matters

1. **Automatic 1-Hop Knowledge Expansion:**
The vector search retrieved `CNC_002` and `RUL_001` based on the prompt's semantics. The graph engine automatically traversed the edge to `CNC_001` (*Vegetable_Dashi_Base*), enabling the model to propose boiling the grains in root-scrap dashi without the user asking for it.
2. **Deterministic Constraint Enforcement:**
The system mapped the solution directly across the three core constraints (`CST_001`, `CST_002`, `CST_003`), demonstrating that Exocortex can structure complex, non-technical decisions with the same rigor as software architecture.

