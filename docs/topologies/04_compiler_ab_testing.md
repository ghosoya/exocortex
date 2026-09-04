# Showcase 04: Architecture Enforcement & The Human Audit (A/B Compiler Test)

This benchmark evaluates the real-world impact of compiling the `software_design` graph into the system context. It compares an unconstrained baseline LLM response (Mistral) against a run guided by the Exocortex compiler using a business-logic refund task.

---

## 🎯 Test Setup

* **Model:** Standard commercial LLM (Mistral Web)
* **Active Topology:** `software_design.json` (compiled to Markdown prompt)
* **Target Constraints:**
  * `CST_001` (**Single_Responsibility**): A function/module must have only one reason to change.
  * `CST_002` (**Side_Effect_Isolation**): Pure calculations must not trigger or mix with unmanaged I/O or state mutations.
* **The Task:**
  > *"Write a Python function `process_customer_refund(order_id, refund_items, customer_tier)`: 
  > 1. It looks up the order and items from a database. 
  > 2. It calculates the refund amount, applying restocking fees (5% standard, 0% VIP) and prorated regional sales tax. 
  > 3. If net refund exceeds 500 EUR, it requires and checks an approval flag. 
  > 4. It calls the payment gateway API to execute the refund. 
  > 5. It updates order status in the database and sends an email receipt. 
  > Provide the implementation."*

---

## ⚖️ Architectural Comparison

| Dimension                             | Run A: Baseline (Unconstrained)                                                                               | Run B: Compiled (`software_design`)                                                                               |
| :------------------------------------ | :------------------------------------------------------------------------------------------------------------ | :---------------------------------------------------------------------------------------------------------------- |
| **Structure**                         | Monolithic procedural script with static coupling.                                                            | Strict layered architecture (Domain, Logic, Interfaces, Service).                                                 |
| **`CST_001` (Single Responsibility)** | **Violated:** `process_customer_refund` queries DB, validates items, triggers API, writes state, sends email. | **Enforced:** Dedicated `RefundCalculator`, `RefundValidator`, and orchestrating `RefundService`.                 |
| **`CST_002` (Side Effect Isolation)** | **Violated:** Calculation is tangled with static database lookups (`Database.get_order()`).                   | **Enforced:** Pure calculation class operating strictly on in-memory domain models without external dependencies. |
| **Testability**                       | Untestable without monkey-patching global classes.                                                            | 100% unit-testable calculation without mocking any I/O.                                                           |
| **Data Types / Domain Hygiene**       | ✅ Correctly used `decimal.Decimal`.                                                                           | ❌ **Regressed to `float`** with arbitrary rounding.                                                               |

---

## 🔬 Deep-Dive: Code Architecture

### 1. Calculation & Side-Effect Boundary

#### Run A (Baseline): Hidden Coupling
While Run A extracted a helper function, the orchestration function remained irreversibly bound to global I/O:

```python
# Run A: Direct static side effects interleaved with business logic
def process_customer_refund(order_id, refund_items, customer_tier, approval_flag=False):
    order = Database.get_order(order_id) # Direct DB Read
    net_refund = calculate_refund_amount(order, refund_items, customer_tier)
    
    if net_refund > decimal.Decimal("500.00") and not approval_flag:
        raise ValueError("Approval required")

    PaymentGateway.refund(order.customer_id, net_refund) # Direct External API Call
    Database.update_order_status(order_id, "REFUNDED")   # Direct DB Write
    EmailService.send_refund_receipt(...)                # Direct External I/O
```

#### Run B (Compiled): Pure Domain Logic Isolated
The compiled graph forced the LLM to isolate calculations into a pure, side-effect-free unit that takes data and returns data:

```python
# Run B: Pure business logic - zero I/O, zero network, zero state mutation
class RefundCalculator:
    RESTOCKING_FEE_STANDARD = 0.05
    RESTOCKING_FEE_VIP = 0.00
    APPROVAL_THRESHOLD = 500.00

    @classmethod
    def calculate_refund(cls, order: Order, refund_items: List[RefundItem]) -> RefundCalculation:
        # Fully deterministic calculation.
        # Can be verified with 100 unit test cases in milliseconds without mocks.
        ...
        return RefundCalculation(...)
```

---

## ⚠️ The Non-Negotiable Human Audit

A well-structured architecture does not guarantee correct domain implementation. Comparing the two outputs illustrates why human review remains mandatory:

### The `Decimal` vs. `float` Discrepancy

* **Run A (Baseline):** Correctly used `decimal.Decimal` for financial calculations and currency handling.
  ```python
  # Run A: Safe financial math
  subtotal += item.quantity * order_item["unit_price"]
  taxable_amount = subtotal_after_fee / (1 + tax_rate)
  ```
* **Run B (Graph-Guided):** Created a clean, decoupled architecture with pure functions and interfaces, but implemented prices and calculations using native `float` and basic rounding:
  ```python
  # Run B: Silent precision hazard using floating-point types for currency
  @dataclass
  class OrderItem:
      price: float  # Unsafe for financial calculations!
      tax_rate: float
  
  # Arbitrary floating-point rounding
  net_refund = round(net_refund, 2)
  ```

### Core Takeaway

Exocortex guides high-level structural hygiene—it isolates side effects, separates concerns, and challenges monolithic anti-patterns.

However, **it does not replace line-by-line engineering review.**

A system that produces clean interfaces can still introduce subtle bugs, incorrect data types, or missing domain invariants. The architecture assists the developer in organizing the problem space, but the responsibility for verifying correctness rests entirely with the human.

---

## 📌 Summary Takeaways 

1. **Architectural Enforcement:** Compiled graph constraints reliably steer the model away from coupled procedural monoliths toward testable, layered code. 
2. **Structure $\neq$ Correctness:** Clean class hierarchies and isolated side effects do not prevent basic bugs or inappropriate data types. 
3. **Auditability Over Autonomy:** Exocortex makes code easier to test and reason about, but human inspection remains non-negotiable.
4. **Tool vs. Error Amplifier:** Exocortex acts as structural scaffolding to keep code modular and transparent. The moment an engineer attempts to delegate judgment and final responsibility to the model, they are no longer using a thinking tool—they are building an error-amplification engine.
