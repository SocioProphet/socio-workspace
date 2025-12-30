
package repair
trigger["unit_ambiguity"] { input.validation.units_ok == false }
trigger["consent_revoked"] { input.consent.allowed == false }
trigger["pii_risk"] { input.deid.estimated_risk > 0.0 }
