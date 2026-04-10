# P1 Implementation Test Scenarios

## Test 1: Multilingual Handler Matching (REQ-12)

### Scenario 1A: Turkish Input
**Input:**
```
Istanbul'da liman deposunda sıcaklık arızası meydana geldi. Soğutulmuş ilaç sevkiyatında
sıcaklık ihlali tespit edildi. Tahmini zarar 450.000 USD. Poliçe numarası TR54-2026-0042.
Acil değerlendirme gerekiyor.
```

**Expected:**
- Detected Language: Turkish (TR) - 95%+ confidence
- Primary Handler: **H-MT-001 Emre Yilmaz** or **H-MT-002 Fatima Al-Hassan** (Turkish speakers)
- LoB: refrigerated_cargo
- Severity: High (temperature breach)
- Match reason should mention "Turkish-speaking handler for improved communication"

### Scenario 1B: German Input
**Input:**
```
Brandschaden in Hamburg Lagerhaus. Elektrischer Fehler verursachte Feuer. Mehrere Paletten
mit Elektronik betroffen. Geschätzter Schaden EUR 1,8 Millionen. Gutachter dringend erforderlich.
```

**Expected:**
- Detected Language: German (DE) - 95%+ confidence
- Primary Handler: **H-DACH-002 Lena Hoffmann** (property specialist)
- Secondary Handler: **H-GL-004 Youssef Benali** (surveyor)
- LoB: property
- Severity: Critical (fire + high value)

### Scenario 1C: Portuguese Input (Brazil)
**Input:**
```
Acidente de caminhão na BR-101 perto de Joinville. Colisão com perda total de carga.
Dano estimado BRL 280.000. Lesão corporal de terceiro relatada. Documentação disponível.
```

**Expected:**
- Detected Language: Portuguese (PT) - 95%+ confidence
- Primary Handler: **H-LATAM-003 Rodrigo Mendes** (Portuguese speaker, motor specialist)
- LoB: motor or transport
- Severity: High (third-party injury + total loss)
- Currency: BRL (not EUR!)

---

## Test 2: Trade Credit & Professional Indemnity Routing (REQ-13)

### Scenario 2A: Trade Credit - Buyer Insolvency
**Input:**
```
Trade credit claim notification. Our client ABC Distributors has filed a claim under policy
NC-TC-2025-0088 due to buyer insolvency. The debtor, XYZ Electronics Ltd, filed for bankruptcy
on March 15, 2026 with outstanding receivables of EUR 1.2 million. Credit default confirmed by
appointed administrator. Urgent review required.
```

**Expected:**
- Detected Keywords: insolvency, bankruptcy, credit default, receivables, trade credit
- LoB: **trade_credit**
- Primary Handler: **H-GL-003 Nina Bergström** (ALWAYS primary for financial lines)
- Region: Global (not routed to regional handler)
- Severity: Critical (high value)
- Match reason: "Nina Bergström is the global specialist for trade credit and financial lines"

### Scenario 2B: Professional Indemnity - Broker Error
**Input:**
```
Professional indemnity notification. Insured broker (Wilson & Partners Insurance Brokers)
facing E&O claim from client. Alleged negligent misrepresentation regarding policy coverage
resulted in GBP 450,000 uninsured loss. Client retained legal counsel. Duty of care breach
alleged. Documentation of advice and correspondence attached.
```

**Expected:**
- Detected Keywords: professional indemnity, E&O, negligent misrepresentation, duty of care breach, broker
- LoB: **professional_indemnity**
- Primary Handler: **H-GL-003 Nina Bergström** (ONLY handler for PI)
- Region: Global
- Severity: High
- Action: escalate or assign_to_handler_urgent

### Scenario 2C: Mixed - Not Financial Lines (Should NOT route to Nina)
**Input:**
```
Marine cargo loss at Rotterdam port. Container of electronics damaged by water ingress.
Estimated value EUR 340,000. Third-party liability claim from warehouse operator also reported.
```

**Expected:**
- LoB: marine_cargo or liability_general (NOT trade_credit or professional_indemnity)
- Primary Handler: **H-BNL-001 Celine Dubois** or **H-BNL-002 Pieter van Dijk** (NOT Nina Bergström)
- Region: Benelux

---

## Test 3: Data Gaps Detection ("What We Still Need" Panel)

### Scenario 3A: Thin Input - Maximum Gaps
**Input:**
```
A container fell off a truck.
```

**Expected Data Gaps:**
- ✓ claim_description: "Please provide a description of what happened"
- ✓ policy_number: "Please provide the policy number"
- ✓ date_of_loss: "Please provide the date of loss"
- ✓ location: "Please provide where the loss occurred"
- ✓ estimated_value: "Please provide the estimated value of the loss"
- ✓ geography (country, city): "Please specify the country and city"
- ✓ insurance_product: "Please specify the type of policy"

**Expected Severity:** Low (0-5/100)
**Expected Action:** request_documentation
**What We Still Need Panel:** Should show ALL missing fields with prompts

### Scenario 3B: Partial Information - Some Gaps
**Input:**
```
Fire at warehouse in Hamburg. Electronics damaged. Multiple consignments affected.
```

**Expected Data Gaps:**
- ✓ policy_number: "Please provide the policy number"
- ✓ estimated_value: "Please provide the estimated value of the loss"
- ✓ date_of_loss: "Please provide when the fire occurred"
- ✓ insured_party: "Please provide the name of the insured"

**Detected (No Gaps):**
- ✓ geography: Hamburg, Germany (DE)
- ✓ claim_type: property (fire damage)
- ✓ severity_indicators: fire, multiple consignments

### Scenario 3C: Complete Information - Zero Gaps
**Input:**
```
Received notification from warehouse operator DHL Supply Chain Germany at 14:15 CET on April 8, 2026.
Fire alarm triggered overnight at bonded warehouse in Hamburg (Warehouse #4, Hafenstraße 122).
Preliminary report indicates an electrical fault in storage rack caused localized fire, contained
by sprinkler system. Affected goods: consumer electronics (laptops, tablets) belonging to
TechDistrib GmbH and two other consignees. Estimated total value EUR 1.8 million.
Policy number: DE-PR-2024-5521. Fire brigade report and incident photos attached.
Insured requesting urgent surveyor appointment within 48 hours.
```

**Expected Data Gaps:** NONE (or minimal)
**What We Still Need Panel:** "✓ All key information detected"

---

## Test 4: Combined P1 Features

### Scenario 4: Turkish Trade Credit Claim
**Input (in Turkish):**
```
Ticari kredi talebi. Müşterimizin alıcısı iflas etti. Ödenmemiş alacaklar 850.000 EUR.
İflas idarecisi tarafından onaylandı. Acil inceleme gerekiyor.
```

**Expected:**
- Detected Language: Turkish (TR) - 95%+ confidence
- LoB: trade_credit
- Primary Handler: **H-GL-003 Nina Bergström** (Priority 2 rule overrides language matching)
- BUT: Should note that Turkish-speaking handlers exist in the region for follow-up communication
- Currency: EUR
- Severity: High (insolvency confirmed)
- Data Gaps: policy_number, date_of_loss, debtor details

---

## Validation Checklist

### Multilingual Handler Matching (REQ-12)
- [ ] Turkish claim → routes to H-MT-001 or H-MT-002
- [ ] German claim → routes to DACH handlers (H-DACH-*)
- [ ] Dutch claim → routes to Benelux handlers (H-BNL-*)
- [ ] Portuguese claim → routes to H-LATAM-002 or H-LATAM-003
- [ ] Spanish claim → routes to H-ES-001 or H-LATAM-001
- [ ] French claim → routes to H-BNL-001 (Celine) or H-GL-002 (David)
- [ ] Arabic claim → routes to H-MT-002 (Fatima) or H-GL-004 (Youssef)
- [ ] Chinese claim → routes to H-APAC-001 (Mei-Lin) or H-GL-001 (Sarah)
- [ ] Only falls back to English-only handlers when NO language match exists

### Trade Credit / PI Routing (REQ-13)
- [ ] Keywords detected: insolvency, bankruptcy, credit default, receivables, buyer insolvency
- [ ] Keywords detected: professional negligence, E&O, broker error, duty of care breach, malpractice
- [ ] ALWAYS routes to H-GL-003 (Nina Bergström) regardless of region
- [ ] Never routes financial lines to regional handlers
- [ ] LoB correctly set to trade_credit or professional_indemnity

### Data Gaps Panel (REQ-08)
- [ ] "What We Still Need" panel visible in UI
- [ ] Shows "✓ All key information detected" when no gaps
- [ ] Lists missing fields with user-facing prompts when gaps exist
- [ ] Thin input (5 words) generates extensive gap list
- [ ] Checks for: policy, geography, financial, insurance_product, third-party, date_of_loss
- [ ] Format: "• field_name: User-friendly prompt"

### Language Detection (Bonus Feature Foundation)
- [ ] Detected Language banner visible in UI
- [ ] Shows: "English (EN) - 95% confidence"
- [ ] Supports: EN, DE, NL, FR, ES, PT, IT, TR, AR, ZH, JA, SV, NO, DA, FI
- [ ] Confidence score 0-100%

---

## Testing Instructions

1. **Start the application:**
   ```bash
   cd /Users/tigerlab/projects/coral-phuket/gradio-demo
   python main.py
   ```

2. **Test each scenario systematically**
3. **Verify output matches expected results**
4. **Check JSON output for:**
   - `detected_language.code` and `confidence`
   - `handlers.primary.handler_id`
   - `handlers.primary.match_reason` (should mention language when applicable)
   - `classification.lob_code`
   - `data_gaps` array

---

## Known Limitations

1. **Language detection accuracy:** Depends on AI's language detection capabilities
2. **Mixed-language handling:** AI should detect primary language when multiple present
3. **Data gaps are AI-inferred:** May not catch all possible gaps, but should catch major ones
4. **Turkish special characters:** May require UTF-8 encoding validation

---

Generated: 2026-04-10
Status: P1 Test Scenarios Ready
