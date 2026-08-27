const express = require('express');
const axios = require('axios');
const { query } = require('../lib/db');
const { authenticate, requireRole } = require('../middleware/auth');
const { emitVitalsLogged, emitScoreUpdated, emitSepsisAlert } = require('../sockets/index');
const { signServiceToken } = require('../utils/jwt');

// mergeParams so this router also works nested under
// /api/encounters/:encounterId/vitals (see routes/index.js)
const router = express.Router({ mergeParams: true });
router.use(authenticate);

const VITAL_FIELDS = ['heartRate', 'systolicBp', 'diastolicBp', 'temperature', 'respiratoryRate', 'spo2', 'map'];

// GET /api/encounters/:encounterId/vitals
router.get('/', async (req, res, next) => {
  try {
    const encounterId = req.params.encounterId;
    const result = await query(
      `SELECT * FROM vitals WHERE "encounterId" = $1 ORDER BY "recordedAt" ASC`,
      [encounterId],
    );
    return res.status(200).json({ data: result.rows });
  } catch (err) {
    return next(err);
  }
});

// POST /api/vitals
router.post('/', requireRole('NURSE'), async (req, res, next) => {
  try {
    const {
      encounterId,
      heartRate,
      systolicBp,
      diastolicBp,
      temperature,
      respiratoryRate,
      spo2,
      map,
      notes,
    } = req.body;

    if (!encounterId) {
      return res.status(400).json({
        error: 'encounterId is required',
        code: 'VALIDATION_ERROR',
        statusCode: 400,
      });
    }

    const hasVitalValue = VITAL_FIELDS.some((field) => req.body[field] !== undefined && req.body[field] !== null);
    if (!hasVitalValue) {
      return res.status(400).json({
        error: 'At least one vital value is required',
        code: 'VALIDATION_ERROR',
        statusCode: 400,
      });
    }

    const encounterResult = await query(
      `SELECT id, "patientId" FROM encounters WHERE id = $1`,
      [encounterId],
    );
    const encounterRow = encounterResult.rows[0];
    if (!encounterRow) {
      return res.status(404).json({
        error: 'Encounter not found',
        code: 'NOT_FOUND',
        statusCode: 404,
      });
    }

    const inserted = await query(
      `INSERT INTO vitals
         ("encounterId", "patientId", "recordedBy", "heartRate", "systolicBp", "diastolicBp",
          temperature, "respiratoryRate", spo2, map, notes)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
       RETURNING *`,
      [
        encounterId,
        encounterRow.patientId,
        req.user.sub,
        heartRate ?? null,
        systolicBp ?? null,
        diastolicBp ?? null,
        temperature ?? null,
        respiratoryRate ?? null,
        spo2 ?? null,
        map ?? null,
        notes || null,
      ],
    );
    const vital = inserted.rows[0];

    emitVitalsLogged({
      encounter_id: encounterId,
      patient_id: encounterRow.patientId,
      recorded_at: new Date().toISOString(),
    });

    // Fire-and-forget immediate AI scoring — do not block the response on it.
    setImmediate(async () => {
      try {
        const enc = await query(
          `SELECT e.*, p."fullName" FROM encounters e
           JOIN patients p ON p.id = e."patientId"
           WHERE e.id = $1`,
          [encounterId],
        );
        if (!enc.rows[0]) return;

        const vitalsResult = await query(
          `SELECT * FROM vitals WHERE "encounterId" = $1
           ORDER BY "recordedAt" DESC LIMIT 24`,
          [encounterId],
        );
        const vitalsReadings = vitalsResult.rows
          .reverse()
          .map((v, idx) => ({
            hr: v.heartRate,
            o2sat: v.spo2,
            temp: v.temperature,
            sbp: v.systolicBp,
            map: v.map,
            dbp: v.diastolicBp,
            resp: v.respiratoryRate,
            iculos: idx + 1,
          }));

        if (vitalsReadings.length < 2) return;

        const medsResult = await query(
          `SELECT "drugName" FROM medications
           WHERE "encounterId" = $1 AND status = 'ACTIVE'`,
          [encounterId],
        );
        const medications = medsResult.rows.map((m) => m.drugName);

        const token = signServiceToken();
        const { data } = await axios.post(
          `${process.env.AI_GATEWAY_URL}/gateway/predict`,
          {
            patient_id: enc.rows[0].patientId,
            encounter_id: encounterId,
            vitals_readings: vitalsReadings,
            medications,
          },
          { headers: { Authorization: `Bearer ${token}` }, timeout: 15000 },
        );

        const sepsisResult = data?.sepsis?.result;
        if (!sepsisResult) return;

        await query(
          `INSERT INTO predictions
           ("encounterId","patientId","modelType","result","alertTriggered","latencyMs")
           VALUES ($1,$2,$3,$4,$5,$6)`,
          [
            encounterId,
            enc.rows[0].patientId,
            'sepsis',
            JSON.stringify(data),
            sepsisResult.alert || false,
            data?.sepsis?.latency_ms || null,
          ],
        );

        if (sepsisResult.alert) {
          emitSepsisAlert({
            patient_id: enc.rows[0].patientId,
            encounter_id: encounterId,
            patient_name: enc.rows[0].fullName,
            risk_score: sepsisResult.risk_score,
            risk_level: sepsisResult.risk_level,
            sofa_rounded: sepsisResult.sofa_rounded,
            alert_text: sepsisResult.alert_text || 'Sepsis alert',
            attention_peak_hour: sepsisResult.attention_peak_hour,
            ward: enc.rows[0].ward,
            bed_id: enc.rows[0].bedId,
          });

          if (enc.rows[0].treatingDoctorId) {
            await query(
              `INSERT INTO notifications
               ("recipientId","type","title","body",
                "patientId","encounterId","severity")
               VALUES ($1,$2,$3,$4,$5,$6,$7)`,
              [
                enc.rows[0].treatingDoctorId,
                'sepsis_alert',
                'Sepsis Alert — ' + enc.rows[0].fullName,
                sepsisResult.alert_text || 'High sepsis risk detected',
                enc.rows[0].patientId,
                encounterId,
                'CRITICAL',
              ],
            );
          }
        }

        emitScoreUpdated({
          encounter_id: encounterId,
          patient_id: enc.rows[0].patientId,
          risk_score: sepsisResult.risk_score,
          risk_level: sepsisResult.risk_level,
          sofa_rounded: sepsisResult.sofa_rounded,
        });
      } catch (err) {
        console.error('[VitalsRoute] AI scoring error:', err.message);
      }
    });

    return res.status(201).json({ data: vital, message: 'Vitals logged' });
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
