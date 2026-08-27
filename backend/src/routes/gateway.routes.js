const express = require('express');
const { authenticate } = require('../middleware/auth');

const router = express.Router();
router.use(authenticate);

// POST /api/gateway/predict
//
// Next session: proxy to AI_GATEWAY_URL + "/gateway/predict" via axios,
// forwarding a service-signed Bearer token (ai-gateway/middleware.py
// requires one). Real request/response contract, read from
// ai-gateway/schemas.py and orchestrator.py (this differs from the
// `/gateway/sepsis-assessment` shape described in CLAUDE.md, which looks
// stale — flag with Krishna before wiring this up):
//
//   POST {AI_GATEWAY_URL}/gateway/predict
//   Authorization: Bearer <token>
//   {
//     "patient_id": "uuid",
//     "encounter_id": "uuid",
//     "models": ["triage" | "deterioration" | "lab_parser" |
//                "drug_interaction" | "differential_dx" | "readmission"],
//     "context": {
//       "symptom_text": "string | null",
//       "medications": ["string"],
//       "lab_report_id": "string | null",
//       "vitals_last_n": 3
//     }
//   }
//
// The gateway does not accept raw vitals readings — each model endpoint
// receives only { patient_id, encounter_id, context }, so vitals history
// must be resolvable by the model itself. That plumbing isn't defined yet.
router.post('/predict', async (req, res) => {
  res.status(200).json({ message: 'TODO: proxy prediction request to AI Gateway', data: null });
});

module.exports = router;
