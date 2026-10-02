const express = require('express')
const router = express.Router()
const { query } = require('../lib/db')
const { authenticate, requireRole } = require('../middleware/auth')
const bcrypt = require('bcrypt')
const { sendStaffInviteEmail } = require('../services/email.service')
const { signResetToken } = require('../utils/jwt')

function generateTempPassword(length = 10) {
  const chars = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
  let result = ''
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

// GET /api/hospital/staff
// Get all staff for the admin's hospital
router.get('/staff', authenticate, requireRole('ADMIN'), async (req, res) => {
  try {
    const result = await query(
      `SELECT id, email, "fullName", role, ward, "isActive", "createdAt"
       FROM users
       WHERE "hospitalId" = $1
       AND role IN ('NURSE', 'DOCTOR')
       ORDER BY role, "fullName" ASC`,
      [req.user.hospitalId]
    )
    res.json({ data: result.rows })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// POST /api/hospital/invite
// Invite a nurse or doctor to the hospital
router.post('/invite', authenticate, requireRole('ADMIN'), async (req, res) => {
  try {
    const { fullName, email, role, ward } = req.body

    if (!fullName || !email || !role) {
      return res.status(400).json({
        error: 'fullName, email and role are required'
      })
    }

    if (!['NURSE', 'DOCTOR'].includes(role.toUpperCase())) {
      return res.status(400).json({
        error: 'role must be NURSE or DOCTOR'
      })
    }

    // Check email not already in use
    const existing = await query(
      `SELECT id FROM users WHERE email = $1`,
      [email]
    )
    if (existing.rows.length > 0) {
      return res.status(409).json({
        error: 'A user with this email already exists'
      })
    }

    // Get hospital name for email
    const hospitalResult = await query(
      `SELECT name FROM hospitals WHERE id = $1`,
      [req.user.hospitalId]
    )
    const hospitalName = hospitalResult.rows[0]?.name || 'your hospital'

    // Generate temp password
    const tempPassword = generateTempPassword()
    const passwordHash = await bcrypt.hash(tempPassword, 12)

    // Create user
    const result = await query(
      `INSERT INTO users
       (email, "passwordHash", "fullName", role, "hospitalId",
        ward, "invitedBy", "mustChangePassword")
       VALUES ($1, $2, $3, $4, $5, $6, $7, true)
       RETURNING id, email, "fullName", role`,
      [email, passwordHash, fullName, role.toUpperCase(),
       req.user.hospitalId, ward || null, req.user.sub]
    )

    // Send invite email
    await sendStaffInviteEmail({
      to: email,
      staffName: fullName,
      hospitalName,
      tempPassword,
      role: role.toUpperCase(),
      resetToken: signResetToken({ id: result.rows[0].id })
    })

    res.status(201).json({
      message: 'Staff invited successfully',
      tempPassword,  // Return for testing — remove in production
      user: result.rows[0]
    })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// DELETE /api/hospital/staff/:userId
// Deactivate a staff member
router.delete('/staff/:userId', authenticate, requireRole('ADMIN'), async (req, res) => {
  try {
    const { userId } = req.params

    // Verify user belongs to same hospital
    const userResult = await query(
      `SELECT id, "hospitalId" FROM users WHERE id = $1`,
      [userId]
    )

    if (userResult.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' })
    }

    if (userResult.rows[0].hospitalId !== req.user.hospitalId) {
      return res.status(403).json({
        error: 'Cannot deactivate staff from another hospital'
      })
    }

    await query(
      `UPDATE users SET "isActive" = false WHERE id = $1`,
      [userId]
    )

    res.json({ message: 'Staff member deactivated' })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

module.exports = router
