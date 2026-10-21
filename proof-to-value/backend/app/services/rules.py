"""Legal hook shown on screen. Amounts are settings to reconfirm with GMC, not claims."""
RULES = {
    "basis": "Supports a non-segregation notice under the Solid Waste Management Rules, 2026 "
             "(four-stream segregation) and Gwalior's spot-fine schedule.",
    "fine_note": "Historical spot-fine: Rs 1,000 first / Rs 3,000 repeat (to be reconfirmed with GMC). "
                 "This system only recommends; the amount and local thresholds are settings.",
    "not_proof": "A photo shows segregation at the moment of pickup. It does not prove on-site wet-waste "
                 "processing, which is a separate duty checked by inspection or portal self-reporting.",
}
LADDER = {
    "warning": "Warning (first 'mixed' verdict in 30 days)",
    "notice": "Formal notice (second 'mixed' verdict in 30 days)",
    "fine_recommendation": "Fine recommendation (third or later 'mixed' verdict in 30 days)",
}
