"""Legal hook shown on screen. Amounts are settings to reconfirm with GMC, not claims."""
RULES = {
    "basis": "Supports a non-segregation notice under the Solid Waste Management Rules, 2016 (as cited in "
             "GMC's public notice of 11 Nov 2025: four streams, wet, dry, sanitary, domestic hazardous) "
             "and the MP SWM bye-laws (Gazette, 28 Sep 2020), Annexure-2.",
    "fine_note": "Annexure-2 spot fine for a bulk generator's non-segregation: Rs 1,000 per day "
                 "(Municipal Corporation above 10 lakh population; Rs 500 per day below). "
                 "This system only recommends; the amount is a setting and the officer decides.",
    "not_proof": "A photo shows segregation at the moment of pickup. It does not prove on-site wet-waste "
                 "processing, which is a separate duty checked by inspection or portal self-reporting.",
}
LADDER = {
    "warning": "Warning (first 'mixed' verdict in 30 days)",
    "notice": "Formal notice (second 'mixed' verdict in 30 days)",
    "fine_recommendation": "Fine recommendation (third or later 'mixed' verdict in 30 days)",
}
