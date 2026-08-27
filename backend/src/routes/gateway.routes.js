const express = require('express');
const axios = require('axios');
const { query } = require('../lib/db');
const { authenticate, requireRole } = require('../middleware/auth');
const { signServiceToken } = require('../utils/jwt');

const router = express.Router();
router.use(authenticate);

// POST /api/gateway/assess
// Manual trigger: doctor/nurse opens a patient and wants an immediate AI
// assessment without waiting for the hourly scoring job.
router.post('/assess', requireRole('DOCTOR', 'NURSE'), async (req, res, next) => {
  try {
    const { encounterId } = req.body;

    if (!encounterId) {
      return res.status(400).json({
        error: 'encounterId is required',
        code: 'VALIDATION_ERROR',
        statusCode: 400,
      });
    }

    const encResult = await query(
      `SELECT e.*, p."fullName" FROM encounters e
       JOIN patients p ON p.id = e."patientId"
       WHERE e.id = $1`,
      [encounterId],
    );
    const encounter = encResult.rows[0];
    if (!encounter) {
      return res.status(404).json({
        error: 'Encounter not found',
        code: 'NOT_FOUND',
        statusCode: 404,
      });
    }

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

    const medsResult = await query(
      `SELECT "drugName" FROM medications
       WHERE "encounterId" = $1 AND status = 'ACTIVE'`,
      [encounterId],
    );
    const medications = medsResult.rows.map((m) => m.drugName);

    const token = signServiceToken();
    const startedAt = Date.now();
    const { data } = await axios.post(
      `${process.env.AI_GATEWAY_URL}/gateway/predict`,
      {
        patient_id: encounter.patientId,
        encounter_id: encounterId,
        vitals_readings: vitalsReadings,
        medications,
      },
      { headers: { Authorization: `Bearer ${token}` }, timeout: 15000 },
    );

    const sepsisResult = data?.sepsis?.result;
    if (sepsisResult) {
      await query(
        `INSERT INTO predictions
         ("encounterId","patientId","modelType","result","alertTriggered","latencyMs")
         VALUES ($1,$2,$3,$4,$5,$6)`,
        [
          encounterId,
          encounter.patientId,
          'sepsis',
          JSON.stringify(data),
          sepsisResult.alert || false,
          data?.sepsis?.latency_ms || Date.now() - startedAt,
        ],
      );
    }

    return res.status(200).json({ data });
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
