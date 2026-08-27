const cron = require('node-cron');
const axios = require('axios');
const { query } = require('../lib/db');
const { signServiceToken } = require('../utils/jwt');
const {
  emitSepsisAlert,
  emitScoreUpdated,
} = require('../sockets/index');

const AI_GATEWAY_URL = process.env.AI_GATEWAY_URL || 'http://localhost:8000';
const SOFA_ALERT_DELTA = 2; // sepsis:alert also fires on SOFA increase >= 2

// See src/routes/gateway.routes.js for why "deterioration" is used here
// instead of a literal "sepsis" model type, and why vitals aren't sent
// directly — that's an open question for the AI Gateway owner.
async function scoreEncounter(encounter) {
  const medsResult = await query(
    `SELECT "drugName" FROM medications WHERE "encounterId" = $1 AND status = 'ACTIVE'`,
    [encounter.id],
  );
  const medications = medsResult.rows.map((row) => row.drugName);

  const previousResult = await query(
    `SELECT result FROM predictions
     WHERE "encounterId" = $1 AND "modelType" = 'deterioration'
     ORDER BY "predictedAt" DESC LIMIT 1`,
    [encounter.id],
  );
  const previousSofa = previousResult.rows[0]?.result?.sofa_rounded ?? null;

  const token = signServiceToken();
  const startedAt = Date.now();

  let block;
  try {
    const response = await axios.post(
      `${AI_GATEWAY_URL}/gateway/predict`,
      {
        patient_id: encounter.patientId,
        encounter_id: encounter.id,
        vitals_readings: encounter.vitals.map((v, idx) => ({
          hr: v.heartRate,
          o2sat: v.spo2,
          temp: v.temperature,
          sbp: v.systolicBp,
          map: v.map,
          dbp: v.diastolicBp,
          resp: v.respiratoryRate,
          iculos: idx + 1
        })),
        medications,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 10_000,
      },
    );
    block = response.data?.deterioration;
  } catch (err) {
    console.error(`[scoringJob] Gateway call failed for encounter ${encounter.id}:`, err.message);
    return;
  }

  if (!block || block.status !== 'success' || !block.result) {
    console.warn(`[scoringJob] No usable result for encounter ${encounter.id}: ${block?.status}`);
    return;
  }

  const result = block.result;
  const sofaIncreased = previousSofa != null && result.sofa_rounded - previousSofa >= SOFA_ALERT_DELTA;
  const alertTriggered = Boolean(result.alert) || sofaIncreased;

  const inserted = await query(
    `INSERT INTO predictions
       ("encounterId", "patientId", "modelType", result, "alertTriggered", "latencyMs")
     VALUES ($1, $2, 'deterioration', $3, $4, $5)
     RETURNING id, "predictedAt"`,
    [encounter.id, encounter.patientId, result, alertTriggered, block.latency_ms ?? Date.now() - startedAt],
  );

  emitScoreUpdated({
    patient_id: encounter.patientId,
    encounter_id: encounter.id,
    risk_score: result.risk_score,
    risk_level: result.risk_level,
    sofa_rounded: result.sofa_rounded,
    trend: result.trend,
    predicted_at: inserted.rows[0].predictedAt,
  });

  if (!alertTriggered) return;

  const alertPayload = {
    patient_id: encounter.patientId,
    encounter_id: encounter.id,
    patient_name: encounter.fullName,
    risk_score: result.risk_score,
    risk_level: result.risk_level,
    sofa_rounded: result.sofa_rounded,
    alert_text: result.alert_text,
    attention_peak_hour: result.attention_peak_hour,
    ward: encounter.ward,
    bed_id: encounter.bedId,
  };

  emitSepsisAlert(alertPayload);
  await notifyCareTeam(encounter, alertPayload);
}

async function notifyCareTeam(encounter, alertPayload) {
  const recipients = await query(
    `SELECT id FROM users
     WHERE "isActive" = true
       AND (
         (role = 'NURSE' AND ward = $1)
         OR ($2::uuid IS NOT NULL AND id = $2::uuid)
       )`,
    [encounter.ward, encounter.treatingDoctorId],
  );

  const title = `Sepsis alert: ${encounter.fullName}`;
  const body = alertPayload.alert_text || `Risk score ${alertPayload.risk_score} (${alertPayload.risk_level}), SOFA ${alertPayload.sofa_rounded}`;

  await Promise.all(
    recipients.rows.map((recipient) =>
      query(
        `INSERT INTO notifications
           ("recipientId", type, title, body, "patientId", "encounterId", severity)
         VALUES ($1, 'sepsis:alert', $2, $3, $4, $5, 'CRITICAL')`,
        [recipient.id, title, body, encounter.patientId, encounter.id],
      ),
    ),
  );
}

async function runScoringPass() {
  const activeEncounters = await query(
    `SELECT e.id, e."patientId", e.ward, e."bedId", e."treatingDoctorId", p."fullName"
     FROM encounters e
     JOIN patients p ON p.id = e."patientId"
     WHERE e.status = 'ACTIVE'`,
  );

  console.log(`[scoringJob] Scoring ${activeEncounters.rows.length} active encounter(s)`);

  for (const encounter of activeEncounters.rows) {
    // Sequential on purpose: keeps load on the AI Gateway predictable and
    // avoids hammering it with N parallel requests every hour.
    await scoreEncounter(encounter).catch((err) =>
      console.error(`[scoringJob] Unhandled error scoring encounter ${encounter.id}:`, err),
    );
  }
}

function startScoringJob() {
  // Hourly, on the hour.
  const task = cron.schedule('0 * * * *', () => {
    runScoringPass().catch((err) => console.error('[scoringJob] Pass failed:', err));
  });
  console.log('[scoringJob] Scheduled hourly sepsis scoring job (0 * * * *)');
  return task;
}

module.exports = { startScoringJob, runScoringPass };
