#!/usr/bin/env python3
"""
P1 Feature Testing Script
Tests multilingual handler matching, Trade Credit/PI routing, and data gaps detection
"""

import json
from functions.fnol_triage import triage_fnol

print("=" * 80)
print("P1 FEATURE TESTING")
print("=" * 80)

# Test 1A: Turkish Input - Multilingual Handler Matching
print("\n[TEST 1A] Turkish Input - Multilingual Handler Matching")
print("-" * 80)
turkish_input = """
Istanbul'da liman deposunda sıcaklık arızası meydana geldi. Soğutulmuş ilaç sevkiyatında
sıcaklık ihlali tespit edildi. Tahmini zarar 450.000 USD. Poliçe numarası TR54-2026-0042.
Acil değerlendirme gerekiyor.
"""
print(f"Input: {turkish_input[:100]}...")

result = triage_fnol(turkish_input, None, "", "", "", "", "", "", "")
data = json.loads(result)

print(f"✓ Detected Language: {data['detected_language']['name']} ({data['detected_language']['code']}) - {data['detected_language']['confidence']}% confidence")
print(f"✓ Primary Handler: {data['handlers']['primary']['name']} ({data['handlers']['primary']['handler_id']})")
print(f"✓ Match Reason: {data['handlers']['primary']['match_reason']}")
print(f"✓ LoB: {data['classification']['lob_code']}")
print(f"✓ Severity: {data['severity']['level']} ({data['severity']['score']}/100)")

# Expected: Turkish detected, routes to H-MT-001 or H-MT-002
expected_handlers = ["H-MT-001", "H-MT-002"]
handler_match = data['handlers']['primary']['handler_id'] in expected_handlers
print(f"\n{'✅ PASS' if handler_match else '❌ FAIL'}: Turkish speaker assigned ({data['handlers']['primary']['handler_id']})")

# Test 2A: Trade Credit - Buyer Insolvency
print("\n\n[TEST 2A] Trade Credit - Buyer Insolvency")
print("-" * 80)
tc_input = """
Trade credit claim notification. Our client ABC Distributors has filed a claim under policy
NC-TC-2025-0088 due to buyer insolvency. The debtor, XYZ Electronics Ltd, filed for bankruptcy
on March 15, 2026 with outstanding receivables of EUR 1.2 million. Credit default confirmed by
appointed administrator. Urgent review required.
"""
print(f"Input: {tc_input[:100]}...")

result = triage_fnol(tc_input, None, "", "", "", "", "", "", "")
data = json.loads(result)

print(f"✓ Detected Language: {data['detected_language']['name']} ({data['detected_language']['code']})")
print(f"✓ LoB: {data['classification']['lob_code']}")
print(f"✓ Primary Handler: {data['handlers']['primary']['name']} ({data['handlers']['primary']['handler_id']})")
print(f"✓ Match Reason: {data['handlers']['primary']['match_reason']}")
print(f"✓ Severity: {data['severity']['level']} ({data['severity']['score']}/100)")

# Expected: ALWAYS routes to H-GL-003 (Nina Bergström)
nina_match = data['handlers']['primary']['handler_id'] == "H-GL-003"
tc_match = data['classification']['lob_code'] == "trade_credit"
print(f"\n{'✅ PASS' if nina_match else '❌ FAIL'}: Nina Bergström assigned for trade credit ({data['handlers']['primary']['handler_id']})")
print(f"{'✅ PASS' if tc_match else '❌ FAIL'}: Classified as trade_credit ({data['classification']['lob_code']})")

# Test 2B: Professional Indemnity - Broker Error
print("\n\n[TEST 2B] Professional Indemnity - Broker Error")
print("-" * 80)
pi_input = """
Professional indemnity notification. Insured broker (Wilson & Partners Insurance Brokers)
facing E&O claim from client. Alleged negligent misrepresentation regarding policy coverage
resulted in GBP 450,000 uninsured loss. Client retained legal counsel. Duty of care breach
alleged. Documentation of advice and correspondence attached.
"""
print(f"Input: {pi_input[:100]}...")

result = triage_fnol(pi_input, None, "", "", "", "", "", "", "")
data = json.loads(result)

print(f"✓ Detected Language: {data['detected_language']['name']} ({data['detected_language']['code']})")
print(f"✓ LoB: {data['classification']['lob_code']}")
print(f"✓ Primary Handler: {data['handlers']['primary']['name']} ({data['handlers']['primary']['handler_id']})")
print(f"✓ Match Reason: {data['handlers']['primary']['match_reason']}")
print(f"✓ Severity: {data['severity']['level']} ({data['severity']['score']}/100)")

# Expected: ALWAYS routes to H-GL-003 (Nina Bergström)
nina_match = data['handlers']['primary']['handler_id'] == "H-GL-003"
pi_match = data['classification']['lob_code'] == "professional_indemnity"
print(f"\n{'✅ PASS' if nina_match else '❌ FAIL'}: Nina Bergström assigned for PI ({data['handlers']['primary']['handler_id']})")
print(f"{'✅ PASS' if pi_match else '❌ FAIL'}: Classified as professional_indemnity ({data['classification']['lob_code']})")

# Test 3A: Thin Input - Maximum Gaps
print("\n\n[TEST 3A] Thin Input - Data Gaps Detection")
print("-" * 80)
thin_input = "A container fell off a truck."
print(f"Input: {thin_input}")

result = triage_fnol(thin_input, None, "", "", "", "", "", "", "")
data = json.loads(result)

print(f"✓ Detected Language: {data['detected_language']['name']} ({data['detected_language']['code']})")
print(f"✓ LoB: {data['classification']['lob_code']}")
print(f"✓ Severity: {data['severity']['level']} ({data['severity']['score']}/100)")

data_gaps = data.get('data_gaps', [])
print(f"\n✓ Data Gaps Detected: {len(data_gaps)} gaps")
for gap in data_gaps[:5]:  # Show first 5
    print(f"  • {gap['field']}: {gap['prompt']}")
if len(data_gaps) > 5:
    print(f"  ... and {len(data_gaps) - 5} more")

# Expected: Extensive data gaps
gaps_detected = len(data_gaps) >= 4
print(f"\n{'✅ PASS' if gaps_detected else '❌ FAIL'}: Multiple data gaps detected ({len(data_gaps)} gaps)")

print("\n" + "=" * 80)
print("P1 TESTING COMPLETE")
print("=" * 80)
