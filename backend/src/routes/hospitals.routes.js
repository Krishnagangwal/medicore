const express = require('express')
const router = express.Router()
const { query, pool } = require('../lib/db')
const { authenticate, requireRole } = require('../middleware/auth')
const bcrypt = require('bcrypt')
const { sendHospitalApprovalEmail } = require('../services/email.service')
const { signResetToken } = require('../utils/jwt')

function generateTempPassword(length = 10) {
  const chars = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
  let result = ''
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

// ── PUBLIC ──────────────────────────────────────────────────

// GET /api/hospitals
// Returns approved hospitals for login dropdown
router.get('/', async (req, res) => {
  try {
    const result = await query(
      `SELECT id, name FROM hospitals
       WHERE status = 'approved'
       ORDER BY name ASC`
    )
    res.json({ data: result.rows })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// GET /api/hospitals/:hospitalId/staff
// Returns staff names for login name dropdown
// Query param: ?role=NURSE or ?role=DOCTOR
router.get('/:hospitalId/staff', async (req, res) => {
  try {
    const { hospitalId } = req.params
    const { role } = req.query

    if (!role || !['NURSE', 'DOCTOR'].includes(role.toUpperCase())) {
      return res.status(400).json({
        error: 'role query param required (NURSE or DOCTOR)'
      })
    }

    const result = await query(
      `SELECT id, "fullName" FROM users
       WHERE "hospitalId" = $1
       AND role = $2
       AND "isActive" = true
       ORDER BY "fullName" ASC`,
      [hospitalId, role.toUpperCase()]
    )
    res.json({ data: result.rows })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// POST /api/hospitals/request
// Hospital requests access to MediCore
router.post('/request', async (req, res) => {
  try {
    const { hospitalName, adminName, adminEmail } = req.body

    if (!hospitalName || !adminName || !adminEmail) {
      return res.status(400).json({
        error: 'hospitalName, adminName and adminEmail are required'
      })
    }

    // Check not already registered
    const existing = await query(
      `SELECT id FROM hospitals WHERE "adminEmail" = $1`,
      [adminEmail]
    )
    if (existing.rows.length > 0) {
      return res.status(409).json({
        error: 'This email has already submitted a request'
      })
    }

    await query(
      `INSERT INTO hospitals (name, "adminEmail", "adminName", status)
       VALUES ($1, $2, $3, 'pending')`,
      [hospitalName, adminEmail, adminName]
    )

    res.status(201).json({
      message: 'Request submitted successfully. You will be notified by email when approved.'
    })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// ── SUPER ADMIN ──────────────────────────────────────────────

// GET /api/hospitals/admin/requests
// All pending hospital requests
router.get('/admin/requests', authenticate, requireRole('SUPER_ADMIN'), async (req, res) => {
  try {
    const result = await query(
      `SELECT * FROM hospitals
       WHERE status = 'pending'
       ORDER BY "createdAt" DESC`
    )
    res.json({ data: result.rows })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// GET /api/hospitals/admin/all
// All hospitals with all fields
router.post('/admin/:hospitalId/approve', authenticate, requireRole('SUPER_ADMIN'), async (req, res) => {
  try {
    console.log('[APPROVE] ===== START =====')
    console.log('[APPROVE] hospitalId:', req.params.hospitalId)
    console.log('[APPROVE] user:', req.user)

    const { hospitalId } = req.params

    console.log('[APPROVE] Fetching hospital...')

    const hospitalResult = await query(
      `SELECT * FROM hospitals WHERE id = $1`,
      [hospitalId]
    )

    console.log('[APPROVE] Hospital query returned:', hospitalResult.rows.length)

    if (hospitalResult.rows.length === 0) {
      console.log('[APPROVE] Hospital NOT FOUND')
      return res.status(404).json({ error: 'Hospital not found' })
    }

    const hospital = hospitalResult.rows[0]

    console.log('[APPROVE] Hospital:', {
      id: hospital.id,
      name: hospital.name,
      adminEmail: hospital.adminEmail,
      adminName: hospital.adminName,
      status: hospital.status
    })

    if (hospital.status === 'approved') {
      console.log('[APPROVE] Already approved')
      return res.status(409).json({ error: 'Hospital already approved' })
    }

    console.log('[APPROVE] Generating password...')

    const tempPassword = generateTempPassword()
    const passwordHash = await bcrypt.hash(tempPassword, 12)

    console.log('[APPROVE] Updating hospital status...')

    await query(
      `UPDATE hospitals
       SET status = 'approved', "approvedAt" = NOW(), "approvedBy" = $1
       WHERE id = $2`,
      [req.user.sub, hospitalId]
    )

    console.log('[APPROVE] Hospital status updated')

    console.log('[APPROVE] Creating admin user...')

    const adminUserResult = await query(
      `INSERT INTO users
       (email, "passwordHash", "fullName", role, "hospitalId", "mustChangePassword")
       VALUES ($1, $2, $3, 'ADMIN', $4, true)
       ON CONFLICT (email) DO UPDATE
       SET "passwordHash" = EXCLUDED."passwordHash",
           "hospitalId" = EXCLUDED."hospitalId",
           "mustChangePassword" = true
       RETURNING id`,
      [
        hospital.adminEmail,
        passwordHash,
        hospital.adminName,
        hospitalId
      ]
    )

    console.log('[APPROVE] Admin user created:', adminUserResult.rows[0])

    const resetToken = signResetToken({
      id: adminUserResult.rows[0].id
    })

    console.log('[APPROVE] Reset token generated')
    console.log('[APPROVE] Sending email to:', hospital.adminEmail)

    await sendHospitalApprovalEmail({
      to: hospital.adminEmail,
      hospitalName: hospital.name,
      adminName: hospital.adminName,
      tempPassword,
      resetToken
    })

    console.log('[APPROVE] Email function completed')
    console.log('[APPROVE] ===== SUCCESS =====')

    res.json({
      message: 'Hospital approved and admin account created',
      tempPassword,
      hospital: {
        ...hospital,
        status: 'approved'
      }
    })

  } catch (err) {
    console.error('[APPROVE] ERROR:', err)
    console.error('[APPROVE] ERROR STACK:', err.stack)

    res.status(500).json({
      error: err.message
    })
  }
})

// POST /api/hospitals/admin/:hospitalId/approve
router.post('/admin/:hospitalId/approve', authenticate, requireRole('SUPER_ADMIN'), async (req, res) => {
  try {
    console.log("HIIIIIIIii")
    const { hospitalId } = req.params

    // Get hospital
    const hospitalResult = await query(
      `SELECT * FROM hospitals WHERE id = $1`,
      [hospitalId]
    )
    if (hospitalResult.rows.length === 0) {
      return res.status(404).json({ error: 'Hospital not found' })
    }
    const hospital = hospitalResult.rows[0]

    if (hospital.status === 'approved') {
      return res.status(409).json({ error: 'Hospital already approved' })
    }

    // Generate temp password
    const tempPassword = generateTempPassword()
    const passwordHash = await bcrypt.hash(tempPassword, 12)

    // Update hospital status
    await query(
      `UPDATE hospitals
       SET status = 'approved', "approvedAt" = NOW(), "approvedBy" = $1
       WHERE id = $2`,
      [req.user.sub, hospitalId]
    )

    // Create hospital admin user
    const adminUserResult = await query(
      `INSERT INTO users
       (email, "passwordHash", "fullName", role, "hospitalId", "mustChangePassword")
       VALUES ($1, $2, $3, 'ADMIN', $4, true)
       ON CONFLICT (email) DO UPDATE
       SET "passwordHash" = EXCLUDED."passwordHash",
           "hospitalId" = EXCLUDED."hospitalId",
           "mustChangePassword" = true
       RETURNING id`,
      [hospital.adminEmail, passwordHash, hospital.adminName, hospitalId]
    )

    // Send approval email — fire-and-forget. sendMail() already catches and
    // logs its own errors instead of throwing, so this never rejects; the
    // point of not awaiting it is purely to stop a slow/blocked SMTP
    // connection (e.g. a host that blocks outbound port 587) from holding
    // the whole HTTP response hostage for minutes.
    sendHospitalApprovalEmail({
      to: hospital.adminEmail,
      hospitalName: hospital.name,
      adminName: hospital.adminName,
      tempPassword,
      resetToken: signResetToken({ id: adminUserResult.rows[0].id })
    })

    res.json({
      message: 'Hospital approved and admin account created',
      tempPassword,  // Return in response for testing (remove in production)
      hospital: { ...hospital, status: 'approved' }
    })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// POST /api/hospitals/admin/:hospitalId/reject
router.post('/admin/:hospitalId/reject', authenticate, requireRole('SUPER_ADMIN'), async (req, res) => {
  try {
    const { hospitalId } = req.params
    const { note } = req.body

    await query(
      `UPDATE hospitals
       SET status = 'rejected', "rejectedAt" = NOW(), "rejectionNote" = $1
       WHERE id = $2`,
      [note || null, hospitalId]
    )

    res.json({ message: 'Hospital rejected' })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// DELETE /api/hospitals/admin/:hospitalId
// Permanently deletes a hospital and every record scoped to it (staff,
// patients, encounters, vitals, medications, predictions, notifications).
// No ON DELETE CASCADE in the schema, so children are removed explicitly
// in dependency order inside one transaction.
router.delete('/admin/:hospitalId', authenticate, requireRole('SUPER_ADMIN'), async (req, res) => {
  const { hospitalId } = req.params
  const client = await pool.connect()
  try {
    const hospitalResult = await client.query(`SELECT id, name FROM hospitals WHERE id = $1`, [hospitalId])
    if (hospitalResult.rows.length === 0) {
      return res.status(404).json({ error: 'Hospital not found' })
    }

    await client.query('BEGIN')

    await client.query(
      `DELETE FROM notifications
       WHERE "recipientId" IN (SELECT id FROM users WHERE "hospitalId" = $1)
          OR "patientId" IN (SELECT id FROM patients WHERE "hospitalId" = $1)`,
      [hospitalId]
    )
    await client.query(
      `DELETE FROM vitals
       WHERE "encounterId" IN (
         SELECT e.id FROM encounters e JOIN patients p ON e."patientId" = p.id
         WHERE p."hospitalId" = $1
       )`,
      [hospitalId]
    )
    await client.query(
      `DELETE FROM medications
       WHERE "encounterId" IN (
         SELECT e.id FROM encounters e JOIN patients p ON e."patientId" = p.id
         WHERE p."hospitalId" = $1
       )`,
      [hospitalId]
    )
    await client.query(
      `DELETE FROM predictions
       WHERE "encounterId" IN (
         SELECT e.id FROM encounters e JOIN patients p ON e."patientId" = p.id
         WHERE p."hospitalId" = $1
       )`,
      [hospitalId]
    )
    await client.query(
      `DELETE FROM encounters
       WHERE "patientId" IN (SELECT id FROM patients WHERE "hospitalId" = $1)`,
      [hospitalId]
    )
    await client.query(`DELETE FROM patients WHERE "hospitalId" = $1`, [hospitalId])
    await client.query(`DELETE FROM users WHERE "hospitalId" = $1`, [hospitalId])
    await client.query(`DELETE FROM hospitals WHERE id = $1`, [hospitalId])

    await client.query('COMMIT')
    res.json({ message: `${hospitalResult.rows[0].name} and all related data deleted` })
  } catch (err) {
    await client.query('ROLLBACK')
    res.status(500).json({ error: err.message })
  } finally {
    client.release()
  }
})

module.exports = router
